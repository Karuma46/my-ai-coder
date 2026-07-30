from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import CompanyMembership
from src.github.schemas import (
    IssueClose,
    IssueCreate,
    PullRequestCreate,
    PullRequestMerge,
)
from src.github.service import GithubService
from src.github.workflow import GithubTaskAction, enqueue_github_task
from src.projects.exceptions import (
    ProjectConflictError,
    ProjectGithubReferenceError,
    ProjectNotFoundError,
)
from src.projects.models import Project, ProjectTodo, ProjectVersion
from src.projects.schemas import (
    AssignTodoRequest,
    CreateProjectRequest,
    CreateVersionRequest,
    CreateVersionTodoRequest,
    CreateWipTodoRequest,
    MergeTodoRequest,
    ReleaseVersionRequest,
    TodoStatus,
    UpdateProjectRequest,
    UpdateTodoRequest,
    UpdateVersionRequest,
    VersionStatus,
)
from src.projects.utils import (
    extract_github_number,
    extract_github_value,
    repository_slug,
    slugify,
)


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        github: GithubService,
        user_id: str,
    ) -> None:
        self.session = session
        self.github = github
        self.user_id = user_id

    async def list_projects(
        self,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        version_count = (
            select(func.count(ProjectVersion.id))
            .where(ProjectVersion.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )
        wip_todo_count = (
            select(func.count(ProjectTodo.id))
            .where(
                ProjectTodo.project_id == Project.id,
                ProjectTodo.version_id.is_(None),
            )
            .correlate(Project)
            .scalar_subquery()
        )
        statement = (
            select(
                Project.id,
                Project.company_id,
                Project.name,
                Project.path,
                version_count.label("version_count"),
                wip_todo_count.label("wip_todo_count"),
                Project.created_at,
                Project.updated_at,
            )
            .join(
                CompanyMembership,
                CompanyMembership.company_id == Project.company_id,
            )
            .where(CompanyMembership.user_id == self.user_id)
            .order_by(Project.id)
            .limit(limit + 1)
        )
        if cursor is not None:
            statement = statement.where(Project.id > cursor)

        rows = [dict(row) for row in (await self.session.execute(statement)).mappings()]
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = rows[-1]["id"] if has_more and rows else None
        return rows, next_cursor

    async def create_project(self, payload: CreateProjectRequest) -> Project:
        await self._require_company_membership(payload.company_id)
        repo = repository_slug(payload.path, payload.name)
        self.github.validate_repository(repo)
        project_id = slugify(repo, fallback="project")
        if await self.session.get(Project, project_id) is not None:
            raise ProjectConflictError(f"Project '{project_id}' already exists")

        project = Project(
            id=project_id,
            company_id=payload.company_id,
            name=payload.name,
            path=payload.path,
            repository_slug=repo,
        )
        self.session.add(project)
        await self._commit()
        return await self.get_project(project_id)

    async def get_project(self, project_id: str) -> Project:
        project = await self.session.scalar(
            select(Project)
            .join(
                CompanyMembership,
                CompanyMembership.company_id == Project.company_id,
            )
            .where(
                Project.id == project_id,
                CompanyMembership.user_id == self.user_id,
            )
            .options(
                selectinload(Project.versions).selectinload(ProjectVersion.todos),
                selectinload(Project.todos),
            )
        )
        if project is None:
            raise ProjectNotFoundError(f"Project '{project_id}' was not found")
        return project

    async def _require_company_membership(self, company_id: str) -> None:
        membership = await self.session.get(
            CompanyMembership,
            (company_id, self.user_id),
        )
        if membership is None:
            raise ProjectNotFoundError("Company membership was not found")

    async def update_project(
        self,
        project_id: str,
        payload: UpdateProjectRequest,
    ) -> Project:
        project = await self.get_project(project_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        project.updated_at = datetime.now(UTC)
        await self._commit()
        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> None:
        project = await self.get_project(project_id)
        await self.session.delete(project)
        await self._commit()

    async def create_version(
        self,
        project_id: str,
        payload: CreateVersionRequest,
    ) -> ProjectVersion:
        project = await self.get_project(project_id)
        version_id = f"{project.id}-{slugify(payload.name, fallback='version')}"
        if await self.session.get(ProjectVersion, version_id) is not None:
            raise ProjectConflictError(f"Version '{payload.name}' already exists")

        branch_name = f"version/{version_id}"
        version = ProjectVersion(
            id=version_id,
            project_id=project.id,
            name=payload.name,
            summary=payload.summary,
            status=VersionStatus.PENDING,
            branch_name=branch_name,
        )
        self.session.add(version)
        project.updated_at = datetime.now(UTC)
        await self._commit()
        return await self.get_version(project_id, version_id)

    async def get_version(self, project_id: str, version_id: str) -> ProjectVersion:
        version = await self.session.scalar(
            select(ProjectVersion)
            .join(Project, Project.id == ProjectVersion.project_id)
            .join(
                CompanyMembership,
                CompanyMembership.company_id == Project.company_id,
            )
            .where(
                ProjectVersion.id == version_id,
                ProjectVersion.project_id == project_id,
                CompanyMembership.user_id == self.user_id,
            )
            .options(selectinload(ProjectVersion.todos))
        )
        if version is None:
            raise ProjectNotFoundError(f"Version '{version_id}' was not found")
        return version

    async def update_version(
        self,
        project_id: str,
        version_id: str,
        payload: UpdateVersionRequest,
    ) -> ProjectVersion:
        version = await self.get_version(project_id, version_id)
        if version.status == VersionStatus.RELEASED:
            raise ProjectConflictError("Released versions are immutable")

        values = payload.model_dump(exclude_unset=True)
        requested_status = values.pop("status", None)
        for field, value in values.items():
            setattr(version, field, value)

        if requested_status is not None:
            await self._transition_version(version, VersionStatus(requested_status))

        version.updated_at = datetime.now(UTC)
        await self._commit()
        return await self.get_version(project_id, version_id)

    async def delete_version(self, project_id: str, version_id: str) -> None:
        version = await self.get_version(project_id, version_id)
        if version.status != VersionStatus.PENDING:
            raise ProjectConflictError("Only a pending version can be deleted")
        for todo in version.todos:
            await self.session.delete(todo)
        await self.session.delete(version)
        await self._commit()

    async def release_version(
        self,
        project_id: str,
        version_id: str,
        payload: ReleaseVersionRequest,
    ) -> ProjectVersion:
        version = await self.get_version(project_id, version_id)
        if version.status != VersionStatus.COMPLETE:
            raise ProjectConflictError("Only a complete version can be released")
        self._require_completed_todos(version)

        project = await self.get_project(project_id)
        await self._ensure_version_pull_request(project, version, payload.release_notes)
        merge_result = await self.github.merge_pull_request(
            PullRequestMerge(
                repo=project.repository_slug,
                pull_number=version.pull_request_number,
                merge_method="squash",
            )
        )
        version.merge_commit_sha = self._optional_string(
            extract_github_value(merge_result, ("sha", "merge_commit_sha"))
        )
        version.status = VersionStatus.RELEASED
        version.released_at = datetime.now(UTC)
        version.updated_at = version.released_at
        await self._commit()
        return await self.get_version(project_id, version_id)

    async def create_version_todo(
        self,
        project_id: str,
        version_id: str,
        payload: CreateVersionTodoRequest,
    ) -> ProjectTodo:
        project = await self.get_project(project_id)
        version = await self.get_version(project_id, version_id)
        self._require_active_version(version)

        todo = await self._create_issue_backed_todo(
            project=project,
            version=version,
            title=payload.title,
            description=payload.description,
        )
        await self._commit()
        return await self.get_todo(project_id, todo.id)

    async def create_wip_todo(
        self,
        project_id: str,
        payload: CreateWipTodoRequest,
    ) -> ProjectTodo:
        project = await self.get_project(project_id)
        todo = await self._create_issue_backed_todo(
            project=project,
            version=None,
            title=payload.title,
            description=payload.description,
        )
        await self._commit()
        return await self.get_todo(project_id, todo.id)

    async def get_todo(self, project_id: str, todo_id: str) -> ProjectTodo:
        todo = await self.session.scalar(
            select(ProjectTodo)
            .join(Project, Project.id == ProjectTodo.project_id)
            .join(
                CompanyMembership,
                CompanyMembership.company_id == Project.company_id,
            )
            .where(
                ProjectTodo.id == todo_id,
                ProjectTodo.project_id == project_id,
                CompanyMembership.user_id == self.user_id,
            )
            .options(selectinload(ProjectTodo.version))
        )
        if todo is None:
            raise ProjectNotFoundError(f"Todo '{todo_id}' was not found")
        return todo

    async def update_todo(
        self,
        project_id: str,
        todo_id: str,
        payload: UpdateTodoRequest,
    ) -> ProjectTodo:
        todo = await self.get_todo(project_id, todo_id)
        if todo.is_merged:
            raise ProjectConflictError("Merged todos are immutable")
        if todo.version is None and payload.status not in {None, TodoStatus.DRAFT}:
            raise ProjectConflictError("Assign a WIP todo before changing its workflow status")
        if todo.version is not None and todo.version.status == VersionStatus.RELEASED:
            raise ProjectConflictError("Todos in a released version are immutable")

        values = payload.model_dump(exclude_unset=True)
        requested_status = values.pop("status", None)
        for field, value in values.items():
            setattr(todo, field, value)

        if requested_status is not None:
            current_status = TodoStatus(todo.status)
            requested_status = TodoStatus(requested_status)
            self._validate_todo_transition(current_status, requested_status)
            if current_status is TodoStatus.DRAFT and requested_status is TodoStatus.PLANNED:
                if todo.version is None:
                    raise ProjectConflictError("Assign a WIP todo before marking it as planned")
                project = await self.get_project(project_id)
                await self._plan_todo(project, todo, todo.version)
            else:
                todo.status = requested_status
            if todo.status is TodoStatus.DONE and todo.version is not None:
                project = await self.get_project(project_id)
                await self._ensure_todo_pull_request(project, todo, todo.version)
            elif todo.status is TodoStatus.IN_PROGRESS and todo.version is not None:
                todo.version.status = VersionStatus.IN_PROGRESS
                await enqueue_github_task(
                    self.session,
                    project_id=todo.project_id,
                    version_id=todo.version_id,
                    todo_id=todo.id,
                    action=GithubTaskAction.CREATE_TODO_BRANCH,
                )

        todo.updated_at = datetime.now(UTC)
        await self._commit()
        return await self.get_todo(project_id, todo_id)

    async def delete_todo(self, project_id: str, todo_id: str) -> None:
        todo = await self.get_todo(project_id, todo_id)
        if todo.status != TodoStatus.DRAFT:
            raise ProjectConflictError("Only a draft todo can be deleted")
        await self.session.delete(todo)
        await self._commit()

    async def assign_todo(
        self,
        project_id: str,
        todo_id: str,
        payload: AssignTodoRequest,
    ) -> ProjectTodo:
        project = await self.get_project(project_id)
        todo = await self.get_todo(project_id, todo_id)
        if todo.version_id is not None or todo.status != TodoStatus.DRAFT:
            raise ProjectConflictError("Only a draft WIP todo can be assigned")

        version = await self.get_version(project_id, payload.version_id)
        self._require_active_version(version)
        todo.version_id = version.id
        todo.version = version
        await self._plan_todo(project, todo, version)
        todo.updated_at = datetime.now(UTC)
        await self._commit()
        return await self.get_todo(project_id, todo_id)

    async def merge_todo(
        self,
        project_id: str,
        todo_id: str,
        payload: MergeTodoRequest,
    ) -> ProjectTodo:
        project = await self.get_project(project_id)
        todo = await self.get_todo(project_id, todo_id)
        if todo.version is None:
            raise ProjectConflictError("A WIP todo cannot be merged")
        if todo.status != TodoStatus.DONE:
            raise ProjectConflictError("Only a done todo can be merged")
        if todo.is_merged:
            await self._close_todo_issue(project, todo)
            return todo

        await self._ensure_todo_pull_request(project, todo, todo.version)
        result = await self.github.merge_pull_request(
            PullRequestMerge(
                repo=project.repository_slug,
                pull_number=todo.pull_request_number,
                merge_method="squash",
            )
        )
        todo.is_merged = True
        todo.merge_commit_sha = payload.merge_commit_sha or self._optional_string(
            extract_github_value(result, ("sha", "merge_commit_sha"))
        )
        todo.merged_at = datetime.now(UTC)
        todo.updated_at = todo.merged_at
        await self._commit()
        await self._close_todo_issue(project, todo)
        return await self.get_todo(project_id, todo_id)

    async def _close_todo_issue(
        self,
        project: Project,
        todo: ProjectTodo,
    ) -> None:
        await self.github.close_issue(
            IssueClose(
                repo=project.repository_slug,
                issue_number=todo.issue_number,
            )
        )

    async def _create_issue_backed_todo(
        self,
        *,
        project: Project,
        version: ProjectVersion | None,
        title: str,
        description: str,
    ) -> ProjectTodo:
        issue_result = await self.github.create_issue(
            IssueCreate(
                repo=project.repository_slug,
                title=title,
                description=description,
            )
        )
        issue_number = extract_github_number(
            issue_result,
            ("number", "issue_number"),
            url_segment="issues",
        )
        if issue_number is None:
            raise ProjectGithubReferenceError("GitHub did not return an issue number")
        issue_url = self._optional_string(
            extract_github_value(issue_result, ("url", "html_url", "issue_url"))
        )

        todo_id = f"todo-{slugify(title, fallback='work')}-{issue_number}"

        todo = ProjectTodo(
            id=todo_id,
            project_id=project.id,
            version_id=version.id if version is not None else None,
            issue_number=issue_number,
            issue_url=issue_url,
            title=title,
            description=description,
            branch_name=None,
        )
        self.session.add(todo)
        project.updated_at = datetime.now(UTC)
        return todo

    async def _transition_version(
        self,
        version: ProjectVersion,
        requested_status: VersionStatus,
    ) -> None:
        current = VersionStatus(version.status)
        if requested_status == current:
            return
        if requested_status is VersionStatus.PENDING or current is VersionStatus.COMPLETE:
            raise ProjectConflictError(f"Cannot move a {current} version to {requested_status}")
        if requested_status is VersionStatus.READY:
            if current is not VersionStatus.PENDING:
                raise ProjectConflictError("Only a pending version can become ready")
            version.status = requested_status
            await enqueue_github_task(
                self.session,
                project_id=version.project_id,
                version_id=version.id,
                action=GithubTaskAction.CREATE_VERSION_BRANCH,
            )
            return
        if requested_status is VersionStatus.IN_PROGRESS:
            if current not in {VersionStatus.PENDING, VersionStatus.READY}:
                raise ProjectConflictError("Only a pending or ready version can start")
            version.status = requested_status
            return
        if requested_status is VersionStatus.COMPLETE:
            self._require_completed_todos(version)
            project = await self.get_project(version.project_id)
            await self._ensure_version_pull_request(project, version, "")
            version.status = requested_status

    def _require_active_version(self, version: ProjectVersion) -> None:
        if version.status not in {
            VersionStatus.PENDING,
            VersionStatus.READY,
            VersionStatus.IN_PROGRESS,
        }:
            raise ProjectConflictError("Todos can only be added to an active version")

    def _validate_todo_transition(
        self,
        current_status: str,
        requested_status: TodoStatus,
    ) -> None:
        current = TodoStatus(current_status)
        if requested_status is current:
            return
        allowed = {
            TodoStatus.DRAFT: {TodoStatus.PLANNED},
            TodoStatus.PLANNED: {
                TodoStatus.IN_PROGRESS,
                TodoStatus.BLOCKED,
                TodoStatus.FAILED,
                TodoStatus.DONE,
            },
            TodoStatus.IN_PROGRESS: {
                TodoStatus.BLOCKED,
                TodoStatus.FAILED,
                TodoStatus.DONE,
            },
            TodoStatus.BLOCKED: {
                TodoStatus.IN_PROGRESS,
                TodoStatus.FAILED,
                TodoStatus.DONE,
            },
            TodoStatus.FAILED: {
                TodoStatus.PLANNED,
                TodoStatus.IN_PROGRESS,
                TodoStatus.DONE,
            },
            TodoStatus.DONE: set(),
        }
        if requested_status not in allowed[current]:
            raise ProjectConflictError(f"Cannot move a todo from {current} to {requested_status}")

    async def _plan_todo(
        self,
        project: Project,
        todo: ProjectTodo,
        version: ProjectVersion,
    ) -> None:
        if todo.branch_name is None:
            todo.branch_name = f"todo/{todo.id}"
        todo.status = TodoStatus.PLANNED

    def _require_completed_todos(self, version: ProjectVersion) -> None:
        if not version.todos:
            raise ProjectConflictError("A version must contain at least one todo")
        if any(todo.status != TodoStatus.DONE or not todo.is_merged for todo in version.todos):
            raise ProjectConflictError("All version todos must be done and merged")

    async def _ensure_todo_pull_request(
        self,
        project: Project,
        todo: ProjectTodo,
        version: ProjectVersion,
    ) -> None:
        if todo.pull_request_number is not None:
            return
        if todo.branch_name is None:
            raise ProjectConflictError("Todo branch reference is missing")

        result = await self.github.create_pull_request(
            PullRequestCreate(
                repo=project.repository_slug,
                title=todo.title,
                head=todo.branch_name,
                base=version.branch_name,
                description=f"Closes #{todo.issue_number}\n\n{todo.description}",
                draft=False,
            )
        )
        todo.pull_request_number = self._required_number(result, "pull request")
        todo.pull_request_url = self._optional_string(
            extract_github_value(result, ("url", "html_url", "pull_request_url"))
        )

    async def _ensure_version_pull_request(
        self,
        project: Project,
        version: ProjectVersion,
        release_notes: str,
    ) -> None:
        if version.pull_request_number is not None:
            return
        body = version.summary
        if release_notes:
            body = f"{body}\n\n## Release notes\n\n{release_notes}"
        result = await self.github.create_pull_request(
            PullRequestCreate(
                repo=project.repository_slug,
                title=f"Release {version.name}",
                head=version.branch_name,
                base=project.default_branch,
                description=body,
                draft=False,
            )
        )
        version.pull_request_number = self._required_number(result, "pull request")
        version.pull_request_url = self._optional_string(
            extract_github_value(result, ("url", "html_url", "pull_request_url"))
        )

    def _required_number(self, result: Any, reference: str) -> int:
        value = extract_github_number(
            result,
            ("number", "pull_number", "pullNumber"),
            url_segment="pull",
        )
        if value is None:
            raise ProjectGithubReferenceError(f"GitHub did not return a {reference} number")
        return value

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProjectConflictError(
                "The operation conflicts with existing project data"
            ) from exc
