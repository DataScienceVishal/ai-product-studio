"""Structured JSON logs with request ids. Never log secrets or personal data.

Log ids (user_id, tenant_id), never emails, names, passwords, tokens or note text.
Sensitive-looking keys passed as `extra` are redacted as a safety net.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import traceback
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
# One dict per request. Sync dependencies and endpoints run in separate threadpool calls, each with a
# copy of the context; the copies share this dict by reference, so bind() in one is seen by all.
_request_fields: contextvars.ContextVar[dict | None] = contextvars.ContextVar("request_fields", default=None)


def start_request_fields() -> contextvars.Token:
    return _request_fields.set({})


def end_request_fields(token: contextvars.Token) -> None:
    _request_fields.reset(token)


def bind(**fields: str) -> None:
    """Attach ids (never personal data) to every log line for the rest of this request."""
    current = _request_fields.get()
    if current is not None:
        current.update(fields)

# Whole key names (optionally prefixed, like new_password), so "input_tokens" is kept but "token" is not.
_SENSITIVE = re.compile(r"(?:\w+_)?(?:pass(?:word)?|token|secret|authori[sz]ation|cookie|api[-_]?key|e?mail|to)", re.I)
_DROP = {"color_message"}  # uvicorn adds a copy of the message with ANSI colour codes
_STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "tenant_id": "-",
        }
        entry.update(_request_fields.get() or {})
        for key, value in vars(record).items():
            if key not in _STANDARD and key not in _DROP and not key.startswith("_"):
                entry[key] = "[redacted]" if _SENSITIVE.fullmatch(key) else value
        if record.exc_info:
            entry["error"] = safe_exception(record.exc_info)
        return json.dumps(entry, default=str)


def safe_exception(exc_info) -> str:
    """Stack trace plus a message that can't carry personal data. Database errors can quote row values
    (for example 'Key (email)=(...) already exists'), so for those only the type and SQLSTATE are kept."""
    kind, error, tb = exc_info
    if error is None:
        return ""
    stack = "".join(traceback.format_tb(tb))
    orig = getattr(error, "orig", None)  # SQLAlchemy wraps the driver's error
    sqlstate = getattr(orig, "sqlstate", None) or getattr(error, "sqlstate", None)
    is_db_error = sqlstate is not None or type(error).__module__.startswith(("sqlalchemy", "psycopg"))
    if is_db_error:
        return f"{stack}{kind.__name__}: database error (sqlstate {sqlstate or 'unknown'}); details hidden"
    return f"{stack}{kind.__name__}: {error}"


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):  # route uvicorn's own lines through the JSON handler
        server_log = logging.getLogger(name)
        server_log.handlers.clear()
        server_log.propagate = True
    logging.getLogger("uvicorn.access").disabled = True  # our middleware writes the access line
