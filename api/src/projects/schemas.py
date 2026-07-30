from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class StrictRequest(APIModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )


class VersionStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    RELEASED = "released"


class TodoStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    FAILED = "failed"
    DONE = "done"


class ProjectTodoResponse(APIModel):
    id: str
    project_id: str
    version_id: str | None
    issue_number: int
    issue_url: str | None
    pull_request_number: int | None
    pull_request_url: str | None
    title: str
    description: str
    status: TodoStatus
    is_merged: bool
    merge_commit_sha: str | None = None
    merged_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectVersionResponse(APIModel):
    id: str
    project_id: str
    name: str
    summary: str
    status: VersionStatus
    todos: list[ProjectTodoResponse]
    created_at: datetime
    updated_at: datetime
    released_at: datetime | None


class ProjectResponse(APIModel):
    id: str
    company_id: str
    name: str
    path: str
    versions: list[ProjectVersionResponse]
    wip_todos: list[ProjectTodoResponse]
    created_at: datetime
    updated_at: datetime


class ProjectSummaryResponse(APIModel):
    id: str
    company_id: str
    name: str
    path: str
    version_count: int
    wip_todo_count: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(APIModel):
    items: list[ProjectSummaryResponse]
    next_cursor: str | None


class CreateProjectRequest(StrictRequest):
    company_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=2_048)


class UpdateProjectRequest(StrictRequest):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    path: str | None = Field(default=None, min_length=1, max_length=2_048)

    @model_validator(mode="after")
    def require_update(self) -> "UpdateProjectRequest":
        if not self.model_fields_set:
            raise ValueError("At least one project field must be provided")
        return self


class CreateVersionRequest(StrictRequest):
    name: str = Field(min_length=1, max_length=60)
    summary: str = Field(min_length=1, max_length=1_000)


class UpdateVersionRequest(StrictRequest):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    summary: str | None = Field(default=None, min_length=1, max_length=1_000)
    status: VersionStatus | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateVersionRequest":
        if not self.model_fields_set:
            raise ValueError("At least one version field must be provided")
        if self.status is VersionStatus.RELEASED:
            raise ValueError("Use the release endpoint to release a version")
        return self


class ReleaseVersionRequest(StrictRequest):
    release_notes: str = Field(default="", max_length=10_000)


class CreateVersionTodoRequest(StrictRequest):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=10_000)
    status: Literal[TodoStatus.DRAFT] = TodoStatus.DRAFT


class CreateWipTodoRequest(StrictRequest):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=10_000)


class UpdateTodoRequest(StrictRequest):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    status: TodoStatus | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateTodoRequest":
        if not self.model_fields_set:
            raise ValueError("At least one todo field must be provided")
        return self


class AssignTodoRequest(StrictRequest):
    version_id: str = Field(min_length=1)


class MergeTodoRequest(StrictRequest):
    merge_commit_sha: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{40}$")
