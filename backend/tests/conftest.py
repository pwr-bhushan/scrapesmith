"""Shared pytest fixtures for the heal spike test suite."""
from __future__ import annotations

import pathlib

import pytest

# Absolute path to fixtures directory (sibling of tests/)
FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


@pytest.fixture
def amazon_case_dir() -> pathlib.Path:
    return FIXTURES_DIR / "drift" / "amazon_product"


@pytest.fixture
def drift_dir() -> pathlib.Path:
    """The whole eval corpus — generated cases plus the hand-written amazon_product one."""
    return FIXTURES_DIR / "drift"


@pytest.fixture
def before_html(amazon_case_dir: pathlib.Path) -> str:
    return (amazon_case_dir / "before.html").read_text(encoding="utf-8")


@pytest.fixture
def after_html(amazon_case_dir: pathlib.Path) -> str:
    return (amazon_case_dir / "after.html").read_text(encoding="utf-8")
