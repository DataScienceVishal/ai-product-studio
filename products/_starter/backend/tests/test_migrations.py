"""Alembic: the whole chain upgrades and downgrades on a scratch database, and matches the models."""
import os
import secrets
import time

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from .conftest import _BASE_NAME, SHARED, TEST_DB, _create_run_db


@pytest.fixture
def scratch_url():
    if SHARED:
        pytest.skip("TEST_DATABASE_SHARED=1 means the user may not CREATE DATABASE, which this test needs")
    base = make_url(TEST_DB)
    # Same name shape and comment marker as the per-run database, so a killed run's leftover is reclaimed by the
    # stale cleanup in conftest instead of leaking.
    name = f"{_BASE_NAME}_t{int(time.time())}_{os.getpid()}_{secrets.token_hex(3)}"
    plain = base.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(plain, autocommit=True) as admin:
        _create_run_db(admin, name)
    try:
        yield base.set(database=name).render_as_string(hide_password=False)
    finally:
        with psycopg.connect(plain, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def _config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    config.attributes["db_auth"] = "password"
    return config


def _pending_index(url: str):
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_ai_usage_pending'")).scalar()
    finally:
        engine.dispose()


def test_pending_usage_partial_index_upgrades_and_downgrades(scratch_url):
    config = _config(scratch_url)
    command.upgrade(config, "0006")
    assert _pending_index(scratch_url) is None
    command.upgrade(config, "head")
    definition = _pending_index(scratch_url)
    assert definition and "(tenant_id, created_at)" in definition and "WHERE" in definition and "'pending'" in definition
    command.check(config)  # models and migrations agree, so autogenerate would add nothing
    command.downgrade(config, "0006")
    assert _pending_index(scratch_url) is None
    command.downgrade(config, "base")
    engine = create_engine(scratch_url)
    try:
        assert "ai_usage" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_scratch_database_carries_the_cleanup_marker(scratch_url):
    admin = make_url(scratch_url).set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    name = make_url(scratch_url).database
    with psycopg.connect(admin, autocommit=True) as conn:
        comment = conn.execute("SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = %s",
                               (name,)).fetchone()[0]
    assert comment == "starter-pytest-ephemeral"
    assert name.startswith(f"{_BASE_NAME}_t")


def test_pending_cancels_migration_upgrades_and_downgrades(scratch_url):
    config = _config(scratch_url)
    command.upgrade(config, "0009")
    engine = create_engine(scratch_url)
    try:
        assert "pending_cancels" not in inspect(engine).get_table_names()
        command.upgrade(config, "head")
        assert "pending_cancels" in inspect(engine).get_table_names()
        uniques = inspect(engine).get_unique_constraints("pending_cancels")
        assert any(u["column_names"] == ["provider", "ref"] for u in uniques)
        command.check(config)
        command.downgrade(config, "0009")
        assert "pending_cancels" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_pending_cancels_last_attempt_migration_upgrades_and_downgrades(scratch_url):
    config = _config(scratch_url)
    command.upgrade(config, "0010")
    engine = create_engine(scratch_url)
    try:
        assert "last_attempt_at" not in {c["name"] for c in inspect(engine).get_columns("pending_cancels")}
        command.upgrade(config, "head")
        column = {c["name"]: c for c in inspect(engine).get_columns("pending_cancels")}["last_attempt_at"]
        assert column["nullable"] is True and column["type"].timezone is True
        command.check(config)
        command.downgrade(config, "0010")
        assert "last_attempt_at" not in {c["name"] for c in inspect(engine).get_columns("pending_cancels")}
    finally:
        engine.dispose()


def test_billing_customers_migration_backfills_upgrades_and_downgrades(scratch_url):
    config = _config(scratch_url)
    command.upgrade(config, "0011")
    engine = create_engine(scratch_url)
    try:
        assert "billing_customers" not in inspect(engine).get_table_names()
        with engine.begin() as conn:  # t1: a Stripe customer; t2: none; t3 and t4 share one customer id
            for name in ("t1", "t2", "t3", "t4"):
                conn.execute(text("INSERT INTO tenants (id, name, created_at) VALUES (gen_random_uuid(), :n, now())"),
                             {"n": name})
            for name, provider, customer in (("t1", "stripe", "cus_A"), ("t2", "mock", None),
                                             ("t3", "stripe", "cus_SHARED"), ("t4", "stripe", "cus_SHARED")):
                conn.execute(text(
                    "INSERT INTO subscriptions (id, tenant_id, plan, status, provider, provider_customer, updated_at) "
                    "SELECT gen_random_uuid(), id, 'trial', 'trialing', :p, :c, now() FROM tenants WHERE name = :n"),
                    {"n": name, "p": provider, "c": customer})
        command.upgrade(config, "head")
        assert "billing_customers" in inspect(engine).get_table_names()
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT t.name, b.provider, b.customer_ref FROM billing_customers b JOIN tenants t ON t.id = b.tenant_id "
                "ORDER BY b.customer_ref")).all()
        # the NULL customer is skipped; the shared customer is kept for one tenant only (the migration must not fail)
        assert [(p, c) for _, p, c in rows] == [("stripe", "cus_A"), ("stripe", "cus_SHARED")]
        assert rows[0][0] == "t1" and rows[1][0] in {"t3", "t4"}
        command.check(config)
        command.downgrade(config, "0011")
        assert "billing_customers" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
