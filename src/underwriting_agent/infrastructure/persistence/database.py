from collections.abc import Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from underwriting_agent.settings import get_settings

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent / "migrations"


def normalize_database_url(url: str) -> str:
    """Point plain PostgreSQL URLs at the installed psycopg 3 driver."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def create_database_engine(database_url: str) -> Engine:
    normalized_url = normalize_database_url(database_url)
    if normalized_url.startswith("sqlite"):
        return create_engine(
            normalized_url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(normalized_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def run_migrations(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIRECTORY))
    config.set_main_option("sqlalchemy.url", normalize_database_url(database_url))
    command.upgrade(config, "head")


settings = get_settings()
engine = create_database_engine(settings.database_url)
SessionFactory = create_session_factory(engine)


def initialize_database() -> None:
    if make_url(normalize_database_url(settings.database_url)).get_backend_name() == "sqlite":
        from underwriting_agent.infrastructure.persistence.models import Base

        Base.metadata.create_all(bind=engine)
        return

    run_migrations(settings.database_url)
