from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.app_env == "development",
            pool_pre_ping=True,
        )
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def get_session_sync() -> Session:
    return Session(get_engine())
