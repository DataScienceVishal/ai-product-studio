"""Database engine and session handling (SQLAlchemy 2, sync, psycopg 3).

Rule for every endpoint: never hold a transaction (and so a pooled connection) across a slow external
call such as the AI or the payment provider. `deps.current` commits after loading the user, and
endpoints that call out commit before the call and reopen afterwards (see routes/notes.py summarize).
"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str, statement_timeout_ms: int = 10_000, idle_in_transaction_timeout_ms: int = 15_000,
                 pool_size: int = 5, max_overflow: int = 5):
        connect_args = {}
        if url.startswith("postgresql"):
            # Every query has a timeout, idle transactions are cut off, and connecting gives up after 5 seconds.
            connect_args = {"connect_timeout": 5,
                            "options": f"-c statement_timeout={statement_timeout_ms} "
                                       f"-c idle_in_transaction_session_timeout={idle_in_transaction_timeout_ms}"}
        # hide_parameters: SQLAlchemy otherwise puts bound values (emails, password hashes, note text)
        # into exception messages, and those reach the logs.
        self.engine: Engine = create_engine(url, pool_pre_ping=True, pool_size=pool_size, max_overflow=max_overflow,
                                            pool_timeout=10, hide_parameters=True, connect_args=connect_args)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def dispose(self) -> None:
        self.engine.dispose()


def get_db(request: Request) -> Iterator[Session]:
    db: Session = request.app.state.db.sessions()
    try:
        yield db
    finally:
        db.close()
