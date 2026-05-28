from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings


settings = get_settings()


def _engine_kwargs(database_url: str) -> dict:
    kwargs: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
    return kwargs


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_session_abandon_columns()


def _ensure_session_abandon_columns() -> None:
    existing_columns = {column["name"] for column in inspect(engine).get_columns("study_sessions")}
    missing_columns = {
        "abandoned_at": "ALTER TABLE study_sessions ADD COLUMN abandoned_at DATETIME NULL",
        "abandon_reason": "ALTER TABLE study_sessions ADD COLUMN abandon_reason VARCHAR(100) NULL",
    }
    with engine.begin() as connection:
        for column_name, statement in missing_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))
