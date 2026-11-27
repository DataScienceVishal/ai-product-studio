"""Health, request ids, security headers, error shape, logging redaction, account deletion,
production settings guards and migrations."""
import json
import logging
import uuid

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text

from app.config import Settings
from app.db import Base
from app.logs import JsonFormatter
from app.main import create_app
from app.models import Note, Tenant, User

from .conftest import PASSWORD, TEST_DB, sign_up


def test_health_ok(new_client):
    response = new_client().get("/healthz")
    assert response.status_code == 200 and response.json()["db"] == "ok"


def test_health_reports_database_down():
    broken = create_app(Settings(env="test", database_url="postgresql+psycopg://x:y@127.0.0.1:1/none", log_level="CRITICAL"))
    with TestClient(broken, base_url="https://testserver") as client:
        response = client.get("/healthz")
    assert response.status_code == 503 and response.json()["db"] == "down"


def test_request_id_and_security_headers(new_client):
    client = new_client()
    echoed = client.get("/healthz", headers={"X-Request-ID": "abc12345-test"})
    assert echoed.headers["x-request-id"] == "abc12345-test"
    replaced = client.get("/healthz", headers={"X-Request-ID": "bad id with spaces"})
    assert replaced.headers["x-request-id"] != "bad id with spaces" and len(replaced.headers["x-request-id"]) == 32
    for header in ("x-content-type-options", "x-frame-options", "referrer-policy", "x-robots-tag"):
        assert header in echoed.headers
    assert "noindex" in echoed.headers["x-robots-tag"]


def test_unhandled_errors_return_json_with_request_id(app):
    @app.get("/api/boom")
    def boom():
        raise RuntimeError("kaboom")

    client = TestClient(app, base_url="https://testserver", raise_server_exceptions=False)
    response = client.get("/api/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_error" and body["request_id"] == response.headers["x-request-id"]
    assert "kaboom" not in response.text


def test_cors_allows_only_configured_origins(new_client):
    client = new_client()
    allowed = client.options("/api/notes", headers={"Origin": "http://localhost:5173",
                                                    "Access-Control-Request-Method": "POST",
                                                    "Access-Control-Request-Headers": "x-requested-with"})
    evil = client.options("/api/notes", headers={"Origin": "https://evil.example",
                                                 "Access-Control-Request-Method": "POST",
                                                 "Access-Control-Request-Headers": "x-requested-with"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in evil.headers


def test_log_lines_are_json_and_redact_sensitive_fields():
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello", None, None)
    record.password, record.email, record.api_key, record.user_id = "hunter2", "a@b.c", "k", "u-1"
    line = json.loads(JsonFormatter().format(record))
    assert line["msg"] == "hello" and line["user_id"] == "u-1"
    assert line["password"] == line["email"] == line["api_key"] == "[redacted]"


def test_account_deletion_removes_only_that_tenant(new_client, database):
    a, b = new_client(), new_client()
    sign_up(a, email="a@alpha.test", company="Alpha")
    sign_up(b, email="b@beta.test", company="Beta")
    a.post("/api/notes", json={"title": "A1"})
    b.post("/api/notes", json={"title": "B1"})
    assert a.request("DELETE", "/api/account", json={"password": PASSWORD, "confirm": "nope"}).status_code == 422
    assert a.request("DELETE", "/api/account", json={"password": "wrong password!", "confirm": "DELETE"}).status_code == 401
    assert a.request("DELETE", "/api/account", json={"password": PASSWORD, "confirm": "DELETE"}).status_code == 204
    assert a.get("/api/auth/me").status_code == 401
    with database.sessions() as db:
        assert [t.name for t in db.scalars(select(Tenant))] == ["Beta"]
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert [n.title for n in db.scalars(select(Note))] == ["B1"]
    assert b.get("/api/notes").json()["total"] == 1


GOOD_PROD = dict(env="prod", app_base_url="https://app.example.com", cors_origins=["https://app.example.com"],
                 trust_proxy_headers=True)


def test_prod_settings_refuse_unsafe_values(monkeypatch):
    for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API",
                 "AZURE_OPENAI_AUTH", "AI_PROVIDER"):
        monkeypatch.delenv(name, raising=False)  # cloud sessions set these; the test needs them unset
    Settings(**GOOD_PROD)  # the safe baseline is accepted
    unsafe = {
        "BILLING_WEBHOOK_SECRET": dict(billing_webhook_secret=""),
        "at least 32": dict(billing_webhook_secret="short"),
        "whsec_": dict(billing_provider="stripe", billing_webhook_secret="x" * 40),
        "CORS_ORIGINS": dict(cors_origins=["*"]),
        "APP_BASE_URL": dict(app_base_url="http://app.example.com"),
        "COOKIE_SECURE": dict(cookie_secure=False),
        "TRUST_PROXY_HEADERS": dict(trust_proxy_headers=False),
        "AZURE_OPENAI_ENDPOINT": dict(ai_provider="azure"),
    }
    for message, change in unsafe.items():
        with pytest.raises(ValueError, match=message):
            Settings(**(GOOD_PROD | change))
    with pytest.raises(ValueError, match="APP_BASE_URL"):
        Settings(**(GOOD_PROD | {"app_base_url": "https://localhost"}))


def test_empty_webhook_secret_is_refused_in_every_environment():
    with pytest.raises(ValueError, match="BILLING_WEBHOOK_SECRET"):
        Settings(env="dev", billing_webhook_secret="")


def test_prod_hides_api_docs(settings):
    prod = create_app(settings.model_copy(update=GOOD_PROD))
    with TestClient(prod, base_url="https://testserver") as client:
        assert client.get("/api/docs").status_code == 404
    prod.state.db.dispose()


def test_migrations_match_models():
    """alembic upgrade head on an empty database gives exactly the models' schema."""
    admin_url = TEST_DB.rsplit("/", 1)[0] + "/postgres"
    name = f"starter_migr_{uuid.uuid4().hex[:8]}"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = TEST_DB.rsplit("/", 1)[0] + f"/{name}"
    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        config.attributes["configure_logger"] = False
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        engine.dispose()
        assert diffs == []
        command.downgrade(config, "base")
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
