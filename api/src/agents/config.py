from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOCAL_AGENT_",
        extra="ignore",
    )

    enabled: bool = False
    provider: Literal["codex", "claude", "ollama"] = "codex"
    model_name: str = ""
    git_command: str = "git"
    git_remote: str = Field(default="origin", pattern=r"^[A-Za-z0-9._-]+$")
    codex_command: str = "codex"
    claude_command: str = "claude"
    ollama_command: str = "codex"
    timeout_seconds: int = Field(default=3_600, ge=30, le=86_400)
    max_output_characters: int = Field(default=100_000, ge=1_000, le=1_000_000)
    push_enabled: bool = False


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
