"""Test fixtures. Tests run against a real Postgres (TEST_DATABASE_URL), like production."""
from __future__ import annotations

import os
import re
import secrets
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import models  # noqa: F401  (register tables)
from app.ai import FakeAI
from app.billing import MockBilling
from app.config import Settings
from app.db import Base, Database
from app.email import OutboxEmail
from app.main import create_app

_BASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://studio:studio@localhost:5432/starter_test")
# Each pytest run gets its own database, `<db>_t<epoch>_<pid>_<rand>`, so runs in parallel (agents, dev + CI on one
# host) never wipe each other's data. TEST_DATABASE_SHARED=1 uses the URL as-is (needs no CREATE DATABASE right).
SHARED = os.environ.get("TEST_DATABASE_SHARED") == "1"
_BASE = make_url(_BASE_URL)
_BASE_NAME = _BASE.database or "starter_test"
_STALE_AFTER_SECONDS = 6 * 3600
if SHARED:
    TEST_DB = _BASE_URL
    _RUN_NAME = _BASE_NAME
else:
    _RUN_NAME = f"{_BASE_NAME}_t{int(time.time())}_{os.getpid()}_{secrets.token_hex(3)}"
    TEST_DB = _BASE.set(database=_RUN_NAME).render_as_string(hide_password=False)
PASSWORD = "correct horse battery"


def _admin_engine():
    return create_engine(_BASE.set(database="postgres").render_as_string(hide_password=False),
                         isolation_level="AUTOCOMMIT")


def _drop_stale(conn) -> None:
    """Drop `<db>_t<epoch>_...` databases left by killed runs once they are older than a few hours."""
    pattern = re.compile(rf"^{re.escape(_BASE_NAME)}_t(\d+)_\d+_[0-9a-f]+$")
    for (name,) in conn.execute(text("SELECT datname FROM pg_database")).fetchall():
        match = pattern.match(name)
        if match and time.time() - int(match.group(1)) > _STALE_AFTER_SECONDS:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


@pytest.fixture(scope="session")
def database():
    if SHARED:
        db = Database(TEST_DB)
        with db.engine.begin() as conn:  # a clean schema, whatever another branch left behind
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    else:
        admin = _admin_engine()
        with admin.connect() as conn:
            _drop_stale(conn)
            conn.execute(text(f'CREATE DATABASE "{_RUN_NAME}"'))
        db = Database(TEST_DB)
    try:
        Base.metadata.create_all(db.engine)
        yield db
    finally:
        db.dispose()
        if not SHARED:
            with admin.connect() as conn:
                conn.execute(text(f'DROP DATABASE IF EXISTS "{_RUN_NAME}" WITH (FORCE)'))
            admin.dispose()


@pytest.fixture(autouse=True)
def _clean(database):
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with database.engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", database_url=TEST_DB, app_base_url="https://app.test", cookie_secure=True,
                    auth_rate_limit_per_minute=1000, ai_rate_limit_per_minute=1000, log_level="WARNING",
                    mock_checkout_enabled=True)


class RecordingAI(FakeAI):
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def complete(self, system, user, max_output_tokens=1200):
        self.calls.append((system, user))
        return super().complete(system, user, max_output_tokens)


@pytest.fixture
def ai() -> RecordingAI:
    return RecordingAI()


@pytest.fixture
def outbox() -> OutboxEmail:
    return OutboxEmail()


@pytest.fixture
def app(settings, ai, outbox):
    application = create_app(settings, ai=ai, email=outbox,
                             billing_provider=MockBilling(settings.billing_webhook_secret, settings.app_base_url))
    yield application
    application.state.db.dispose()


@pytest.fixture
def new_client(app):
    """Each call gives an independent browser (own cookie jar) with the CSRF header set."""
    clients = []

    def make(csrf: bool = True) -> TestClient:
        client = TestClient(app, base_url="https://testserver",
                            headers={"X-Requested-With": "test"} if csrf else {})
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


def sign_up(client: TestClient, email: str = "owner@acme.test", company: str = "Acme Ltd",
            password: str = PASSWORD) -> dict:
    response = client.post("/api/auth/signup", json={"company_name": company, "email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def link_token(outbox: OutboxEmail, path: str) -> str:
    """Token from the newest email whose link goes to /<path>?token=..."""
    for message in reversed(outbox.sent):
        match = re.search(rf"/{path}\?token=(\S+)", message.body)
        if match:
            return match.group(1)
    raise AssertionError(f"no /{path} email in the outbox")


def verify_email(client: TestClient, outbox: OutboxEmail) -> None:
    response = client.post("/api/auth/verify-email", json={"token": link_token(outbox, "verify-email")})
    assert response.status_code == 204, response.text


@pytest.fixture
def owner(new_client, outbox):
    """A signed-up owner whose email is verified, as most owner actions need."""
    client = new_client()
    sign_up(client)
    verify_email(client, outbox)
    return client, client.get("/api/auth/me").json()
