from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.accounts.models import Company
from src.agents.models import AgentRun
from src.agents.schemas import AgentProvider, AgentRunStatus
from src.database import Base
from src.github.workflow import (
    GithubTaskAction,
    GithubTaskStatus,
    GithubWorkflowExecutor,
    enqueue_github_task,
)
from src.projects.models import Project, ProjectTodo, ProjectVersion
from src.projects.schemas import TodoStatus, VersionStatus


class FakeGithub:
    def __init__(self) -> None:
        self.branches: list[tuple[str, str | None]] = []
        self.pull_requests: list[tuple[str, str]] = []
        self.merges: list[int] = []
        self.closed_issues: list[int] = []
        self.fail_merge = False

    async def create_branch(self, payload):
        self.branches.append((payload.branch, payload.from_branch))
        return {"ref": f"refs/heads/{payload.branch}"}

    async def create_pull_request(self, payload):
        self.pull_requests.append((payload.head, payload.base))
        return {"number": 91, "html_url": "https://example.test/pull/91"}

    async def merge_pull_request(self, payload):
        if self.fail_merge:
            raise RuntimeError("merge conflict")
        self.merges.append(payload.pull_number)
        return {"merged": True, "sha": "a" * 40}

    async def close_issue(self, payload):
        self.closed_issues.append(payload.issue_number)
        return {"number": payload.issue_number, "state": "closed"}


async def test_github_workflow_executes_branch_agent_merge_sequence(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workflow.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        company = Company(id="company", name="Company")
        project = Project(
            id="project",
            company_id=company.id,
            name="Project",
            path="/project",
            repository_slug="project",
        )
        version = ProjectVersion(
            id="project-v1",
            project_id=project.id,
            name="v1",
            summary="First version",
            status=VersionStatus.READY,
            branch_name="version/project-v1",
        )
        todo = ProjectTodo(
            id="todo-work-42",
            project_id=project.id,
            version_id=version.id,
            issue_number=42,
            title="Do work",
            description="Implement the work.",
            status=TodoStatus.IN_PROGRESS,
            branch_name="todo/todo-work-42",
        )
        run = AgentRun(
            id="run-42",
            project_id=project.id,
            todo_id=todo.id,
            local_agent_id=None,
            provider=AgentProvider.CODEX,
            status=AgentRunStatus.QUEUED,
            branch_name=todo.branch_name,
            repository_path=project.path,
            pushed=False,
            output="",
        )
        session.add_all([company, project, version, todo, run])
        version_task = await enqueue_github_task(
            session,
            project_id=project.id,
            version_id=version.id,
            action=GithubTaskAction.CREATE_VERSION_BRANCH,
        )
        todo_task = await enqueue_github_task(
            session,
            project_id=project.id,
            version_id=version.id,
            todo_id=todo.id,
            action=GithubTaskAction.CREATE_TODO_BRANCH,
        )
        await session.commit()

        github = FakeGithub()
        executor = GithubWorkflowExecutor(session, github)
        completed_version_task, version_run_ids, version_completed_run = await executor.execute(
            version_task.id
        )
        completed_todo_task, todo_run_ids, todo_completed_run = await executor.execute(
            todo_task.id
        )

        assert completed_version_task.status == GithubTaskStatus.SUCCEEDED
        assert completed_todo_task.status == GithubTaskStatus.SUCCEEDED
        assert version_run_ids == []
        assert version_completed_run is None
        assert todo_run_ids == [run.id]
        assert todo_completed_run is None
        assert github.branches == [
            (version.branch_name, project.default_branch),
            (todo.branch_name, version.branch_name),
        ]

        run.status = AgentRunStatus.SUCCEEDED
        merge_task = await enqueue_github_task(
            session,
            project_id=project.id,
            version_id=version.id,
            todo_id=todo.id,
            action=GithubTaskAction.MERGE_TODO,
        )
        await session.commit()
        completed_merge_task, merge_run_ids, completed_run_id = await executor.execute(
            merge_task.id
        )

        assert completed_merge_task.status == GithubTaskStatus.SUCCEEDED
        assert merge_run_ids == []
        assert completed_run_id == run.id
        assert github.pull_requests == [(todo.branch_name, version.branch_name)]
        assert github.merges == [91]
        assert github.closed_issues == [todo.issue_number]
        assert todo.status == TodoStatus.DONE
        assert todo.is_merged is True

        failed_todo = ProjectTodo(
            id="todo-failed-43",
            project_id=project.id,
            version_id=version.id,
            issue_number=43,
            title="Conflicting work",
            description="This merge will fail.",
            status=TodoStatus.IN_PROGRESS,
            branch_name="todo/todo-failed-43",
        )
        failed_run = AgentRun(
            id="run-43",
            project_id=project.id,
            todo_id=failed_todo.id,
            local_agent_id=None,
            provider=AgentProvider.CODEX,
            status=AgentRunStatus.SUCCEEDED,
            branch_name=failed_todo.branch_name,
            repository_path=project.path,
            pushed=True,
            output="done",
        )
        session.add_all([failed_todo, failed_run])
        failed_merge_task = await enqueue_github_task(
            session,
            project_id=project.id,
            version_id=version.id,
            todo_id=failed_todo.id,
            action=GithubTaskAction.MERGE_TODO,
        )
        await session.commit()
        github.fail_merge = True

        terminal_task, dispatched_runs, completed_failed_run = (
            await executor.execute(failed_merge_task.id)
        )

        assert terminal_task.status == GithubTaskStatus.FAILED
        assert terminal_task.error == "merge conflict"
        assert terminal_task.attempts == 1
        assert dispatched_runs == []
        assert completed_failed_run == failed_run.id
        assert failed_todo.status == TodoStatus.DONE
        assert failed_todo.is_merged is False

    await engine.dispose()
