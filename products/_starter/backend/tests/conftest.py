"""Test fixtures. Tests run against a real Postgres (TEST_DATABASE_URL), like production."""
from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401  (register tables)
from app.ai import FakeAI
from app.billing import MockBilling
from app.config import Settings
from app.db import Base, Database
from app.email import OutboxEmail
from app.main import create_app

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://studio:studio@localhost:5432/starter_test")
PASSWORD = "correct horse battery"


@pytest.fixture(scope="session")
def database():
    db = Database(TEST_DB)
    with db.engine.begin() as conn:  # a clean schema, whatever another branch left behind
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(db.engine)
    yield db
    db.dispose()


@pytest.fixture(autouse=True)
def _clean(database):
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with database.engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", database_url=TEST_DB, app_base_url="https://app.test", cookie_secure=True,
                    auth_rate_limit_per_minute=1000, ai_rate_limit_per_minute=1000, log_level="WARNING")


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
