from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.accounts.models import Company
from src.agents.config import AgentSettings
from src.agents.exceptions import AgentProcessError, AgentRunConflictError
from src.agents.models import LocalAgent
from src.agents.runner import ProcessResult
from src.agents.schemas import AgentProvider, AgentRunStatus, CreateAgentRunRequest
from src.agents.service import AgentRunService
from src.database import Base
from src.github.models import GithubWorkflowTask
from src.github.workflow import GithubTaskAction, GithubTaskStatus
from src.projects.models import Project, ProjectTodo, ProjectVersion
from src.projects.schemas import TodoStatus, VersionStatus


class FakeGithub:
    def __init__(self) -> None:
        self.pull_requests: list[object] = []

    async def create_pull_request(self, payload) -> dict[str, object]:
        self.pull_requests.append(payload)
        return {
            "number": 84,
            "html_url": "https://github.com/rumatech/shoppa/pull/84",
        }


class FakeRunner:
    def __init__(self, repository: Path) -> None:
        self.repository = repository
        self.calls: list[dict[str, object]] = []

    def repository_path(self, repository_slug: str) -> Path:
        return self.repository

    def project_path(self, folder_path: str | Path) -> Path:
        return self.repository

    def with_settings(self, settings: AgentSettings) -> "FakeRunner":
        return self

    async def run(self, **arguments) -> ProcessResult:
        self.calls.append(arguments)
        return ProcessResult(exit_code=0, output="Todo implemented and committed")


class FailingRunner(FakeRunner):
    async def run(self, **arguments) -> ProcessResult:
        self.calls.append(arguments)
        raise AgentProcessError(
            "codex exited with status 1",
            output="Tests failed",
            exit_code=1,
        )


async def test_service_runs_only_planned_todo_and_advances_status(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'agent.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    repository = tmp_path / "repositories" / "shoppa"
    runner = FakeRunner(repository)
    github = FakeGithub()
    settings = AgentSettings(
        enabled=True,
        provider="claude",
        push_enabled=True,
    )

    async with session_factory() as session:
        project = Project(
            id="shoppa",
            company_id="company",
            name="Shoppa",
            path="/display-only/shoppa",
            repository_slug="shoppa",
        )
        company = Company(id="company", name="Company")
        local_agent = LocalAgent(
            id="company-default-agent",
            company_id="company",
            name="Company default",
            provider=AgentProvider.CODEX,
            model_name="test-model",
            enabled=True,
            is_default=True,
            command="codex",
            repository_root=str(repository.parent),
            git_command="git",
            git_remote="origin",
            timeout_seconds=3_600,
            max_output_characters=100_000,
            push_enabled=True,
        )
        version = ProjectVersion(
            id="shoppa-v1",
            project_id=project.id,
            name="v1",
            summary="First release",
            status=VersionStatus.PENDING,
            branch_name="version/shoppa-v1",
        )
        todo = ProjectTodo(
            id="todo-add-cart-42",
            project_id=project.id,
            version_id=version.id,
            issue_number=42,
            title="Add cart",
            description="Implement a shopping cart.",
            status=TodoStatus.PLANNED,
            branch_name="todo/todo-add-cart-42",
        )
        session.add_all([company, local_agent, project, version, todo])
        await session.commit()

        service = AgentRunService(session, runner, settings, github)
        with pytest.raises(
            AgentRunConflictError,
            match="version must be ready or in-progress",
        ):
            await service.enqueue_planned_todo(
                CreateAgentRunRequest(
                    project_id=project.id,
                    todo_id=todo.id,
                    provider=AgentProvider.CODEX,
                )
            )

        version.status = VersionStatus.READY
        await session.commit()
        queued_run = await service.enqueue_planned_todo(
            CreateAgentRunRequest(
                project_id=project.id,
                todo_id=todo.id,
                provider=AgentProvider.CODEX,
            )
        )

        assert queued_run.status == AgentRunStatus.QUEUED
        assert queued_run.local_agent_id == local_agent.id
        assert queued_run.provider == AgentProvider.CODEX
        assert todo.status == TodoStatus.IN_PROGRESS
        with pytest.raises(AgentRunConflictError, match="Only planned todos"):
            await service.enqueue_planned_todo(
                CreateAgentRunRequest(
                    project_id=project.id,
                    todo_id=todo.id,
                    provider=AgentProvider.CODEX,
                )
            )

        run = await service.execute_queued_run(queued_run.id)

        assert run.status == AgentRunStatus.SUCCEEDED
        assert run.output == "Todo implemented and committed"
        assert run.repository_path == str(repository)
        assert runner.calls[0]["branch_name"] == todo.branch_name
        assert runner.calls[0]["folder_path"] == project.path
        assert "repository_slug" not in runner.calls[0]
        assert runner.calls[0]["push"] is True
        assert todo.status == TodoStatus.IN_PROGRESS
        assert todo.pull_request_number is None
        assert github.pull_requests == []
        merge_task = await session.scalar(
            select(GithubWorkflowTask).where(
                GithubWorkflowTask.todo_id == todo.id,
                GithubWorkflowTask.action == GithubTaskAction.MERGE_TODO,
            )
        )
        assert merge_task is not None
        assert merge_task.status == GithubTaskStatus.PENDING
        assert version.status == VersionStatus.IN_PROGRESS

        with pytest.raises(AgentRunConflictError, match="Only planned todos"):
            await service.enqueue_planned_todo(
                CreateAgentRunRequest(
                    project_id=project.id,
                    todo_id=todo.id,
                )
            )

        failed_todo = ProjectTodo(
            id="todo-add-checkout-43",
            project_id=project.id,
            version_id=version.id,
            issue_number=43,
            title="Add checkout",
            description="Implement checkout.",
            status=TodoStatus.PLANNED,
            branch_name="todo/todo-add-checkout-43",
        )
        session.add(failed_todo)
        await session.commit()
        failing_service = AgentRunService(
            session,
            FailingRunner(repository),
            settings,
            github,
        )

        failed_queued_run = await failing_service.enqueue_planned_todo(
            CreateAgentRunRequest(
                project_id=project.id,
                todo_id=failed_todo.id,
                provider=AgentProvider.CODEX,
            )
        )
        failed_run = await failing_service.execute_queued_run(
            failed_queued_run.id
        )

        assert failed_run.status == AgentRunStatus.FAILED
        assert failed_run.exit_code == 1
        assert failed_todo.status == TodoStatus.FAILED

    await engine.dispose()
