"""App factory. `uvicorn app.main:app` for servers; tests call create_app(settings, ...)."""
from __future__ import annotations

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import __version__, errors
from .ai import AIProvider, build_provider
from .billing import BillingProvider, build_billing
from .config import Settings
from .db import Database
from .email import EmailSender, OutboxEmail
from .logs import end_request_fields, request_id_var, setup_logging, start_request_fields
from .ratelimit import RateLimiter
from .routes import account, auth, billing, health, notes

log = logging.getLogger("app.http")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"x-robots-tag", b"noindex, nofollow"),  # private demos until approved
    (b"cache-control", b"no-store"),
]


class RequestContext:
    """Pure ASGI middleware: request id, access log, security headers, and a last-resort 500."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode(errors="ignore")
        rid = incoming if REQUEST_ID.match(incoming) else uuid.uuid4().hex
        rid_token, fields_token = request_id_var.set(rid), start_request_fields()
        started, status, response_started = time.perf_counter(), 500, False

        async def send_wrapper(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status, response_started = message["status"], True
                headers = [h for h in message.get("headers", []) if h[0].lower() not in {k for k, _ in SECURITY_HEADERS}]
                message["headers"] = headers + SECURITY_HEADERS + [(b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("unhandled error", extra={"path": scope.get("path")})
            if not response_started:
                body = (b'{"error":"internal_error","message":"Something went wrong on our side. '
                        b'Please try again.","request_id":"' + rid.encode() + b'"}')
                await send_wrapper({"type": "http.response.start", "status": 500,
                                    "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
        finally:
            log.info("request", extra={"method": scope.get("method"), "path": scope.get("path"), "status": status,
                                       "duration_ms": round((time.perf_counter() - started) * 1000, 1)})
            request_id_var.reset(rid_token)
            end_request_fields(fields_token)


def create_app(settings: Settings | None = None, *, ai: AIProvider | None = None,
               billing_provider: BillingProvider | None = None, email: EmailSender | None = None) -> FastAPI:
    settings = settings or Settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.db.dispose()

    docs = None if settings.env == "prod" else "/api/docs"
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan, docs_url=docs,
                  redoc_url=None, openapi_url=None if settings.env == "prod" else "/api/openapi.json")
    app.state.settings = settings
    app.state.db = Database(settings.database_url, settings.db_statement_timeout_ms)
    app.state.limiter = RateLimiter()
    app.state.ai = ai or build_provider(settings)
    app.state.billing = billing_provider or build_billing(settings)
    app.state.email = email or OutboxEmail()

    errors.install(app)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["content-type", "x-requested-with", "x-request-id"])
    app.add_middleware(RequestContext)  # added last, so it runs outermost
    for module in (health, auth, notes, billing, account):
        app.include_router(module.router)
    return app


_app: FastAPI | None = None


def __getattr__(name: str):
    """`uvicorn app.main:app` builds the app on first access, so importing this module
    (as tests do) needs no settings or database."""
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
