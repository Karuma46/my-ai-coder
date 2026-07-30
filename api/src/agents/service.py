from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import CompanyMembership
from src.agents.config import AgentSettings
from src.agents.exceptions import (
    AgentConfigurationError,
    AgentProcessError,
    AgentRepositoryError,
    AgentRunConflictError,
    AgentRunNotFoundError,
)
from src.agents.models import AgentRun, LocalAgent
from src.agents.runner import LocalAgentRunner
from src.agents.schemas import (
    AgentProvider,
    AgentRunStatus,
    CreateAgentRunRequest,
    CreateLocalAgentRequest,
    UpdateLocalAgentRequest,
)
from src.github.models import GithubWorkflowTask
from src.github.service import GithubService
from src.github.workflow import (
    GithubTaskAction,
    GithubTaskStatus,
    enqueue_github_task,
)
from src.projects.models import Project, ProjectTodo
from src.projects.schemas import TodoStatus, VersionStatus


class AgentRunService:
    def __init__(
        self,
        session: AsyncSession,
        runner: LocalAgentRunner,
        settings: AgentSettings,
        github: GithubService,
        user_id: str | None = None,
    ) -> None:
        self.session = session
        self.runner = runner
        self.settings = settings
        self.github = github
        self.user_id = user_id

    async def _membership(self, company_id: str) -> CompanyMembership | None:
        if self.user_id is None:
            return None
        return await self.session.get(CompanyMembership, (company_id, self.user_id))

    async def list_local_agents(self, company_id: str) -> list[LocalAgent]:
        if await self._membership(company_id) is None:
            raise AgentRunNotFoundError("Company was not found")
        result = await self.session.scalars(
            select(LocalAgent)
            .where(LocalAgent.company_id == company_id)
            .order_by(LocalAgent.created_at, LocalAgent.name)
        )
        return list(result)

    async def create_local_agent(
        self, company_id: str, payload: CreateLocalAgentRequest
    ) -> LocalAgent:
        membership = await self._membership(company_id)
        if membership is None:
            raise AgentRunNotFoundError("Company was not found")
        if membership.role != "owner":
            raise AgentRunConflictError("Only company owners can configure local agents")
        existing_agent = await self.session.scalar(
            select(LocalAgent.id).where(LocalAgent.company_id == company_id).limit(1)
        )
        should_be_default = payload.is_default or existing_agent is None
        if should_be_default:
            await self.session.execute(
                update(LocalAgent)
                .where(LocalAgent.company_id == company_id)
                .values(is_default=False)
            )
        values = payload.model_dump(mode="json")
        values["is_default"] = should_be_default
        agent = LocalAgent(
            id=str(uuid4()),
            company_id=company_id,
            **values,
        )
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def update_local_agent(
        self, company_id: str, agent_id: str, payload: UpdateLocalAgentRequest
    ) -> LocalAgent:
        membership = await self._membership(company_id)
        agent = await self.session.scalar(
            select(LocalAgent).where(LocalAgent.id == agent_id, LocalAgent.company_id == company_id)
        )
        if membership is None or agent is None:
            raise AgentRunNotFoundError("Local agent was not found")
        if membership.role != "owner":
            raise AgentRunConflictError("Only company owners can configure local agents")
        changes = payload.model_dump(mode="json", exclude_unset=True)
        if changes.get("is_default") is True:
            await self.session.execute(
                update(LocalAgent)
                .where(
                    LocalAgent.company_id == company_id,
                    LocalAgent.id != agent_id,
                )
                .values(is_default=False)
            )
        elif changes.get("is_default") is False and agent.is_default:
            raise AgentRunConflictError(
                "Choose another default agent before removing this default"
            )
        for field, value in changes.items():
            setattr(agent, field, value)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def delete_local_agent(self, company_id: str, agent_id: str) -> None:
        membership = await self._membership(company_id)
        agent = await self.session.scalar(
            select(LocalAgent).where(LocalAgent.id == agent_id, LocalAgent.company_id == company_id)
        )
        if membership is None or agent is None:
            raise AgentRunNotFoundError("Local agent was not found")
        if membership.role != "owner":
            raise AgentRunConflictError("Only company owners can configure local agents")
        if agent.is_default:
            replacement = await self.session.scalar(
                select(LocalAgent)
                .where(
                    LocalAgent.company_id == company_id,
                    LocalAgent.id != agent_id,
                )
                .order_by(LocalAgent.created_at, LocalAgent.id)
                .limit(1)
            )
            if replacement is not None:
                replacement.is_default = True
        await self.session.delete(agent)
        await self.session.commit()

    @staticmethod
    def _settings_for(agent: LocalAgent) -> AgentSettings:
        commands = {
            "codex_command": agent.command if agent.provider == AgentProvider.CODEX else "codex",
            "claude_command": (
                agent.command if agent.provider == AgentProvider.CLAUDE else "claude"
            ),
            "ollama_command": (
                agent.command if agent.provider == AgentProvider.OLLAMA else "codex"
            ),
        }
        return AgentSettings(
            enabled=agent.enabled,
            provider=agent.provider,
            model_name=agent.model_name,
            git_command=agent.git_command,
            git_remote=agent.git_remote,
            timeout_seconds=agent.timeout_seconds,
            max_output_characters=agent.max_output_characters,
            push_enabled=agent.push_enabled,
            **commands,
        )

    async def _company_agent(
        self,
        company_id: str,
        agent_id: str | None = None,
    ) -> LocalAgent:
        statement = select(LocalAgent).where(LocalAgent.company_id == company_id)
        if agent_id is not None:
            statement = statement.where(LocalAgent.id == agent_id)
        else:
            statement = statement.order_by(
                LocalAgent.is_default.desc(),
                LocalAgent.created_at,
                LocalAgent.id,
            )
        agent = await self.session.scalar(statement.limit(1))
        if agent is None:
            message = (
                "Local agent was not found"
                if agent_id is not None
                else "No local agent is configured for this project's company"
            )
            raise AgentConfigurationError(message)
        if not agent.enabled:
            raise AgentConfigurationError("The selected local agent is disabled")
        return agent

    async def is_todo_branch_ready(self, todo_id: str) -> bool:
        task = await self.session.scalar(
            select(GithubWorkflowTask).where(
                GithubWorkflowTask.todo_id == todo_id,
                GithubWorkflowTask.action == GithubTaskAction.CREATE_TODO_BRANCH,
            )
        )
        return task is not None and task.status == GithubTaskStatus.SUCCEEDED

    async def enqueue_planned_todo(self, payload: CreateAgentRunRequest) -> AgentRun:
        if not payload.push:
            raise AgentConfigurationError(
                "Agent completion requires pushing the commit before creating a pull request"
            )
        project_statement = select(Project).where(Project.id == payload.project_id)
        if self.user_id is not None:
            project_statement = project_statement.join(
                CompanyMembership,
                CompanyMembership.company_id == Project.company_id,
            ).where(CompanyMembership.user_id == self.user_id)
        project = await self.session.scalar(project_statement)
        todo = await self.session.scalar(
            select(ProjectTodo)
            .where(
                ProjectTodo.id == payload.todo_id,
                ProjectTodo.project_id == payload.project_id,
            )
            .options(selectinload(ProjectTodo.version))
        )
        if project is None or todo is None:
            raise AgentRunNotFoundError("Project or todo was not found")
        configured_agent = await self._company_agent(
            project.company_id, payload.local_agent_id
        )
        if payload.push and not configured_agent.push_enabled:
            raise AgentConfigurationError("Pushes are disabled for the selected local agent")
        if TodoStatus(todo.status) is not TodoStatus.PLANNED:
            raise AgentRunConflictError("Only planned todos can be sent to a local agent")
        if todo.version is None or todo.branch_name is None:
            raise AgentRunConflictError("Todo must belong to a version and have a GitHub branch")
        if VersionStatus(todo.version.status) not in {
            VersionStatus.READY,
            VersionStatus.IN_PROGRESS,
        }:
            raise AgentRunConflictError(
                "Todo version must be ready or in-progress before agent execution"
            )

        claimed_at = datetime.now(UTC)
        claim = await self.session.execute(
            update(ProjectTodo)
            .where(
                ProjectTodo.id == todo.id,
                ProjectTodo.project_id == project.id,
                ProjectTodo.status == TodoStatus.PLANNED,
            )
            .values(
                status=TodoStatus.IN_PROGRESS,
                updated_at=claimed_at,
            )
            .returning(ProjectTodo.id)
            .execution_options(synchronize_session=False)
        )
        if claim.scalar_one_or_none() is None:
            await self.session.rollback()
            raise AgentRunConflictError("Todo was already claimed by another runner")
        todo.status = TodoStatus.IN_PROGRESS
        todo.updated_at = claimed_at
        await enqueue_github_task(
            self.session,
            project_id=project.id,
            version_id=todo.version_id,
            todo_id=todo.id,
            action=GithubTaskAction.CREATE_TODO_BRANCH,
        )

        provider = AgentProvider(configured_agent.provider)
        selected_runner = self.runner.with_settings(self._settings_for(configured_agent))
        repository = selected_runner.project_path(project.path)
        run = AgentRun(
            id=str(uuid4()),
            project_id=project.id,
            todo_id=todo.id,
            local_agent_id=configured_agent.id,
            provider=provider,
            status=AgentRunStatus.QUEUED,
            branch_name=todo.branch_name,
            repository_path=str(repository),
            pushed=False,
            output="",
            started_at=claimed_at,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def execute_queued_run(self, run_id: str) -> AgentRun:
        run = await self.session.get(AgentRun, run_id)
        if run is None:
            raise AgentRunNotFoundError(f"Agent run '{run_id}' was not found")
        if AgentRunStatus(run.status) is not AgentRunStatus.QUEUED:
            raise AgentRunConflictError(f"Agent run '{run_id}' is {run.status}, not queued")

        project = await self.session.get(Project, run.project_id)
        todo = await self.session.scalar(
            select(ProjectTodo)
            .where(
                ProjectTodo.id == run.todo_id,
                ProjectTodo.project_id == run.project_id,
            )
            .options(selectinload(ProjectTodo.version))
        )
        if project is None or todo is None:
            raise AgentRunNotFoundError("Project or todo was not found")
        if todo.version is None or todo.branch_name is None:
            return await self._fail_run(
                run,
                todo,
                AgentRunConflictError("Todo must belong to a version and have a GitHub branch"),
            )

        run.status = AgentRunStatus.RUNNING
        await self.session.commit()

        try:
            configured_agent = await self._company_agent(
                project.company_id,
                run.local_agent_id,
            )
            selected_runner = self.runner.with_settings(
                self._settings_for(configured_agent)
            )
            run.provider = configured_agent.provider
            result = await selected_runner.run(
                folder_path=project.path,
                branch_name=todo.branch_name,
                provider=AgentProvider(run.provider),
                title=todo.title,
                description=todo.description,
                push=True,
            )
            run.exit_code = result.exit_code
            run.output = result.output
            run.pushed = True
        except AgentProcessError as exc:
            return await self._fail_run(run, todo, exc)
        except (
            AgentConfigurationError,
            AgentRepositoryError,
            AgentRunConflictError,
        ) as exc:
            return await self._fail_run(run, todo, exc)

        run.status = AgentRunStatus.SUCCEEDED
        run.completed_at = datetime.now(UTC)
        todo.updated_at = run.completed_at
        await enqueue_github_task(
            self.session,
            project_id=project.id,
            version_id=todo.version_id,
            todo_id=todo.id,
            action=GithubTaskAction.MERGE_TODO,
        )
        if todo.version.status == VersionStatus.READY:
            todo.version.status = VersionStatus.IN_PROGRESS
            todo.version.updated_at = run.completed_at
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def release_queued_run(self, run_id: str, error: str) -> AgentRun:
        run = await self.session.get(AgentRun, run_id)
        if run is None:
            raise AgentRunNotFoundError(f"Agent run '{run_id}' was not found")
        if AgentRunStatus(run.status) is not AgentRunStatus.QUEUED:
            return run

        todo = await self.session.scalar(
            select(ProjectTodo).where(
                ProjectTodo.id == run.todo_id,
                ProjectTodo.project_id == run.project_id,
            )
        )
        completed_at = datetime.now(UTC)
        run.status = AgentRunStatus.FAILED
        run.error = error
        run.completed_at = completed_at
        if todo is not None and TodoStatus(todo.status) is TodoStatus.IN_PROGRESS:
            todo.status = TodoStatus.PLANNED
            todo.updated_at = completed_at
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def fail_active_run(self, run_id: str, error: str) -> AgentRun:
        run = await self.session.get(AgentRun, run_id)
        if run is None:
            raise AgentRunNotFoundError(f"Agent run '{run_id}' was not found")
        if AgentRunStatus(run.status) in {
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.FAILED,
        }:
            return run

        todo = await self.session.scalar(
            select(ProjectTodo).where(
                ProjectTodo.id == run.todo_id,
                ProjectTodo.project_id == run.project_id,
            )
        )
        completed_at = datetime.now(UTC)
        run.status = AgentRunStatus.FAILED
        run.error = error
        run.completed_at = completed_at
        if todo is not None:
            todo.status = TodoStatus.FAILED
            todo.updated_at = completed_at
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def _fail_run(
        self,
        run: AgentRun,
        todo: ProjectTodo,
        exc: Exception,
    ) -> AgentRun:
        completed_at = datetime.now(UTC)
        run.status = AgentRunStatus.FAILED
        run.error = str(exc)
        run.completed_at = completed_at
        if isinstance(exc, AgentProcessError):
            run.exit_code = exc.exit_code
            run.output = exc.output
        todo.status = TodoStatus.FAILED
        todo.updated_at = completed_at
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> AgentRun:
        statement = select(AgentRun).where(AgentRun.id == run_id)
        if self.user_id is not None:
            statement = (
                statement.join(Project, Project.id == AgentRun.project_id)
                .join(
                    CompanyMembership,
                    CompanyMembership.company_id == Project.company_id,
                )
                .where(CompanyMembership.user_id == self.user_id)
            )
        run = await self.session.scalar(statement)
        if run is None:
            raise AgentRunNotFoundError(f"Agent run '{run_id}' was not found")
        return run
