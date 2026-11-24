"""AI provider interface, a fake for dev/tests, Azure OpenAI, and per-tenant usage caps.

Azure OpenAI uses the v1 API (chat completions or responses): POST {endpoint}/openai/v1/chat/completions with an `api-key`
header and the deployment name as `model` (Microsoft Learn, checked 2026-11-23). In cloud runs
the key is injected by the environment's network secret, so AZURE_OPENAI_API_KEY holds only a
placeholder. gpt-5-mini is a reasoning model: max_completion_tokens covers reasoning too.

The studio's real deployment (a reasoning model) refuses chat/completions with HTTP 400 and supports only the
v1 Responses API: POST {endpoint}/openai/v1/responses with `input` (role/content items), `instructions` and
`max_output_tokens`. AZURE_OPENAI_API picks `chat` or `responses`; `auto` (default) uses responses when the
configured endpoint ends in /openai/v1/responses, else chat. The endpoint may be the resource root or end in
/openai/v1, /openai/v1/responses or /openai/v1/chat/completions (see normalise_endpoint).

With AZURE_OPENAI_AUTH=managed_identity there is no key: a bearer token for the app's managed identity
is fetched from the Container Apps identity endpoint (see ManagedIdentityToken) and sent as
`Authorization: Bearer`.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from datetime import timedelta
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .errors import AppError
from .models import AIUsage

log = logging.getLogger("app.ai")


def _count(value) -> int:
    """A usage count: never negative. Raises ValueError/TypeError/OverflowError on junk (callers bill the budget)."""
    return max(int(value or 0), 0)


def _reason(value) -> str | None:
    """A 'why' for the user message: a string or None, whatever junk the provider sent."""
    return value if isinstance(value, str) else (None if value is None else "unknown")


def _dicts(value) -> list[dict]:
    """The dict items of a provider list; anything malformed counts as no items."""
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


@dataclass(frozen=True)
class AIResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class AIUnavailable(AppError):
    """The call failed. `input_tokens`/`output_tokens` are what the provider may have billed anyway
    (an empty answer still costs, and a timed-out request may have run), so callers record them."""

    def __init__(self, message: str = "The AI service is busy right now. Please try again in a minute.",
                 input_tokens: int = 0, output_tokens: int = 0):
        super().__init__(503, "ai_unavailable", message)
        self.input_tokens, self.output_tokens = input_tokens, output_tokens


class AIProvider(Protocol):
    name: str
    output_headroom: int  # extra output tokens the provider may add to a call's budget (reasoning); reserve them too

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult: ...


class FakeAI:
    """Deterministic stand-in: no network, no cost. Used in dev and tests."""
    name = "fake"
    output_headroom = 0

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult:
        words = [w for w in user.split() if not (w.startswith("<") and w.endswith(">"))]  # drop delimiters
        return AIResult(text="Summary: " + " ".join(words[:25]), input_tokens=len(system.split()) + len(words),
                        output_tokens=min(len(words), 25) + 1, model="fake")


def estimate_tokens(system: str, user: str, max_output_tokens: int) -> int:
    """An upper bound: every token is at least one byte of UTF-8, so input bytes bound input tokens
    (characters don't: some scripts take several tokens per character). Plus the whole output budget."""
    return len(system.encode("utf-8")) + len(user.encode("utf-8")) + max_output_tokens


def reservation_estimate(provider, system: str, user: str, max_output_tokens: int) -> int:
    """estimate_tokens plus the provider's reasoning headroom, so a reservation covers what may be billed."""
    return estimate_tokens(system, user, max_output_tokens + int(provider.output_headroom))  # no default: fail loudly


class AISlots:
    """In-process cap on simultaneous AI calls, so slow calls can't occupy every request thread."""

    def __init__(self, size: int):
        self._slots = threading.BoundedSemaphore(size)

    def __enter__(self):
        if not self._slots.acquire(timeout=2.0):
            raise AppError(503, "ai_busy", "The AI is busy with other requests. Please try again in a moment.",
                           headers={"Retry-After": "10"})
        return self

    def __exit__(self, *exc) -> None:
        self._slots.release()


class _CallerTimeout(AIUnavailable):
    """The token fetch ran out of the caller's own (short) budget. Never cached as an endpoint failure."""


class ManagedIdentityToken:
    """Bearer tokens for Azure OpenAI from the Container Apps managed identity endpoint.

    Contract (Microsoft Learn, "Managed identities in Azure Container Apps", REST endpoint reference,
    https://learn.microsoft.com/azure/container-apps/managed-identity#rest-endpoint-reference, checked 2026-11-23):
    GET $IDENTITY_ENDPOINT?resource=<audience>&api-version=2019-08-01 with header `X-IDENTITY-HEADER:
    $IDENTITY_HEADER`; optional `client_id` picks a user-assigned identity (without it the system-assigned
    identity is used). The answer is JSON with `access_token` and `expires_on` (epoch seconds, as a string).
    Tokens are cached until `refresh_margin` seconds before expiry; one lock makes concurrent callers share
    a single fetch. The token and the identity header are never logged or put in an error message."""

    RESOURCE = "https://cognitiveservices.azure.com"  # scope https://cognitiveservices.azure.com/.default
    API_VERSION = "2019-08-01"

    def __init__(self, client_id: str = "", endpoint: str | None = None, header: str | None = None,
                 client: httpx.Client | None = None, timeout: float = 5.0, refresh_margin: float = 300.0,
                 now=time.time, monotonic=time.monotonic, resource: str | None = None):
        self.client_id = client_id
        self.resource = resource or self.RESOURCE  # the audience; one instance (and cache) per audience
        self._endpoint = endpoint if endpoint is not None else os.environ.get("IDENTITY_ENDPOINT", "")
        self._header = header if header is not None else os.environ.get("IDENTITY_HEADER", "")
        self._client = client or httpx.Client(timeout=timeout)
        self._timeout, self._margin, self._now, self._mono = timeout, refresh_margin, now, monotonic
        self._lock = threading.Lock()
        self._token = ""
        self._expires_on = 0.0
        self._failed_until = 0.0  # a failed fetch is remembered until then, so queued callers fail fast
        self._failure: AIUnavailable | None = None

    FAILURE_TTL = 10.0

    def get(self, timeout: float | None = None) -> str:
        """`timeout` is the caller's remaining deadline. It bounds the lock wait and the fetch together: the
        fetch gets only what is left after the wait, so `get(t)` never takes much longer than t.

        Only a failure of the endpoint itself is remembered (for FAILURE_TTL). A timeout caused by the caller's
        own short budget says nothing about the endpoint, so it is raised but not cached."""
        budget = self._timeout if timeout is None else min(self._timeout, timeout)
        if budget <= 0:
            raise AIUnavailable()
        started = self._mono()
        if not self._lock.acquire(timeout=budget):
            log.warning("managed identity token wait timed out")
            raise AIUnavailable()
        try:
            if self._token and self._now() < self._expires_on - self._margin:
                return self._token
            if self._failure is not None and self._mono() < self._failed_until:
                raise AIUnavailable(self._failure.message)
            left = budget - (self._mono() - started)
            if left <= 0:
                raise AIUnavailable()
            try:
                self._token, self._expires_on = self._fetch(left, short=left < self._timeout - _TIMEOUT_MARGIN)
            except _CallerTimeout:
                raise  # the caller's own deadline, not an endpoint failure: do not cache
            except AIUnavailable as error:
                self._failure, self._failed_until = error, self._mono() + self.FAILURE_TTL
                raise
            self._failure = None
            return self._token
        finally:
            self._lock.release()

    def invalidate(self) -> None:
        """Forget the cached token (the service rejected it), so the next call fetches a fresh one.
        It leaves a remembered fetch failure alone: that expires by itself after FAILURE_TTL."""
        with self._lock:
            self._token, self._expires_on = "", 0.0

    def _fetch(self, timeout: float, short: bool = False) -> tuple[str, float]:
        if not self._endpoint or not self._header:
            log.error("managed identity endpoint is not available")
            raise AIUnavailable("The AI service isn't configured correctly. The team has been notified.")
        params = {"resource": self.resource, "api-version": self.API_VERSION}
        if self.client_id:
            params["client_id"] = self.client_id
        try:
            response = self._client.get(self._endpoint, params=params, headers={"X-IDENTITY-HEADER": self._header},
                                        timeout=timeout)
        except httpx.TimeoutException as error:
            log.log(logging.WARNING if short else logging.ERROR, "managed identity token request failed",
                    extra={"kind": type(error).__name__})
            if short:  # timed out on a budget shorter than our own timeout: the caller's deadline, not the endpoint
                raise _CallerTimeout() from None
            raise AIUnavailable() from None
        except httpx.HTTPError as error:  # only the class name: messages can echo the URL
            log.error("managed identity token request failed", extra={"kind": type(error).__name__})
            raise AIUnavailable() from None
        if response.status_code != 200:
            log.error("managed identity token request rejected", extra={"status": response.status_code})
            raise AIUnavailable("The AI service isn't configured correctly. The team has been notified.") from None
        try:
            data = response.json()
            token, expires_on = str(data["access_token"]), float(data["expires_on"])
            if not token:
                raise ValueError
        except (ValueError, KeyError, TypeError):
            log.error("managed identity token response was malformed")
            raise AIUnavailable() from None
        return token, expires_on


_TIMEOUT_MARGIN = 0.05  # seconds: a budget this much below the full timeout counts as a shortened (caller-limited) call

_ENDPOINT_SUFFIXES = ("/openai/v1/chat/completions", "/openai/v1/responses", "/openai/v1", "/openai")


def normalise_endpoint(endpoint: str) -> str:
    """The resource root (no trailing slash, no API path), from a root or any known /openai/... form."""
    root = endpoint.strip().rstrip("/")
    if "?" in root or "#" in root:
        raise ValueError("AZURE_OPENAI_ENDPOINT must not contain a query string or fragment; the API version is fixed (v1)")
    for suffix in _ENDPOINT_SUFFIXES:
        if root.lower().endswith(suffix):
            return root[: -len(suffix)].rstrip("/")
    return root


_NO_ANSWER = {
    "max_output_tokens": "The AI ran out of room before finishing its answer. Try a shorter input.",
    "length": "The AI ran out of room before finishing its answer. Try a shorter input.",
    "reasoning": "The AI spent its whole allowance thinking and didn't answer. Try a shorter or simpler input.",
    "content_filter": "The AI's safety filter blocked this answer. Try rewording the note.",
    "refusal": "The AI declined to answer this note. Try rewording it.",
    "failed": "The AI couldn't finish this request. Please try again.",
    None: "The AI returned no answer. Please try again.",
}


class AzureOpenAI:
    name = "azure"

    def __init__(self, endpoint: str, deployment: str, api_key: str, timeout: float = 20.0, deadline: float = 25.0,
                 retries: int = 1, client: httpx.Client | None = None, sleep=time.sleep, clock=time.monotonic,
                 token_provider: ManagedIdentityToken | None = None, api: str = "auto",
                 reasoning_headroom: int = 0):
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
        if api not in ("auto", "chat", "responses"):
            raise ValueError("AZURE_OPENAI_API must be auto, chat or responses")
        if api == "auto":
            api = "responses" if endpoint.strip().rstrip("/").lower().endswith("/openai/v1/responses") else "chat"
        self.api = api
        # Responses reasoning tokens count inside max_output_tokens: add headroom so reasoning can't eat the answer.
        self.output_headroom = max(int(reasoning_headroom), 0) if api == "responses" else 0
        path = "/openai/v1/responses" if api == "responses" else "/openai/v1/chat/completions"
        self.url = normalise_endpoint(endpoint) + path
        self.deployment = deployment
        self.token_provider = token_provider  # set: bearer token from the managed identity, no api-key
        self.headers = {"api-key": api_key or "proxy-injected", "Content-Type": "application/json"}
        self.client = client or httpx.Client(timeout=timeout)
        self.timeout, self.deadline, self.retries = timeout, deadline, retries
        self.sleep, self.clock = sleep, clock

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult:
        if self.api == "responses":  # reasoning tokens count inside max_output_tokens
            max_output_tokens += self.output_headroom  # the wanted answer length is then still available
            payload = {"model": self.deployment, "instructions": system, "max_output_tokens": max_output_tokens,
                       "store": False,  # Azure keeps no copy of the prompt or answer (DATA.md)
                       "input": [{"role": "user", "content": user}]}
        else:
            payload = {"model": self.deployment, "max_completion_tokens": max_output_tokens,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        started = self.clock()
        billed_in = billed_out = 0  # from attempts that failed but may have cost money

        def remaining() -> float:
            return self.deadline - (self.clock() - started)

        def fail(message: str | None = None) -> AIUnavailable:
            return AIUnavailable(message or AIUnavailable().message, billed_in, billed_out)

        for attempt in range(self.retries + 1):
            if remaining() < 1.0:
                break
            try:
                headers = self.headers
                if self.token_provider is not None:  # may raise AIUnavailable; nothing was sent, so nothing billed
                    headers = {"Authorization": f"Bearer {self.token_provider.get(remaining())}", "Content-Type": "application/json"}
                if remaining() < 1.0:  # the token wait used the budget: never hand httpx a tiny or negative timeout
                    break
                response = self.client.post(self.url, json=payload, headers=headers,
                                            timeout=min(self.timeout, remaining()))
            except (httpx.ConnectError, httpx.ConnectTimeout) as error:  # never reached the model: no cost
                log.warning("ai call failed", extra={"attempt": attempt, "kind": type(error).__name__})
                self._pause(attempt, None, remaining)
                continue
            except httpx.TransportError as error:  # sent, then timed out or dropped: it may have run and cost
                log.warning("ai call failed after sending", extra={"attempt": attempt, "kind": type(error).__name__})
                billed_in += estimate_tokens(system, user, 0)
                billed_out += max_output_tokens
                raise fail() from None  # no retry: a second send could be billed again on top of the first
            if response.status_code == 429 or response.status_code >= 500:
                log.warning("ai call throttled or failed", extra={"attempt": attempt, "status": response.status_code})
                self._pause(attempt, response.headers.get("retry-after"), remaining)
                continue
            if response.status_code in (401, 403):
                log.error("ai credentials rejected", extra={"status": response.status_code})
                if self.token_provider is not None:
                    self.token_provider.invalidate()
                raise fail("The AI service isn't configured correctly. The team has been notified.")
            if response.status_code >= 400:
                log.error("ai request rejected", extra={"status": response.status_code})
                raise AppError(502, "ai_rejected", "The AI service couldn't handle that request.")
            try:
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError
            except ValueError:  # a 200 we can't read: it may have run, so bill the whole budget (as a timeout)
                billed_in += estimate_tokens(system, user, 0)
                billed_out += max_output_tokens
                raise fail() from None
            try:
                used_in, used_out, text, why = self._parse(data)
            except (TypeError, ValueError, AttributeError, OverflowError):  # malformed body: it ran, so bill what we can't read
                log.warning("ai response could not be parsed")
                billed_in += estimate_tokens(system, user, 0)
                billed_out += max_output_tokens
                raise fail() from None
            billed_in, billed_out = billed_in + used_in, billed_out + used_out
            if why is not None or not text:
                log.warning("ai returned no usable answer", extra={"finish_reason": why})
                raise fail(_NO_ANSWER.get(why, _NO_ANSWER[None]))
            return AIResult(text=text, input_tokens=billed_in, output_tokens=billed_out,
                            model=data.get("model", self.deployment))
        raise fail()

    def _parse(self, data: dict) -> tuple[int, int, str, str | None]:
        """(input tokens, output tokens, text, why there is no text) for either API."""
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        if self.api == "chat":
            choices = data.get("choices")
            choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
            message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
            content = message.get("content")
            text = content.strip() if isinstance(content, str) else ""
            # chat keeps its old rule: any text is an answer, even when finish_reason is "length"
            return (_count(usage.get("prompt_tokens")), _count(usage.get("completion_tokens")), text,
                    None if text else _reason(choice.get("finish_reason")))
        output = _dicts(data.get("output"))
        parts = [part.get("text") or "" for item in output if item.get("type") == "message"
                 for part in _dicts(item.get("content")) if part.get("type") == "output_text"
                 if isinstance(part.get("text"), str)]
        refused = any(part.get("type") == "refusal" for item in output if item.get("type") == "message"
                      for part in _dicts(item.get("content")))
        used_out = _count(usage.get("output_tokens"))
        details = usage.get("output_tokens_details")
        reasoning = _count(details.get("reasoning_tokens")) if isinstance(details, dict) else 0
        text = "".join(parts).strip()
        why = None
        if data.get("status") not in (None, "completed"):  # incomplete or failed: never saved as a success
            why = data.get("status")
            incomplete = data.get("incomplete_details")
            if why == "incomplete":
                why = (incomplete.get("reason") if isinstance(incomplete, dict) else None) or "max_output_tokens"
            if why == "max_output_tokens" and not text and used_out and reasoning >= used_out:
                why = "reasoning"  # all of the budget went on thinking
        elif not text and refused:
            why = "refusal"
        return _count(usage.get("input_tokens")), used_out, text, _reason(why)

    def _pause(self, attempt: int, retry_after: str | None, remaining) -> None:
        if attempt >= self.retries:
            return  # no more attempts: don't sleep for nothing
        try:
            wait = float(retry_after) if retry_after else 2.0 ** attempt
        except ValueError:
            wait = 2.0 ** attempt
        wait = min(wait, 8.0, max(remaining() - 1.0, 0.0))
        if wait > 0:
            self.sleep(wait)


def build_provider(settings) -> AIProvider:
    if settings.ai_provider == "azure":
        token = ManagedIdentityToken(settings.azure_client_id) if settings.azure_openai_auth == "managed_identity" else None
        return AzureOpenAI(settings.azure_openai_endpoint, settings.azure_openai_deployment,
                           settings.azure_openai_api_key, timeout=settings.ai_timeout_seconds,
                           deadline=settings.ai_deadline_seconds, retries=settings.ai_retries,
                           token_provider=token, api=settings.azure_openai_api,
                           reasoning_headroom=settings.ai_reasoning_headroom)
    return FakeAI()


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def tokens_this_month(db: Session, tenant_id: uuid.UUID) -> int:
    used = db.scalar(select(func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0))
                     .where(AIUsage.tenant_id == tenant_id, AIUsage.created_at >= month_start()))
    return int(used or 0)


GLOBAL_LOCK = 7_350_001  # pg advisory lock id for the cross-tenant daily budget


def _tenant_lock(tenant_id: uuid.UUID) -> int:
    return tenant_id.int & 0x7FFF_FFFF_FFFF_FFFF


def _today() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def tokens_today_all_tenants(db: Session) -> int:
    used = db.scalar(select(func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0))
                     .where(AIUsage.created_at >= _today()))  # includes deleted tenants' rows (tenant_id NULL)
    return int(used or 0)


def trial_tokens_today(db: Session) -> int:
    used = db.scalar(select(func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0))
                     .where(AIUsage.created_at >= _today(), AIUsage.trial.is_(True)))
    return int(used or 0)


def tokens_today(db: Session, tenant_id: uuid.UUID) -> int:
    used = db.scalar(select(func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0))
                     .where(AIUsage.tenant_id == tenant_id, AIUsage.created_at >= _today()))
    return int(used or 0)


def reserve(db: Session, tenant_id: uuid.UUID, cap: int, estimate: int, feature: str,
            global_daily_cap: int | None = None, daily_cap: int | None = None, max_in_flight: int | None = None,
            in_flight_window: timedelta = timedelta(minutes=2), trial: bool = False,
            trial_pool_cap: int | None = None) -> uuid.UUID:
    """Reserve an upper-bound estimate before calling the model, under Postgres advisory locks, so concurrent
    calls see each other's reservations. A call is refused if it *would* cross any cap: the plan's monthly
    allowance, a daily cap (trials), or the studio-wide daily budget. At most `max_in_flight` calls per tenant
    run at once. Commits, so no transaction stays open during the AI call."""
    db.execute(text("SELECT pg_advisory_xact_lock(CAST(:key AS bigint))"), {"key": _tenant_lock(tenant_id)})
    if global_daily_cap is not None:
        db.execute(text("SELECT pg_advisory_xact_lock(CAST(:key AS bigint))"), {"key": GLOBAL_LOCK})

    def refuse(status: int, code: str, message: str):
        db.rollback()
        raise AppError(status, code, message)

    if max_in_flight is not None:
        pending = db.scalar(select(func.count()).select_from(AIUsage).where(
            AIUsage.tenant_id == tenant_id, AIUsage.model == "pending",
            AIUsage.created_at > datetime.now(timezone.utc) - in_flight_window))
        if pending >= max_in_flight:
            refuse(429, "ai_in_progress", "Your other AI requests are still running. Try again when they finish.")
    if tokens_this_month(db, tenant_id) + estimate > cap:
        refuse(429, "ai_cap_reached", "You've used this month's AI allowance. It resets on the 1st, or upgrade your plan.")
    if daily_cap is not None and tokens_today(db, tenant_id) + estimate > daily_cap:
        refuse(429, "ai_daily_cap_reached", "You've reached today's AI allowance for the free trial. It resets at midnight (UTC).")
    if trial and trial_pool_cap is not None and trial_tokens_today(db) + estimate > trial_pool_cap:
        refuse(503, "ai_trial_pool_reached", "Free-trial AI is busy for today. It resets at midnight (UTC); paid plans aren't affected.")
    if global_daily_cap is not None and tokens_today_all_tenants(db) + estimate > global_daily_cap:
        log.error("global daily AI budget reached")
        refuse(503, "ai_budget_reached", "The AI is resting until tomorrow. Everything else still works.")
    row = AIUsage(tenant_id=tenant_id, feature=f"{feature}:reserved", model="pending",
                  input_tokens=estimate, output_tokens=0, trial=trial)
    db.add(row)
    db.commit()
    return row.id


def settle(db: Session, reservation_id: uuid.UUID, feature: str, input_tokens: int, output_tokens: int,
           model: str) -> None:
    """Replace a reservation with what was actually used (or billed, for failed calls)."""
    row = db.get(AIUsage, reservation_id)
    if row is None:  # the tenant was deleted meanwhile
        return
    row.feature, row.model, row.input_tokens, row.output_tokens = feature, model, input_tokens, output_tokens
    db.commit()
    log.info("ai usage", extra={"feature": feature, "input_tokens": input_tokens, "output_tokens": output_tokens,
                                "model": model})
