from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    app_name: str = "Project Release API"
    database_url: str = "sqlite+aiosqlite:///./app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
