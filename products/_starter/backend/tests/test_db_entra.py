"""DB_AUTH=entra: a managed-identity token is the Postgres password. No network: tokens come from fakes and the
psycopg connect call is replaced, so the tests assert on the connection parameters (a real Entra server isn't available)."""
from __future__ import annotations

import logging

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config

from app.config import Settings
from app.db import Database
from app.dbauth import DB_RESOURCE, ENTRA_POOL_RECYCLE_SECONDS, DbAuthConfigError, DbTokenError, build_token_provider

URL = "postgresql+psycopg://my-identity@db.example.postgres.database.azure.com:5432/app?sslmode=verify-full"
SECRET = "tok-SECRET-abc123"


class Stop(Exception):
    """Raised by the fake connect so no real connection is needed."""


@pytest.fixture
def connects(monkeypatch):
    calls: list[dict] = []

    def fake_connect(*args, **kwargs):
        calls.append(kwargs)
        raise Stop()

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    return calls


class FakeProvider:
    def __init__(self, tokens=("t1", "t2", "t3")):
        self.tokens, self.n = list(tokens), 0

    def get(self, timeout=None):
        self.n += 1
        return self.tokens[min(self.n, len(self.tokens)) - 1]


def try_connect(database: Database) -> None:
    with pytest.raises(Stop):
        database.engine.raw_connection()


def test_do_connect_injects_token_as_password(connects):
    database = Database(URL, db_auth="entra", token_provider=FakeProvider(["abc"]))
    try_connect(database)
    assert connects[0]["password"] == "abc"
    assert connects[0]["user"] == "my-identity"
    assert connects[0]["sslmode"] == "verify-full"
    assert database.engine.pool._recycle == ENTRA_POOL_RECYCLE_SECONDS < 3600


def test_every_new_connection_asks_the_provider(connects):
    provider = FakeProvider()
    database = Database(URL, db_auth="entra", token_provider=provider)
    for _ in range(3):
        try_connect(database)
    assert [c["password"] for c in connects] == ["t1", "t2", "t3"]


def test_password_mode_is_unchanged(connects):
    database = Database("postgresql+psycopg://u:pw@localhost:5432/x")
    try_connect(database)
    assert connects[0]["password"] == "pw"
    assert database.engine.pool._recycle == -1


def test_unknown_db_auth_refused():
    with pytest.raises(ValueError):
        Database(URL, db_auth="kerberos")


@pytest.mark.parametrize("url, fragment", [
    ("postgresql+psycopg://my-identity:hunter2@h/app?sslmode=verify-full", "must not contain a password"),
    ("postgresql+psycopg://my-identity@h/app?sslmode=verify-full&password=hunter2", "must not contain a password"),
    ("postgresql+psycopg://my-identity@h/app?sslmode=verify-full&passfile=/tmp/hunter2", "must not contain a password"),
    ("postgresql+psycopg://my-identity@h/app", "sslmode=verify-full"),
    ("postgresql+psycopg://my-identity@h/app?sslmode=require", "sslmode=verify-full"),
    ("postgresql+psycopg://h/app?sslmode=verify-full", "Entra role"),
    ("sqlite:///x.db", "PostgreSQL"),
])
def test_unsafe_urls_refused_without_leaking(url, fragment):
    with pytest.raises(DbAuthConfigError) as caught:
        Database(url, db_auth="entra")
    with pytest.raises(ValueError) as from_settings:
        Settings(database_url=url, db_auth="entra")
    for error in (caught.value, from_settings.value):
        assert fragment in str(error)
        assert "hunter2" not in str(error)


def test_settings_accept_safe_entra_url_and_default_is_password():
    assert Settings(database_url=URL, db_auth="entra").db_auth == "entra"
    assert Settings().db_auth == "password"


def test_token_fetched_once_per_cache_window(connects):
    clock = [1_000_000.0]
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"access_token": f"tok{len(requests)}", "expires_on": str(int(clock[0]) + 3600)})

    provider = build_token_provider("client-1")
    provider._endpoint, provider._header = "http://identity.invalid/token", "hdr"
    provider._client = httpx.Client(transport=httpx.MockTransport(handler))
    provider._now = lambda: clock[0]
    database = Database(URL, db_auth="entra", token_provider=provider)
    for _ in range(4):
        try_connect(database)
    assert len(requests) == 1
    assert {c["password"] for c in connects} == {"tok1"}
    assert requests[0].url.params["resource"] == DB_RESOURCE
    assert requests[0].url.params["client_id"] == "client-1"
    assert requests[0].headers["X-IDENTITY-HEADER"] == "hdr"
    clock[0] += 3600 - 60  # inside the refresh margin: a new token
    try_connect(database)
    assert len(requests) == 2 and connects[-1]["password"] == "tok2"


def test_fetch_failure_fails_the_connection_without_leaking(connects, caplog):
    class Broken:
        def get(self, timeout=None):
            raise RuntimeError(f"identity said {SECRET} X-IDENTITY-HEADER=hdr")

    database = Database(URL, db_auth="entra", token_provider=Broken())
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DbTokenError) as caught:
            database.engine.raw_connection()
    assert connects == []  # never reached the database
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert SECRET not in str(caught.value) and "hdr" not in str(caught.value)
    assert SECRET not in caplog.text and "hdr" not in caplog.text
    assert "could not be fetched" in caplog.text


def test_real_provider_error_response_does_not_leak(connects, caplog):
    def handler(request):
        return httpx.Response(500, text=f"boom {SECRET}")

    provider = build_token_provider()
    provider._endpoint, provider._header = "http://identity.invalid/token", "hdr-secret"
    provider._client = httpx.Client(transport=httpx.MockTransport(handler))
    database = Database(URL, db_auth="entra", token_provider=provider)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DbTokenError):
            database.engine.raw_connection()
    assert SECRET not in caplog.text and "hdr-secret" not in caplog.text


def alembic_config(url: str, **attributes) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    config.attributes.update(attributes)
    return config


def test_alembic_env_uses_the_token(connects):
    provider = FakeProvider(["mig-token"])
    with pytest.raises(Stop):
        command.upgrade(alembic_config(URL, db_auth="entra", token_provider=provider), "head")
    assert connects[0]["password"] == "mig-token" and connects[0]["user"] == "my-identity"
    assert provider.n == 1


def test_alembic_env_refuses_unsafe_url(connects):
    with pytest.raises(DbAuthConfigError):
        command.upgrade(alembic_config("postgresql+psycopg://x:pw@h/app?sslmode=verify-full", db_auth="entra",
                                       token_provider=FakeProvider()), "head")
    assert connects == []


def test_alembic_env_password_mode_has_no_hook(connects):
    with pytest.raises(Stop):
        command.upgrade(alembic_config("postgresql+psycopg://u:pw@localhost/x", db_auth="password",
                                       token_provider=FakeProvider(["never"])), "head")
    assert connects[0]["password"] == "pw"


def test_healthz_is_503_down_when_the_token_fetch_fails(app, connects):
    from fastapi.testclient import TestClient

    class Broken:
        def get(self, timeout=None):
            raise RuntimeError(SECRET)

    app.state.db.dispose()  # the fixture's own engine; its teardown disposes only what is in app.state.db
    app.state.db = Database(URL, db_auth="entra", token_provider=Broken())
    response = TestClient(app, base_url="https://testserver").get("/healthz")
    assert response.status_code == 503
    assert response.json()["db"] == "down"
    assert SECRET not in response.text
