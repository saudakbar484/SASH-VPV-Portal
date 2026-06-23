"""SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.settings import DB_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DB_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fks(dbapi_conn, _record) -> None:
    """SQLite needs FK enforcement enabled explicitly per connection."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_all() -> None:
    """Create tables if they don't exist (lightweight migration on startup)."""
    from backend.db import models  # noqa: F401  - ensure models are imported
    Base.metadata.create_all(bind=engine)
