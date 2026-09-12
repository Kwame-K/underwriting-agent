from collections.abc import Callable

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from underwriting_agent.settings import get_settings


def create_database_engine(database_url: str) -> Engine:
    connect_args: dict[str, bool] = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        database_url,
        connect_args=connect_args,
    )


def create_session_factory(
    engine: Engine,
) -> Callable[[], Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


settings = get_settings()
engine = create_database_engine(settings.database_url)
SessionFactory = create_session_factory(engine)


def initialize_database() -> None:
    from underwriting_agent.infrastructure.persistence.models import Base

    Base.metadata.create_all(bind=engine)
