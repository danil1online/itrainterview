"""Подключение к БД: engine, сессии и базовый класс моделей."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy-моделей (DeclarativeBase)."""
    pass


def _make_engine(url: str):
    """Создаёт engine; для sqlite отключает check_same_thread."""
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI-зависимость: сессия БД на запрос, закрывается после."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
