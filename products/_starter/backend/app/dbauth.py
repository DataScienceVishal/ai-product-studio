"""Passwordless Postgres sign-in with Microsoft Entra ID (DB_AUTH=entra), ADR 0002 decisions 5 and 6.

The DATABASE_URL carries host, database and user (the Entra role name, e.g. the managed identity's name) and no
password. On every NEW pooled connection a token for the managed identity is fetched and passed as the password.
Contract (Microsoft Learn, "Connect with managed identity in Azure Database for PostgreSQL flexible server",
https://learn.microsoft.com/azure/postgresql/security/security-connect-with-managed-identity, checked 2026-11-24):
audience/resource `https://ossrdbms-aad.database.windows.net`, and "you pass the access token in the password
field". From Container Apps the token comes from the IDENTITY_ENDPOINT (ManagedIdentityToken), not the VM metadata
address. Tokens live 5 to 60 minutes. Postgres checks the token only when a connection is made, so an open
connection keeps working after its token expires; pool_recycle just stops connections living much longer than that.

Tokens and identity headers are never logged or put in an error message.
"""
from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine, make_url


log = logging.getLogger("app.dbauth")

DB_RESOURCE = "https://ossrdbms-aad.database.windows.net"
# Below the shortest token lifetime we rely on (the token is only checked at connect time, see above).
ENTRA_POOL_RECYCLE_SECONDS = 45 * 60


class DbAuthConfigError(ValueError):
    """DB_AUTH=entra with an unsafe DATABASE_URL. The message never contains the URL."""


class DbTokenError(SQLAlchemyError):
    """A database access token could not be fetched. The connection attempt fails; nothing sensitive in the message."""


def validate_entra_url(url: str) -> None:
    try:
        parsed = make_url(url)
    except Exception:  # noqa: BLE001  (the parse error text can echo the URL)
        raise DbAuthConfigError("DATABASE_URL is not a valid database URL") from None
    if not parsed.drivername.startswith("postgresql"):
        raise DbAuthConfigError("DB_AUTH=entra needs a PostgreSQL DATABASE_URL")
    # Also refuse a password or passfile in the query string: SQLAlchemy would print it in repr(engine) and logs.
    if parsed.password or any(key in parsed.query for key in ("password", "passfile")):
        raise DbAuthConfigError("DATABASE_URL must not contain a password with DB_AUTH=entra (the token is the password)")
    if not parsed.username:
        raise DbAuthConfigError("DATABASE_URL must name the Entra role as the user with DB_AUTH=entra")
    if parsed.query.get("sslmode") != "verify-full":
        raise DbAuthConfigError("DATABASE_URL needs sslmode=verify-full with DB_AUTH=entra (ADR 0002)")


def build_token_provider(client_id: str = ""):
    from .ai import ManagedIdentityToken  # late: ai imports models, which import db, which imports this module
    # Margin 2 minutes: tokens last at least 5 minutes, so one is fetched at most about every 3 minutes under load.
    return ManagedIdentityToken(client_id, resource=DB_RESOURCE, refresh_margin=120.0)


def attach_entra_token(engine: Engine, provider) -> None:
    """Pass a fresh token as the password of every new DBAPI connection. `provider.get()` returns the token."""

    @event.listens_for(engine, "do_connect")
    def _inject_token(dialect, conn_rec, cargs, cparams):  # noqa: ANN001
        try:
            cparams["password"] = provider.get()
        except Exception as error:  # noqa: BLE001  (the message may carry provider detail: log the class only)
            log.error("database access token could not be fetched", extra={"kind": type(error).__name__})
            raise DbTokenError("could not get a database access token from the managed identity") from None
