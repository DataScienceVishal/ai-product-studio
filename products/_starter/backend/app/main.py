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

from . import __version__, errors, spa
from .ai import AIProvider, AISlots, build_provider
from .billing import BillingProvider, build_billing
from .config import Settings
from .db import Database
from .email import EmailSender, OutboxEmail
from .logs import end_request_fields, request_id_var, setup_logging, start_request_fields
from .ratelimit import RateLimiter, build_redis_client
from .routes import account, auth, billing, health, notes, team

log = logging.getLogger("app.http")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"x-robots-tag", b"noindex, nofollow"),  # private demos until approved
    (b"cache-control", b"no-store"),
]
HSTS = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
API_CSP = (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")  # JSON only; docs are off in prod
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_EXEMPT = {"/api/billing/webhook"}  # called by the payment provider; protected by its signature


class CsrfGuard:
    """Pure ASGI: every cookie-authenticated write under /api needs an X-Requested-With header. Browsers
    can't add one cross-site without a CORS preflight, which CORS refuses for other origins. Global, so a
    new router can't forget it; the only exemption is listed above."""

    BODY = b'{"error":"csrf_check_failed","message":"Missing request header. Please reload the page and try again."}'

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (scope["type"] == "http" and scope.get("method") in UNSAFE_METHODS
                and scope.get("path", "").startswith("/api/") and scope.get("path") not in CSRF_EXEMPT
                and not dict(scope.get("headers") or []).get(b"x-requested-with")):
            await send({"type": "http.response.start", "status": 403,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": self.BODY})
            return
        await self.app(scope, receive, send)


class BodyTooLarge(Exception):
    pass


class BodyLimit:
    """Pure ASGI: refuse request bodies over `limit` bytes, by Content-Length or while streaming.

    Reading stops as soon as the limit is passed. FastAPI turns errors raised while it parses a body into
    its own 400, so once the limit is crossed we replace whatever response the app starts with our 413."""

    BODY = b'{"error":"too_large","message":"That request is too large."}'

    def __init__(self, app: ASGIApp, limit: int):
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope.get("headers") or []).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.limit:
            await self._refuse(send)
            return
        received, exceeded, refused = 0, False, False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    exceeded = True
                    raise BodyTooLarge()
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal refused
            if not exceeded:
                await send(message)
            elif not refused:
                refused = True
                await self._refuse(send)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except BodyTooLarge:
            if not refused:
                await self._refuse(send)

    async def _refuse(self, send: Send) -> None:
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(self.BODY)).encode())]})
        await send({"type": "http.response.body", "body": self.BODY})


class RequestContext:
    """Pure ASGI middleware: request id, access log, security headers, and a last-resort 500."""

    def __init__(self, app: ASGIApp, hsts: bool = False, strict_csp: bool = False):
        self.app = app
        self.headers = SECURITY_HEADERS + ([HSTS] if hsts else []) + ([API_CSP] if strict_csp else [])
        self.names = {name for name, _ in self.headers}
        self.spa_own = {b"cache-control", b"content-security-policy"}  # only responses the SPA module marked (index.html, /assets)

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
                own = self.spa_own if scope.get(spa.OWN_HEADERS) else set()
                headers = [h for h in message.get("headers", []) if h[0].lower() not in self.names - own]
                kept = {h[0].lower() for h in headers}
                extra = [h for h in self.headers if h[0] not in kept]
                message["headers"] = headers + extra + [(b"x-request-id", rid.encode())]
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
        app.state.limiter.shutdown()
        app.state.db.dispose()

    docs = None if settings.env == "prod" else "/api/docs"
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan, docs_url=docs,
                  redoc_url=None, openapi_url=None if settings.env == "prod" else "/api/openapi.json")
    app.state.settings = settings
    app.state.db = Database(settings.database_url, settings.db_statement_timeout_ms,
                            settings.db_idle_in_transaction_timeout_ms, settings.db_pool_size, settings.db_max_overflow,
                            db_auth=settings.db_auth, client_id=settings.azure_client_id)
    app.state.limiter = RateLimiter(redis_client=build_redis_client(settings.rate_limit_redis_url) if settings.rate_limit_redis_url else None,
                                    redis_prefix=f"rl:{settings.app_name}:{settings.env}:",
                                    redis_threads=settings.rate_limit_redis_threads,
                                    redis_queue_timeout=settings.rate_limit_redis_queue_timeout)
    app.state.ai = ai or build_provider(settings)
    app.state.ai_slots = AISlots(settings.ai_concurrent_calls)
    app.state.billing = billing_provider or build_billing(settings)
    app.state.email = email or OutboxEmail()
    if settings.env == "prod" and isinstance(app.state.email, OutboxEmail):
        log.warning("email goes to the in-memory outbox: password reset, verification and invitation emails "
                    "are not delivered. Fine for demos; a real email adapter needs approval")

    errors.install(app)
    app.add_middleware(BodyLimit, limit=settings.max_body_bytes)
    app.add_middleware(CsrfGuard)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["content-type", "x-requested-with", "x-request-id"])
    app.add_middleware(RequestContext, hsts=settings.cookie_secure, strict_csp=settings.env == "prod")  # outermost
    for router in (health.router, auth.router, notes.router, billing.router, account.router, team.router, team.public):
        app.include_router(router)
    spa.install(app, settings.frontend_dist)
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
