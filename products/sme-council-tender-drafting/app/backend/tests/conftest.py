"""Test fixtures. Tests run against a real Postgres (TEST_DATABASE_URL), like production."""
from __future__ import annotations

import os
import re
import secrets
import signal
import time
import warnings

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import models  # noqa: F401  (register tables)
from app.ai import FakeAI
from app.billing import MockBilling
from app.config import Settings
from app.db import Base, Database
from app.email import OutboxEmail
from app.main import create_app

from . import vehicle

_BASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://studio:studio@localhost:5432/starter_test")
# Each pytest run gets its own database, `<db>_t<epoch>_<pid>_<rand>`, so runs in parallel (agents, dev + CI on one
# host) never wipe each other's data. TEST_DATABASE_SHARED=1 uses the URL as-is (needs no CREATE DATABASE right).
SHARED = os.environ.get("TEST_DATABASE_SHARED") == "1"
_BASE = make_url(_BASE_URL)
_BASE_NAME = _BASE.database or "starter_test"
_STALE_AFTER_SECONDS = 6 * 3600
_BASE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,35}$")
# `<base>_t<10 digits>_<pid up to 7>_<6 hex>` adds 2+10+1+7+1+6 = 27 bytes; 36 + 27 = 63 = Postgres NAMEDATALEN - 1.
_MAX_DB_NAME = 63
# Only databases carrying this comment (set at creation) are ever dropped by the stale cleanup.
_MARKER = "starter-pytest-ephemeral"
if SHARED:
    TEST_DB = _BASE_URL
    _RUN_NAME = _BASE_NAME
else:
    _RUN_NAME = f"{_BASE_NAME}_t{int(time.time())}_{os.getpid()}_{secrets.token_hex(3)}"
    TEST_DB = _BASE.set(database=_RUN_NAME).render_as_string(hide_password=False)
PASSWORD = "correct horse battery"


def pytest_configure(config) -> None:
    """SIGTERM (a timeout, a cut-off agent run) becomes KeyboardInterrupt so the per-run DB is still dropped.
    SIGKILL cannot be caught; its leftovers are reclaimed by the stale cleanup of a later run."""
    try:
        signal.signal(signal.SIGTERM, lambda signum, frame: (_ for _ in ()).throw(KeyboardInterrupt()))
    except ValueError:  # not the main thread
        pass


def _check_base_name(name: str) -> None:
    if not _BASE_NAME_RE.match(name):
        pytest.exit(f"TEST_DATABASE_URL database name {name!r} is not allowed: use letters, digits and underscores "
                    f"only (max 36 characters, not starting with a digit), or set TEST_DATABASE_SHARED=1.", 2)


def _admin_conn():
    extra = {k: v for k, v in _BASE.query.items() if isinstance(v, str)}
    return psycopg.connect(host=_BASE.host, port=_BASE.port, user=_BASE.username, password=_BASE.password,
                           dbname="postgres", autocommit=True, connect_timeout=10, **extra)


def _stale_pattern(base: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(base)}_t(\d{{10}})_\d{{1,7}}_[0-9a-f]{{6}}$")


def _drop_stale(conn, base: str, now: float | None = None) -> list[str]:
    """Drop databases this conftest made and a killed run left behind: exact generated name, our comment marker,
    owned by the current user, older than a few hours. Never raises."""
    now = time.time() if now is None else now
    pattern = _stale_pattern(base)
    rows = conn.execute(
        "SELECT d.datname FROM pg_database d WHERE shobj_description(d.oid, 'pg_database') = %s "
        "AND d.datdba = (SELECT oid FROM pg_roles WHERE rolname = current_user)", (_MARKER,)).fetchall()
    dropped = []
    for (name,) in rows:
        match = pattern.match(name)
        if not match or now - int(match.group(1)) <= _STALE_AFTER_SECONDS:
            continue
        try:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
            dropped.append(name)
        except psycopg.Error as exc:
            warnings.warn(f"could not drop stale test database {name}: {exc}")
    return dropped


def _create_run_db(conn, name: str) -> None:
    assert len(name.encode()) <= _MAX_DB_NAME, f"test database name {name!r} exceeds Postgres's 63-byte limit"
    try:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.errors.InsufficientPrivilege:
        pytest.exit("The test database user needs the CREATEDB privilege (ALTER ROLE <user> CREATEDB), "
                    "or set TEST_DATABASE_SHARED=1 to use the shared database.", 2)
    try:
        conn.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(name), sql.Literal(_MARKER)))
    except Exception as exc:  # an unmarked DB would never be reclaimed by the stale cleanup: drop it now
        outcome = "it was dropped"
        try:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        except psycopg.Error as drop_exc:
            outcome = f"dropping it failed too ({drop_exc}); drop it by hand"
        pytest.exit(f"could not mark test database {name} ({exc}); {outcome}.", 2)


@pytest.fixture(scope="session")
def database():
    if SHARED:
        db = Database(TEST_DB)
        with db.engine.begin() as conn:  # a clean schema, whatever another branch left behind
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        try:
            Base.metadata.create_all(db.engine)
            vehicle.create_table(db.engine)
            yield db
        finally:
            db.dispose()
        return
    _check_base_name(_BASE_NAME)
    admin = _admin_conn()
    try:
        _drop_stale(admin, _BASE_NAME)
        _create_run_db(admin, _RUN_NAME)
        try:
            db = Database(TEST_DB)
            try:
                Base.metadata.create_all(db.engine)
                vehicle.create_table(db.engine)
                yield db
            finally:
                db.dispose()
        finally:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(_RUN_NAME)))
    finally:
        admin.close()


@pytest.fixture(autouse=True)
def _clean(database):
    yield
    tables = ", ".join([t.name for t in Base.metadata.sorted_tables] + ["vehicle_items"])
    with database.engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", database_url=TEST_DB, app_base_url="https://app.test", cookie_secure=True,
                    auth_rate_limit_per_minute=1000, ai_rate_limit_per_minute=1000, log_level="WARNING",
                    mock_checkout_enabled=True, billing_enabled=True)


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
                             billing_provider=MockBilling(settings.billing_webhook_secret, settings.app_base_url),
                             extra_routers=(vehicle.router,))
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
