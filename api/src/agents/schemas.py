from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from src.projects import schemas as project_schemas


class AgentProvider(StrEnum):
    CODEX = "codex"
    CLAUDE = "claude"
    OLLAMA = "ollama"


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CreateAgentRunRequest(project_schemas.StrictRequest):
    project_id: str = Field(min_length=1, max_length=120)
    todo_id: str = Field(min_length=1, max_length=220)
    provider: AgentProvider | None = None
    local_agent_id: str | None = Field(default=None, min_length=1, max_length=36)
    push: bool = True


class AgentRunResponse(project_schemas.APIModel):
    id: str
    project_id: str
    todo_id: str
    local_agent_id: str | None = None
    provider: AgentProvider
    status: AgentRunStatus
    branch_name: str
    repository_path: str
    pushed: bool
    exit_code: int | None
    output: str
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class LocalAgentFields(project_schemas.StrictRequest):
    name: str = Field(min_length=1, max_length=120)
    provider: AgentProvider
    model_name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    is_default: bool = False
    command: str = Field(min_length=1, max_length=2_048)
    git_command: str = Field(default="git", min_length=1, max_length=2_048)
    git_remote: str = Field(
        default="origin", min_length=1, max_length=255, pattern=r"^[A-Za-z0-9._-]+$"
    )
    timeout_seconds: int = Field(default=3_600, ge=30, le=86_400)
    max_output_characters: int = Field(default=100_000, ge=1_000, le=1_000_000)
    push_enabled: bool = True


class CreateLocalAgentRequest(LocalAgentFields):
    pass


class UpdateLocalAgentRequest(project_schemas.StrictRequest):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider: AgentProvider | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    is_default: bool | None = None
    command: str | None = Field(default=None, min_length=1, max_length=2_048)
    git_command: str | None = Field(default=None, min_length=1, max_length=2_048)
    git_remote: str | None = Field(
        default=None, min_length=1, max_length=255, pattern=r"^[A-Za-z0-9._-]+$"
    )
    timeout_seconds: int | None = Field(default=None, ge=30, le=86_400)
    max_output_characters: int | None = Field(
        default=None, ge=1_000, le=1_000_000
    )
    push_enabled: bool | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateLocalAgentRequest":
        if not self.model_fields_set:
            raise ValueError("At least one local agent field must be provided")
        return self


class LocalAgentResponse(project_schemas.APIModel):
    id: str
    company_id: str
    name: str
    provider: AgentProvider
    model_name: str
    enabled: bool
    is_default: bool
    command: str
    git_command: str
    git_remote: str
    timeout_seconds: int
    max_output_characters: int
    push_enabled: bool
    created_at: datetime
    updated_at: datetime
