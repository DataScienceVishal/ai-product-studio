"""The per-run test DB cleanup drops only what conftest made, and the base name is validated."""
import secrets
import time

import psycopg
import pytest
from psycopg import sql

from tests import conftest as c

OLD = int(time.time()) - 10 * 24 * 3600


@pytest.fixture
def admin():
    if c.SHARED:
        pytest.skip("needs CREATE DATABASE (TEST_DATABASE_SHARED=1)")
    conn = c._admin_conn()
    yield conn
    conn.close()


def _make(conn, name, comment=None):
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    if comment:
        conn.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(name), sql.Literal(comment)))


def _exists(conn, name):
    return conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone() is not None


def test_stale_cleanup_only_drops_marked_exact_names(admin):
    base = f"tdbc{secrets.token_hex(3)}"
    stale = f"{base}_t{OLD}_123_{secrets.token_hex(3)}"
    recent = f"{base}_t{int(time.time())}_123_{secrets.token_hex(3)}"
    keep = [f"{base}_t1_1_a", f"{base}_t15", f"{base}_keep", f"{base}_t{OLD}_123_abcdef"]  # last: no marker
    names = [stale, recent] + keep
    try:
        for n in names:
            _make(admin, n, None if n == keep[-1] else c._MARKER if n in (stale, recent) else "hand made")
        dropped = c._drop_stale(admin, base)
        assert dropped == [stale]
        assert not _exists(admin, stale)
        for n in [recent] + keep:
            assert _exists(admin, n), n
    finally:
        for n in names:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(n)))


def test_marked_name_with_other_base_survives(admin):
    base = f"tdbc{secrets.token_hex(3)}"
    other = f"{base}x_t{OLD}_123_abcdef"
    try:
        _make(admin, other, c._MARKER)
        assert c._drop_stale(admin, base) == []
        assert _exists(admin, other)
    finally:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(other)))


@pytest.mark.parametrize("name", ['inj" OWNER "postgres" --', "a;b", "1abc", "a-b", "", "x" * 42, "a b"])
def test_bad_base_name_refused(name):
    with pytest.raises(pytest.exit.Exception):
        c._check_base_name(name)


@pytest.mark.parametrize("name", ["starter_test", "_x", "A1_b", "x" * 41])
def test_good_base_name_accepted(name):
    c._check_base_name(name)
