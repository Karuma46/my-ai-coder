from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CelerySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CELERY_",
        extra="ignore",
    )

    broker_url: str = "redis://127.0.0.1:6380/0"
    result_backend: str = "redis://127.0.0.1:6380/1"
    planned_todo_scan_seconds: int = Field(default=30, ge=5, le=3_600)
    github_task_scan_seconds: int = Field(default=1, ge=1, le=60)
    planned_todo_batch_size: int = Field(default=10, ge=1, le=100)
    result_expires_seconds: int = Field(default=86_400, ge=60)
    agent_execution_lock_key: str = "project-release-api:agent-execution"
    agent_execution_lock_retry_seconds: int = Field(default=5, ge=1, le=300)
    task_events_channel: str = Field(
        default="project-release-api:agent-events",
        min_length=1,
    )


@lru_cache
def get_celery_settings() -> CelerySettings:
    return CelerySettings()
