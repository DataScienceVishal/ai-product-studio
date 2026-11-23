"""Database engine and session handling (SQLAlchemy 2, sync, psycopg 3)."""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str, statement_timeout_ms: int = 10_000):
        connect_args = {}
        if url.startswith("postgresql"):
            # every query has a timeout, and connecting gives up after 5 seconds
            connect_args = {"connect_timeout": 5, "options": f"-c statement_timeout={statement_timeout_ms}"}
        self.engine: Engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5,
                                            connect_args=connect_args)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def dispose(self) -> None:
        self.engine.dispose()


def get_db(request: Request) -> Iterator[Session]:
    db: Session = request.app.state.db.sessions()
    try:
        yield db
    finally:
        db.close()
