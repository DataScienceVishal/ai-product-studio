"""Alembic: the whole chain upgrades and downgrades on a scratch database, and matches the models."""
import secrets

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from .conftest import TEST_DB


@pytest.fixture
def scratch_url():
    base = make_url(TEST_DB)
    name = f"mig_{secrets.token_hex(4)}"
    plain = base.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(plain, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
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
