from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace

import pytest
from celery.exceptions import Retry
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.accounts.models import Company
from src.agents import tasks as agent_tasks
from src.agents.celery_app import celery_app
from src.database import Base
from src.projects.models import Project, ProjectTodo, ProjectVersion
from src.projects.schemas import TodoStatus, VersionStatus


def test_celery_beat_schedules_planned_todo_dispatch() -> None:
    schedule = celery_app.conf.beat_schedule["dispatch-planned-todos"]

    assert schedule["task"] == "agents.dispatch_planned_todos"
    assert schedule["schedule"] >= 5
    assert schedule["options"]["expires"] == schedule["schedule"]
    assert celery_app.conf.worker_concurrency == 1
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True
    github_schedule = celery_app.conf.beat_schedule[
        "dispatch-github-workflow-tasks"
    ]
    assert github_schedule["task"] == "github.dispatch-workflow-tasks"
    assert github_schedule["schedule"] == 1


def test_agent_execution_lock_allows_only_one_runner(monkeypatch) -> None:
    class FakeLock:
        active = False

        def acquire(self, *, blocking: bool) -> bool:
            assert blocking is False
            if self.__class__.active:
                return False
            self.__class__.active = True
            return True

        def release(self) -> None:
            self.__class__.active = False

    class FakeRedis:
        def lock(
            self,
            name: str,
            *,
            timeout: int,
            blocking: bool,
        ) -> FakeLock:
            assert name == "project-release-api:agent-execution"
            assert timeout > 0
            assert blocking is False
            return FakeLock()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        agent_tasks.Redis,
        "from_url",
        lambda url: FakeRedis(),
    )

    with agent_tasks.agent_execution_lock() as first_acquired:
        with agent_tasks.agent_execution_lock() as second_acquired:
            assert first_acquired is True
            assert second_acquired is False

    with agent_tasks.agent_execution_lock() as acquired_after_release:
        assert acquired_after_release is True


def test_busy_execution_lock_retries_without_running_agent(monkeypatch) -> None:
    executed = False

    @contextmanager
    def fake_agent_execution_lock():
        yield False

    async def fake_execute_run(run_id: str):
        nonlocal executed
        executed = True
        return {"id": run_id}

    monkeypatch.setattr(
        agent_tasks,
        "agent_execution_lock",
        fake_agent_execution_lock,
    )
    monkeypatch.setattr(agent_tasks, "execute_run", fake_execute_run)

    with pytest.raises(Retry):
        agent_tasks.execute_agent_run.run("run-one")

    assert executed is False


def test_execute_task_publishes_completion_event(monkeypatch) -> None:
    published: list[dict[str, object]] = []
    result = {
        "id": "run-one",
        "projectId": "project",
        "todoId": "todo",
        "provider": "codex",
        "status": "succeeded",
        "branchName": "todo/todo",
        "repositoryPath": "/repositories/project",
        "pushed": True,
        "exitCode": 0,
        "output": "done",
        "error": None,
        "startedAt": "2026-07-28T11:00:00Z",
        "completedAt": "2026-07-28T12:00:00Z",
    }

    @contextmanager
    def fake_agent_execution_lock():
        yield True

    async def fake_execute_run(run_id: str):
        assert run_id == "run-one"
        return result

    monkeypatch.setattr(
        agent_tasks,
        "agent_execution_lock",
        fake_agent_execution_lock,
    )
    monkeypatch.setattr(agent_tasks, "execute_run", fake_execute_run)
    monkeypatch.setattr(
        agent_tasks,
        "publish_completion_event",
        published.append,
    )

    task_result = agent_tasks.execute_agent_run.run("run-one")

    assert task_result == result
    assert published == []


def test_execute_task_publishes_failed_completion_event(monkeypatch) -> None:
    published: list[dict[str, object]] = []
    failed_result = {
        "id": "run-failed",
        "projectId": "project",
        "todoId": "todo",
        "provider": "codex",
        "status": "failed",
        "branchName": "todo/todo",
        "repositoryPath": "/repositories/project",
        "pushed": False,
        "exitCode": None,
        "output": "",
        "error": "Unexpected worker failure: crashed",
        "startedAt": "2026-07-28T11:00:00Z",
        "completedAt": "2026-07-28T12:00:00Z",
    }

    @contextmanager
    def fake_agent_execution_lock():
        yield True

    async def fake_execute_run(run_id: str):
        raise RuntimeError("crashed")

    async def fake_fail_active_run(run_id: str, error: str):
        assert run_id == "run-failed"
        assert error == "Unexpected worker failure: crashed"
        return failed_result

    monkeypatch.setattr(
        agent_tasks,
        "agent_execution_lock",
        fake_agent_execution_lock,
    )
    monkeypatch.setattr(agent_tasks, "execute_run", fake_execute_run)
    monkeypatch.setattr(agent_tasks, "fail_active_run", fake_fail_active_run)
    monkeypatch.setattr(
        agent_tasks,
        "publish_completion_event",
        published.append,
    )

    with pytest.raises(RuntimeError, match="crashed"):
        agent_tasks.execute_agent_run.run("run-failed")

    assert published == [failed_result]


async def test_claims_todos_only_for_runnable_versions(
    monkeypatch,
    tmp_path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dispatch.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        project = Project(
            id="project",
            company_id="company",
            name="Project",
            path="/project",
            repository_slug="project",
        )
        company = Company(id="company", name="Company")
        versions = [
            ProjectVersion(
                id=f"version-{status}",
                project_id=project.id,
                name=f"Version {status}",
                summary=f"{status} version",
                status=status,
                branch_name=f"version/{status}",
            )
            for status in (
                VersionStatus.PENDING,
                VersionStatus.READY,
                VersionStatus.IN_PROGRESS,
            )
        ]
        todos = [
            ProjectTodo(
                id=f"todo-{status}",
                project_id=project.id,
                version_id=f"version-{status}",
                issue_number=index,
                title=f"Todo {status}",
                description=f"Work for {status}",
                status=TodoStatus.PLANNED,
                branch_name=f"todo/{status}",
            )
            for index, status in enumerate(
                (
                    VersionStatus.PENDING,
                    VersionStatus.READY,
                    VersionStatus.IN_PROGRESS,
                ),
                start=1,
            )
        ]
        session.add_all([company, project, *versions, *todos])
        await session.commit()

    claimed: list[str] = []

    class FakeService:
        def __init__(self, session) -> None:
            self.session = session

        async def enqueue_planned_todo(self, payload):
            claimed.append(payload.todo_id)
            return SimpleNamespace(id=f"run-{payload.todo_id}")

    @asynccontextmanager
    async def fake_agent_service():
        async with session_factory() as session:
            yield FakeService(session)

    monkeypatch.setattr(agent_tasks, "agent_service", fake_agent_service)

    run_ids = await agent_tasks.claim_planned_todos()

    assert set(claimed) == {
        f"todo-{VersionStatus.READY}",
        f"todo-{VersionStatus.IN_PROGRESS}",
    }
    assert set(run_ids) == {
        f"run-todo-{VersionStatus.READY}",
        f"run-todo-{VersionStatus.IN_PROGRESS}",
    }
    await engine.dispose()


def test_dispatch_publishes_each_claimed_run(monkeypatch) -> None:
    published: list[str] = []

    async def fake_claim_planned_todos() -> list[str]:
        return ["run-one", "run-two"]

    def fake_apply_async(*, args: list[str]) -> None:
        published.append(args[0])

    monkeypatch.setattr(
        agent_tasks,
        "claim_planned_todos",
        fake_claim_planned_todos,
    )
    monkeypatch.setattr(
        agent_tasks.execute_agent_run,
        "apply_async",
        fake_apply_async,
    )

    result = agent_tasks.dispatch_planned_todos.run()

    assert result == {"claimed": 2, "published": 2}
    assert published == ["run-one", "run-two"]
