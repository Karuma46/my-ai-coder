from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GithubSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GITHUB_",
        extra="ignore",
    )

    enabled: bool = False
    personal_access_token: SecretStr | None = None
    owner: str = ""
    allowed_repositories: str = ""
    toolsets: str = "repos,issues,pull_requests,actions"
    mcp_image: str = "ghcr.io/github/github-mcp-server:v1.7.0"
    mcp_transport: Literal["http", "stdio"] = "http"
    mcp_url: str = "http://127.0.0.1:8082/mcp"
    write_enabled: bool = False
    merge_enabled: bool = False
    release_enabled: bool = False

    @property
    def allowed_repository_names(self) -> frozenset[str]:
        return frozenset(
            repository.strip()
            for repository in self.allowed_repositories.split(",")
            if repository.strip()
        )


@lru_cache
def get_github_settings() -> GithubSettings:
    return GithubSettings()
