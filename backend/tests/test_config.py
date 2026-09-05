"""Config loading and the startup gate.

The gate exists because a deployment that forgets SCRAPESMITH_DATABASE_URL used to start
happily on the local dev default and only fall over later, on the first query, with an asyncpg
connection error that says nothing about the real mistake.
"""
from __future__ import annotations

import pathlib

import pytest

from app.config import (
    DEFAULT_DATABASE_URL,
    ENV_FILE,
    Settings,
    check_settings,
    safe_database_url,
)

EXAMPLE = pathlib.Path(__file__).parent.parent / ".env.local.example"

REAL_URL = "postgresql+asyncpg://svc:s3cr3t@db.internal:5432/scrapesmith"


class TestStartupGate:
    def test_local_env_allows_the_dev_defaults(self):
        """The default env must keep working with no configuration at all, or every test and
        every local run breaks."""
        check_settings(Settings(env="local", database_url=DEFAULT_DATABASE_URL))

    def test_default_url_is_refused_outside_local(self):
        with pytest.raises(RuntimeError) as e:
            check_settings(Settings(env="production", database_url=DEFAULT_DATABASE_URL))
        # The message has to name the variable — the whole point is that the old failure did not.
        assert "SCRAPESMITH_DATABASE_URL" in str(e.value)

    def test_default_password_is_refused_even_against_another_host(self):
        """Pointing at a real host while leaving the shipped password behind is the more
        likely mistake, and the URL no longer equals the default so it needs its own check."""
        with pytest.raises(RuntimeError) as e:
            check_settings(
                Settings(
                    env="production",
                    database_url="postgresql+asyncpg://scrapesmith:scrapesmith@db.internal:5432/x",
                )
            )
        assert "default scrapesmith:scrapesmith password" in str(e.value)

    def test_real_url_passes_outside_local(self):
        check_settings(Settings(env="production", database_url=REAL_URL))

    def test_failure_message_points_at_the_env_file(self):
        with pytest.raises(RuntimeError) as e:
            check_settings(Settings(env="staging", database_url=DEFAULT_DATABASE_URL))
        assert ".env.local" in str(e.value)


class TestPasswordMasking:
    def test_password_is_masked(self):
        masked = safe_database_url(REAL_URL)
        assert "s3cr3t" not in masked
        assert "svc" in masked and "db.internal" in masked

    def test_url_without_credentials_is_returned_unchanged(self):
        assert safe_database_url("redis://localhost:6379") == "redis://localhost:6379"

    def test_masking_survives_a_password_containing_an_at_sign(self):
        """rsplit on '@' rather than split, so an '@' inside the password does not truncate
        the host and leak the tail of the password into the log line."""
        masked = safe_database_url("postgresql://u:p@ss@host:5432/db")
        assert "p@ss" not in masked
        assert masked.endswith("@host:5432/db")


class TestEnvFileContract:
    def test_example_file_exists_and_is_not_the_real_file(self):
        assert EXAMPLE.is_file()
        assert EXAMPLE != ENV_FILE

    def test_example_documents_every_setting(self):
        """A .env.local.example that has drifted from the code is worse than none — it tells
        someone they have configured everything when they have not."""
        text = EXAMPLE.read_text(encoding="utf-8")
        for field in Settings.model_fields:
            assert f"SCRAPESMITH_{field.upper()}" in text, f"{field} missing from the example"
        # Read directly from os.environ rather than through Settings, so they have no prefix
        # and would not be caught by the loop above.
        for bare in ("OLLAMA_HOST", "ANTHROPIC_API_KEY", "SCRAPESMITH_CLOUD_MODEL"):
            assert bare in text, f"{bare} missing from the example"

    def test_example_carries_no_real_looking_key(self):
        text = EXAMPLE.read_text(encoding="utf-8")
        assert "sk-ant-..." in text, "the placeholder should stay an obvious placeholder"
        for line in text.splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                pytest.fail(f"example must leave the key commented out, got: {line}")
