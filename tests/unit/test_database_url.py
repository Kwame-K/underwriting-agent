from typing import Any

import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url

from underwriting_agent.infrastructure.persistence import database

PERCENT_ENCODED_URL = (
    "postgresql://underwriting_app:p%40ss%2Fword@localhost:5432/underwriting"
)


def test_run_migrations_keeps_percent_encoded_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Config] = []

    def fake_upgrade(config: Config, revision: str, **kwargs: Any) -> None:
        captured.append(config)

    monkeypatch.setattr(
        "underwriting_agent.infrastructure.persistence.database.command.upgrade",
        fake_upgrade,
    )

    database.run_migrations(PERCENT_ENCODED_URL)

    configured = captured[0].get_main_option("sqlalchemy.url")

    assert configured == database.normalize_database_url(PERCENT_ENCODED_URL)
    assert configured is not None
    assert make_url(configured).password == "p@ss/word"
