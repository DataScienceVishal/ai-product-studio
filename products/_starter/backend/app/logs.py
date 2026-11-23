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

_SENSITIVE = re.compile(r"pass(word)?|token|secret|authori[sz]ation|cookie|api[-_]?key|email", re.I)
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
            if key not in _STANDARD and not key.startswith("_"):
                entry[key] = "[redacted]" if _SENSITIVE.search(key) else value
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


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
