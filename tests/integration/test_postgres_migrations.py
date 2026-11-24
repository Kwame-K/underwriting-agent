"""Alembic migrations against a real database (PostgreSQL in CI).

Set TEST_POSTGRES_URL to run, e.g.:
    TEST_POSTGRES_URL=postgresql://postgres:ci@localhost:5432/underwriting \
        uv run pytest tests/integration/test_postgres_migrations.py -rs
The target database should be empty or disposable.
"""

import os

import pytest
from sqlalchemy import inspect

from underwriting_agent.infrastructure.persistence.database import (
    create_database_engine,
    run_migrations,
)
from underwriting_agent.infrastructure.persistence.models import Base


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL is not set")
    return url


def _table_names(database_url: str) -> set[str]:
    engine = create_database_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migrations_create_every_mapped_table(database_url: str) -> None:
    run_migrations(database_url)

    tables = _table_names(database_url)

    assert "alembic_version" in tables
    assert set(Base.metadata.tables) <= tables


def test_migrations_can_be_applied_twice(database_url: str) -> None:
    run_migrations(database_url)
    run_migrations(database_url)

    assert set(Base.metadata.tables) <= _table_names(database_url)
