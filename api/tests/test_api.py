from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.github.config import get_github_settings
from src.github.dependencies import get_github_service
from src.github.models import GithubWorkflowTask
from src.github.schemas import IssueCreate
from src.github.workflow import GithubTaskAction, GithubTaskStatus
from src.main import app
from src.projects.models import ProjectTodo, ProjectVersion


@pytest.fixture(autouse=True)
def disable_live_github_configuration(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GITHUB_ENABLED", "false")
    get_github_settings.cache_clear()
    yield
    get_github_settings.cache_clear()


@pytest.fixture
async def client(tmp_path) -> AsyncIterator[AsyncClient]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    test_engine = create_async_engine(database_url)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_session_factory = test_session_factory
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test Owner",
                "email": "owner@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert register_response.status_code == 201
        test_client.headers["Authorization"] = f"Bearer {register_response.json()['accessToken']}"
        company_response = await test_client.post(
            "/api/v1/companies",
            json={"name": "Test Company"},
        )
        assert company_response.status_code == 201
        app.state.test_company_id = company_response.json()["id"]
        yield test_client

    app.dependency_overrides.clear()
    del app.state.test_company_id
    del app.state.test_session_factory
    await test_engine.dispose()


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["checkedAt"]
    assert payload["services"] == [
        {"name": "database", "status": "operational"},
        {"name": "github", "status": "unavailable"},
    ]


async def test_item_crud(client: AsyncClient) -> None:
    create_response = await client.post(
        "/items",
        json={"name": "Learn FastAPI", "description": "Build a small API"},
    )
    assert create_response.status_code == 201
    item = create_response.json()
    assert item["name"] == "Learn FastAPI"
    assert item["completed"] is False

    update_response = await client.patch(
        f"/items/{item['id']}",
        json={"completed": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["completed"] is True

    list_response = await client.get("/items")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = await client.delete(f"/items/{item['id']}")
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/items/{item['id']}")
    assert missing_response.status_code == 404


async def test_github_integration_is_disabled_by_default(client: AsyncClient) -> None:
    response = await client.get("/github/tools")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GITHUB_NOT_CONFIGURED"
    assert response.json()["error"]["message"] == "GitHub MCP integration is disabled"


async def test_github_issue_route_delegates_to_service(client: AsyncClient) -> None:
    class FakeGithubService:
        async def create_issue(self, payload: IssueCreate) -> dict[str, str]:
            return {"repository": payload.repo, "title": payload.title}

    async def override_github_service() -> FakeGithubService:
        return FakeGithubService()

    app.dependency_overrides[get_github_service] = override_github_service

    response = await client.post(
        "/github/issues",
        json={
            "repo": "project-api",
            "title": "Group issues by version",
            "description": "Associate project work with a release version.",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "repository": "project-api",
        "title": "Group issues by version",
    }


async def test_project_validation_uses_contract_error_shape(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={
            "companyId": app.state.test_company_id,
            "name": "Missing path",
        },
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "path"
    assert error["requestId"].startswith("req_")


async def test_project_release_workflow(client: AsyncClient) -> None:
    class FakeGithubWorkflow:
        def __init__(self) -> None:
            self.issue_number = 140
            self.pull_number = 240
            self.branches: list[tuple[str, str]] = []
            self.pull_requests: list[tuple[str, str]] = []
            self.merges: list[int] = []
            self.closed_issues: list[int] = []

        def validate_repository(self, repository: str) -> None:
            assert repository == "project-api"

        async def create_issue(self, payload) -> dict[str, object]:
            self.issue_number += 1
            return {
                "number": self.issue_number,
                "html_url": (f"https://github.com/example/project-api/issues/{self.issue_number}"),
            }

        async def create_branch(self, payload) -> dict[str, str]:
            self.branches.append((payload.branch, payload.from_branch))
            return {"ref": f"refs/heads/{payload.branch}"}

        async def create_pull_request(self, payload) -> dict[str, object]:
            self.pull_number += 1
            self.pull_requests.append((payload.head, payload.base))
            return {
                "number": self.pull_number,
                "html_url": (f"https://github.com/example/project-api/pull/{self.pull_number}"),
            }

        async def merge_pull_request(self, payload) -> dict[str, object]:
            self.merges.append(payload.pull_number)
            return {"merged": True, "sha": "a" * 40}

        async def close_issue(self, payload) -> dict[str, object]:
            self.closed_issues.append(payload.issue_number)
            return {"number": payload.issue_number, "state": "closed"}

    github = FakeGithubWorkflow()

    async def override_github_workflow() -> FakeGithubWorkflow:
        return github

    app.dependency_overrides[get_github_service] = override_github_workflow

    project_response = await client.post(
        "/api/v1/projects",
        json={
            "companyId": app.state.test_company_id,
            "name": "Project API",
            "path": "/project-api",
        },
    )
    assert project_response.status_code == 201
    assert project_response.headers["location"] == "/api/v1/projects/project-api"
    project = project_response.json()
    assert project["id"] == "project-api"

    version_response = await client.post(
        "/api/v1/projects/project-api/versions",
        json={"name": "v1.0", "summary": "Initial project workflow release."},
    )
    assert version_response.status_code == 201
    version = version_response.json()
    version_id = version["id"]
    version_branch = f"version/{version_id}"
    assert version["status"] == "pending"
    assert github.branches == []

    ready_response = await client.patch(
        f"/api/v1/projects/project-api/versions/{version_id}",
        json={"status": "ready"},
    )
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    async with app.state.test_session_factory() as session:
        version_branch_task = await session.scalar(
            select(GithubWorkflowTask).where(
                GithubWorkflowTask.version_id == version_id,
                GithubWorkflowTask.action
                == GithubTaskAction.CREATE_VERSION_BRANCH,
            )
        )
        assert version_branch_task is not None
        assert version_branch_task.status == GithubTaskStatus.PENDING

    invalid_initial_status_response = await client.post(
        f"/api/v1/projects/project-api/versions/{version_id}/todos",
        json={
            "title": "Skip the draft state",
            "description": "New todos must not create their branches immediately.",
            "status": "planned",
        },
    )
    assert invalid_initial_status_response.status_code == 400
    assert github.branches == []

    todo_response = await client.post(
        f"/api/v1/projects/project-api/versions/{version_id}/todos",
        json={
            "title": "Implement project roadmap",
            "description": "Create the project, version, and todo workflow.",
        },
    )
    assert todo_response.status_code == 201
    todo = todo_response.json()
    assert todo["issueNumber"] == 141
    assert todo["status"] == "draft"
    assert github.branches == []

    plan_response = await client.patch(
        f"/api/v1/projects/project-api/todos/{todo['id']}",
        json={"status": "planned"},
    )
    assert plan_response.status_code == 200
    todo = plan_response.json()
    assert todo["status"] == "planned"
    assert github.branches == []

    start_response = await client.patch(
        f"/api/v1/projects/project-api/todos/{todo['id']}",
        json={"status": "in-progress"},
    )
    assert start_response.status_code == 200
    todo = start_response.json()
    async with app.state.test_session_factory() as session:
        todo_branch_task = await session.scalar(
            select(GithubWorkflowTask).where(
                GithubWorkflowTask.todo_id == todo["id"],
                GithubWorkflowTask.action == GithubTaskAction.CREATE_TODO_BRANCH,
            )
        )
        assert todo_branch_task is not None
        assert todo_branch_task.status == GithubTaskStatus.PENDING

    premature_complete = await client.patch(
        f"/api/v1/projects/project-api/versions/{version_id}",
        json={"status": "complete"},
    )
    assert premature_complete.status_code == 409
    assert premature_complete.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    premature_merge = await client.post(
        f"/api/v1/projects/project-api/todos/{todo['id']}/merge",
        json={},
    )
    assert premature_merge.status_code == 409
    assert premature_merge.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    wip_response = await client.post(
        "/api/v1/projects/project-api/wip/todos",
        json={
            "title": "Document release workflow",
            "description": "Explain how version pull requests are released.",
        },
    )
    assert wip_response.status_code == 201
    wip_todo = wip_response.json()
    assert wip_todo["status"] == "draft"
    assert wip_todo["versionId"] is None

    assign_response = await client.post(
        f"/api/v1/projects/project-api/todos/{wip_todo['id']}/assign",
        json={"versionId": version_id},
    )
    assert assign_response.status_code == 200
    assigned_todo = assign_response.json()
    assert assigned_todo["status"] == "planned"
    assert assigned_todo["versionId"] == version_id
    assert github.branches == []

    for current_todo in (todo, assigned_todo):
        done_response = await client.patch(
            f"/api/v1/projects/project-api/todos/{current_todo['id']}",
            json={"status": "done"},
        )
        assert done_response.status_code == 200
        assert done_response.json()["status"] == "done"
        assert done_response.json()["pullRequestNumber"] == github.pull_number
        assert done_response.json()["pullRequestUrl"] == (
            f"https://github.com/example/project-api/pull/{github.pull_number}"
        )
        assert github.pull_requests[-1] == (f"todo/{current_todo['id']}", version_branch)

        merge_response = await client.post(
            f"/api/v1/projects/project-api/todos/{current_todo['id']}/merge",
            json={},
        )
        assert merge_response.status_code == 200
        assert merge_response.json()["isMerged"] is True
        assert github.closed_issues[-1] == current_todo["issueNumber"]

    complete_response = await client.patch(
        f"/api/v1/projects/project-api/versions/{version_id}",
        json={"status": "complete"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "complete"
    assert github.pull_requests[-1] == (version_branch, "main")

    release_response = await client.post(
        f"/api/v1/projects/project-api/versions/{version_id}/release",
        json={"releaseNotes": "First complete release."},
    )
    assert release_response.status_code == 200
    released = release_response.json()
    assert released["status"] == "released"
    assert released["releasedAt"] is not None
    assert len(github.merges) == 3
    assert github.closed_issues == [todo["issueNumber"], assigned_todo["issueNumber"]]

    roadmap_response = await client.get("/api/v1/projects/project-api")
    assert roadmap_response.status_code == 200
    roadmap = roadmap_response.json()
    assert len(roadmap["versions"]) == 1
    assert len(roadmap["versions"][0]["todos"]) == 2
    assert [todo["issueNumber"] for todo in roadmap["versions"][0]["todos"]] == [142, 141]

    newer_version_response = await client.post(
        "/api/v1/projects/project-api/versions",
        json={"name": "v2", "summary": "The next release."},
    )
    assert newer_version_response.status_code == 201
    newer_version_id = newer_version_response.json()["id"]

    reordered_roadmap_response = await client.get("/api/v1/projects/project-api")
    assert reordered_roadmap_response.status_code == 200
    assert [version["id"] for version in reordered_roadmap_response.json()["versions"]] == [
        newer_version_id,
        version_id,
    ]
    assert roadmap["wipTodos"] == []

    disposable_todo_response = await client.post(
        f"/api/v1/projects/project-api/versions/{newer_version_id}/todos",
        json={
            "title": "Discard this pending work",
            "description": "Verify pending versions delete their todos.",
        },
    )
    assert disposable_todo_response.status_code == 201
    assert disposable_todo_response.json()["status"] == "draft"

    delete_pending_version_response = await client.delete(
        f"/api/v1/projects/project-api/versions/{newer_version_id}"
    )
    assert delete_pending_version_response.status_code == 204

    delete_non_draft_todo_response = await client.delete(
        f"/api/v1/projects/project-api/todos/{todo['id']}"
    )
    assert delete_non_draft_todo_response.status_code == 409

    disposable_wip_response = await client.post(
        "/api/v1/projects/project-api/wip/todos",
        json={
            "title": "Discard this draft",
            "description": "Verify draft WIP todos can be deleted.",
        },
    )
    assert disposable_wip_response.status_code == 201
    delete_draft_todo_response = await client.delete(
        f"/api/v1/projects/project-api/todos/{disposable_wip_response.json()['id']}"
    )
    assert delete_draft_todo_response.status_code == 204

    roadmap_after_deletes_response = await client.get("/api/v1/projects/project-api")
    assert roadmap_after_deletes_response.status_code == 200
    roadmap_after_deletes = roadmap_after_deletes_response.json()
    assert [version["id"] for version in roadmap_after_deletes["versions"]] == [version_id]
    assert roadmap_after_deletes["wipTodos"] == []

    async with app.state.test_session_factory() as session:
        stored_version = await session.get(ProjectVersion, version_id)
        stored_todos = list(
            await session.scalars(
                select(ProjectTodo).where(ProjectTodo.project_id == "project-api")
            )
        )

    assert stored_version is not None
    assert stored_version.branch_name == version_branch
    assert stored_version.pull_request_number is not None
    assert all(todo.branch_name == f"todo/{todo.id}" for todo in stored_todos)
    assert all(todo.pull_request_number is not None for todo in stored_todos)
