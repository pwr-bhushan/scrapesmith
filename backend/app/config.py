"""Environment-driven settings for the app skeleton.

One place to configure everything: ``backend/.env.local`` (gitignored, see
``.env.local.example``). It is loaded into ``os.environ`` rather than only into ``Settings``,
because two consumers never touch this model — the ``anthropic`` SDK reads ``ANTHROPIC_API_KEY``
itself, and ``OllamaProvider`` reads ``OLLAMA_HOST`` directly. Binding the file to the model
alone would leave both silently unset.

Real process environment always wins over the file, so ``SCRAPESMITH_ENV=production uvicorn …``
and container-injected secrets keep working untouched.
"""
from __future__ import annotations

import pathlib

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved against this file, not the cwd: uvicorn, arq and pytest are each started from
# different directories and all of them need the same file.
ENV_FILE = pathlib.Path(__file__).resolve().parent.parent / ".env.local"
load_dotenv(ENV_FILE, override=False)

# Convenience credentials for a local docker/homebrew Postgres. Fine for a dev machine,
# never for a deployment — check_settings() refuses them outside SCRAPESMITH_ENV=local.
DEFAULT_DATABASE_URL = "postgresql+asyncpg://scrapesmith:scrapesmith@localhost:5432/scrapesmith"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCRAPESMITH_", extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = "redis://localhost:6379"
    # "local" keeps the dev defaults usable. Anything else opts into check_settings().
    env: str = "local"


settings = Settings()


def safe_database_url(url: str) -> str:
    """The URL with its password masked, for logging. Never log ``database_url`` raw."""
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    creds, host = rest.rsplit("@", 1)
    user = creds.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


def check_settings(s: Settings | None = None) -> None:
    """Fail fast on configuration that is only safe on a dev machine.

    Without this, a deployment that forgets ``SCRAPESMITH_DATABASE_URL`` still starts and only
    falls over later, on the first query, with an asyncpg connection error that says nothing
    about the actual mistake. Raising here names the missing setting instead.

    No-op when ``SCRAPESMITH_ENV`` is ``local`` (the default), so tests and local runs keep
    using the built-in defaults.
    """
    s = s or settings
    if s.env == "local":
        return

    problems = []
    if s.database_url == DEFAULT_DATABASE_URL:
        problems.append(
            "SCRAPESMITH_DATABASE_URL is unset — falling back to the local dev default"
        )
    elif "scrapesmith:scrapesmith@" in s.database_url:
        problems.append(
            "SCRAPESMITH_DATABASE_URL still carries the default scrapesmith:scrapesmith password"
        )
    if problems:
        raise RuntimeError(
            f"Refusing to start with SCRAPESMITH_ENV={s.env!r}: "
            + "; ".join(problems)
            + f". Set them in {ENV_FILE} or the process environment."
        )
