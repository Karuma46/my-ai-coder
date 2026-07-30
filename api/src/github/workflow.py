from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agents.models import AgentRun
from src.agents.schemas import AgentRunStatus
from src.github.models import GithubWorkflowTask
from src.github.schemas import BranchCreate, IssueClose, PullRequestCreate, PullRequestMerge
from src.github.service import GithubService
from src.projects.models import Project, ProjectTodo, ProjectVersion
from src.projects.schemas import TodoStatus
from src.projects.utils import extract_github_number, extract_github_value


class GithubTaskAction(StrEnum):
    CREATE_VERSION_BRANCH = "create-version-branch"
    CREATE_TODO_BRANCH = "create-todo-branch"
    MERGE_TODO = "merge-todo"


class GithubTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


async def enqueue_github_task(
    session: AsyncSession,
    *,
    project_id: str,
    action: GithubTaskAction,
    version_id: str | None = None,
    todo_id: str | None = None,
) -> GithubWorkflowTask:
    existing = await session.scalar(
        select(GithubWorkflowTask).where(
            GithubWorkflowTask.action == action,
            GithubWorkflowTask.version_id == version_id,
            GithubWorkflowTask.todo_id == todo_id,
        )
    )
    if existing is not None:
        if existing.status == GithubTaskStatus.FAILED:
            existing.status = GithubTaskStatus.PENDING
            existing.error = None
            existing.completed_at = None
        return existing
    task = GithubWorkflowTask(
        id=str(uuid4()),
        project_id=project_id,
        version_id=version_id,
        todo_id=todo_id,
        action=action,
        status=GithubTaskStatus.PENDING,
    )
    session.add(task)
    return task


class GithubWorkflowExecutor:
    def __init__(self, session: AsyncSession, github: GithubService) -> None:
        self.session = session
        self.github = github

    async def execute(
        self, task_id: str
    ) -> tuple[GithubWorkflowTask, list[str], str | None]:
        task = await self.session.get(GithubWorkflowTask, task_id)
        if task is None:
            raise RuntimeError(f"GitHub workflow task '{task_id}' was not found")
        task.status = GithubTaskStatus.RUNNING
        task.attempts += 1
        task.updated_at = datetime.now(UTC)
        await self.session.commit()
        try:
            run_ids, completed_run_id = await self._execute_action(task)
            task.status = GithubTaskStatus.SUCCEEDED
            task.error = None
            task.completed_at = datetime.now(UTC)
            task.updated_at = task.completed_at
            await self.session.commit()
            return task, run_ids, completed_run_id
        except Exception as exc:
            task.status = GithubTaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = datetime.now(UTC)
            task.updated_at = task.completed_at
            if (
                task.action == GithubTaskAction.MERGE_TODO
                and task.todo_id is not None
            ):
                todo = await self.session.get(ProjectTodo, task.todo_id)
                if todo is not None:
                    todo.status = TodoStatus.DONE
                    todo.updated_at = task.completed_at
                await self.session.commit()
                return task, [], await self._completed_run_id(task)
            await self.session.commit()
            raise

    async def _execute_action(
        self, task: GithubWorkflowTask
    ) -> tuple[list[str], str | None]:
        action = GithubTaskAction(task.action)
        project = await self.session.get(Project, task.project_id)
        if project is None:
            raise RuntimeError("GitHub workflow project was not found")
        if action is GithubTaskAction.CREATE_VERSION_BRANCH:
            await self._create_version_branch(project, task)
            return [], None
        if action is GithubTaskAction.CREATE_TODO_BRANCH:
            await self._create_todo_branch(project, task)
            return await self._queued_run_ids(task), None
        await self._merge_todo(project, task)
        return [], await self._completed_run_id(task)

    async def _create_version_branch(
        self, project: Project, task: GithubWorkflowTask
    ) -> None:
        version = await self.session.get(ProjectVersion, task.version_id)
        if version is None:
            raise RuntimeError("Version was not found")
        await self.github.create_branch(
            BranchCreate(
                repo=project.repository_slug,
                branch=version.branch_name,
                from_branch=project.default_branch,
            )
        )

    async def _create_todo_branch(
        self, project: Project, task: GithubWorkflowTask
    ) -> None:
        todo = await self.session.scalar(
            select(ProjectTodo)
            .where(ProjectTodo.id == task.todo_id)
            .options(selectinload(ProjectTodo.version))
        )
        if todo is None or todo.version is None or todo.branch_name is None:
            raise RuntimeError("Todo branch configuration was not found")
        version_task = await self.session.scalar(
            select(GithubWorkflowTask).where(
                GithubWorkflowTask.action == GithubTaskAction.CREATE_VERSION_BRANCH,
                GithubWorkflowTask.version_id == todo.version_id,
            )
        )
        if (
            version_task is not None
            and version_task.status != GithubTaskStatus.SUCCEEDED
        ):
            raise RuntimeError("Version branch task has not completed")
        await self.github.create_branch(
            BranchCreate(
                repo=project.repository_slug,
                branch=todo.branch_name,
                from_branch=todo.version.branch_name,
            )
        )

    async def _queued_run_ids(self, task: GithubWorkflowTask) -> list[str]:
        result = await self.session.scalars(
            select(AgentRun.id).where(
                AgentRun.todo_id == task.todo_id,
                AgentRun.status == AgentRunStatus.QUEUED,
            )
        )
        return list(result)

    async def _completed_run_id(self, task: GithubWorkflowTask) -> str | None:
        return await self.session.scalar(
            select(AgentRun.id)
            .where(
                AgentRun.todo_id == task.todo_id,
                AgentRun.status == AgentRunStatus.SUCCEEDED,
            )
            .order_by(AgentRun.completed_at.desc(), AgentRun.id.desc())
            .limit(1)
        )

    async def _merge_todo(self, project: Project, task: GithubWorkflowTask) -> None:
        todo = await self.session.scalar(
            select(ProjectTodo)
            .where(ProjectTodo.id == task.todo_id)
            .options(selectinload(ProjectTodo.version))
        )
        if todo is None or todo.version is None or todo.branch_name is None:
            raise RuntimeError("Todo merge configuration was not found")
        if todo.pull_request_number is None:
            pull_request = await self.github.create_pull_request(
                PullRequestCreate(
                    repo=project.repository_slug,
                    title=todo.title,
                    head=todo.branch_name,
                    base=todo.version.branch_name,
                    description=f"Closes #{todo.issue_number}\n\n{todo.description}",
                    draft=False,
                )
            )
            todo.pull_request_number = extract_github_number(
                pull_request,
                ("number", "pull_number", "pullNumber"),
                url_segment="pull",
            )
            if todo.pull_request_number is None:
                raise RuntimeError("GitHub did not return a pull request number")
            pull_request_url = extract_github_value(
                pull_request, ("url", "html_url", "pull_request_url")
            )
            todo.pull_request_url = (
                str(pull_request_url) if pull_request_url is not None else None
            )
            await self.session.commit()
        if not todo.is_merged:
            merge_result = await self.github.merge_pull_request(
                PullRequestMerge(
                    repo=project.repository_slug,
                    pull_number=todo.pull_request_number,
                    merge_method="squash",
                )
            )
            todo.is_merged = True
            merge_sha = extract_github_value(
                merge_result, ("sha", "merge_commit_sha")
            )
            todo.merge_commit_sha = str(merge_sha) if merge_sha is not None else None
            todo.merged_at = datetime.now(UTC)
            await self.session.commit()
        await self.github.close_issue(
            IssueClose(repo=project.repository_slug, issue_number=todo.issue_number)
        )
        todo.status = TodoStatus.DONE
        todo.updated_at = datetime.now(UTC)
