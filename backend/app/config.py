"""Environment-driven settings for the app skeleton."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCRAPESMITH_", extra="ignore")

    database_url: str = "postgresql+asyncpg://scrapesmith:scrapesmith@localhost:5432/scrapesmith"
    redis_url: str = "redis://localhost:6379"


settings = Settings()
