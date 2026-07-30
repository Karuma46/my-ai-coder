from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUTH_",
        extra="ignore",
    )

    jwt_secret: SecretStr = Field(
        default=SecretStr("local-development-secret-change-me"),
        min_length=32,
    )
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "project-release-api"
    jwt_audience: str = "project-release-client"
    access_token_minutes: int = Field(default=60, ge=5, le=10_080)


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
