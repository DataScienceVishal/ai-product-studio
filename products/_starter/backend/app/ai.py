"""AI provider interface, a fake for dev/tests, Azure OpenAI, and per-tenant usage caps.

Azure OpenAI uses the v1 API: POST {endpoint}/openai/v1/chat/completions with an `api-key`
header and the deployment name as `model` (Microsoft Learn, checked 2026-11-23). In cloud runs
the key is injected by the environment's network secret, so AZURE_OPENAI_API_KEY holds only a
placeholder. gpt-5-mini is a reasoning model: max_completion_tokens covers reasoning too.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .errors import AppError
from .models import AIUsage

log = logging.getLogger("app.ai")


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

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult: ...


class FakeAI:
    """Deterministic stand-in: no network, no cost. Used in dev and tests."""
    name = "fake"

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult:
        words = [w for w in user.split() if not (w.startswith("<") and w.endswith(">"))]  # drop delimiters
        return AIResult(text="Summary: " + " ".join(words[:25]), input_tokens=len(system.split()) + len(words),
                        output_tokens=min(len(words), 25) + 1, model="fake")


def estimate_tokens(system: str, user: str, max_output_tokens: int) -> int:
    """Conservative: about 3 characters per token for the input, plus the whole output budget."""
    return (len(system) + len(user)) // 3 + max_output_tokens


class AzureOpenAI:
    name = "azure"

    def __init__(self, endpoint: str, deployment: str, api_key: str, timeout: float = 20.0, deadline: float = 25.0,
                 retries: int = 1, client: httpx.Client | None = None, sleep=time.sleep, clock=time.monotonic):
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
        self.url = endpoint.rstrip("/") + "/openai/v1/chat/completions"
        self.deployment = deployment
        self.headers = {"api-key": api_key or "proxy-injected", "Content-Type": "application/json"}
        self.client = client or httpx.Client(timeout=timeout)
        self.timeout, self.deadline, self.retries = timeout, deadline, retries
        self.sleep, self.clock = sleep, clock

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult:
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
                response = self.client.post(self.url, json=payload, headers=self.headers,
                                            timeout=min(self.timeout, remaining()))
            except (httpx.ConnectError, httpx.ConnectTimeout) as error:  # never reached the model: no cost
                log.warning("ai call failed", extra={"attempt": attempt, "kind": type(error).__name__})
                self._pause(attempt, None, remaining)
                continue
            except httpx.TransportError as error:  # sent, then timed out or dropped: it may have run and cost
                log.warning("ai call failed after sending", extra={"attempt": attempt, "kind": type(error).__name__})
                billed_in += estimate_tokens(system, user, 0)
                billed_out += max_output_tokens
                self._pause(attempt, None, remaining)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                log.warning("ai call throttled or failed", extra={"attempt": attempt, "status": response.status_code})
                self._pause(attempt, response.headers.get("retry-after"), remaining)
                continue
            if response.status_code in (401, 403):
                log.error("ai credentials rejected", extra={"status": response.status_code})
                raise fail("The AI service isn't configured correctly. The team has been notified.")
            if response.status_code >= 400:
                log.error("ai request rejected", extra={"status": response.status_code})
                raise AppError(502, "ai_rejected", "The AI service couldn't handle that request.")
            try:
                data = response.json()
            except ValueError:
                raise fail() from None
            usage = data.get("usage") or {}
            used_in, used_out = int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
            choice = (data.get("choices") or [{}])[0]
            text = ((choice.get("message") or {}).get("content") or "").strip()
            if not text:
                log.warning("ai returned no text", extra={"finish_reason": choice.get("finish_reason")})
                billed_in, billed_out = billed_in + used_in, billed_out + used_out
                raise fail("The AI ran out of room before answering. Try a shorter input.")
            return AIResult(text=text, input_tokens=used_in + billed_in, output_tokens=used_out + billed_out,
                            model=data.get("model", self.deployment))
        raise fail()

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
        return AzureOpenAI(settings.azure_openai_endpoint, settings.azure_openai_deployment,
                           settings.azure_openai_api_key, timeout=settings.ai_timeout_seconds,
                           deadline=settings.ai_deadline_seconds, retries=settings.ai_retries)
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


def tokens_today_all_tenants(db: Session) -> int:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used = db.scalar(select(func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0))
                     .where(AIUsage.created_at >= today))
    return int(used or 0)


def reserve(db: Session, tenant_id: uuid.UUID, cap: int, estimate: int, feature: str,
            global_daily_cap: int | None = None) -> uuid.UUID:
    """Reserve an estimated amount before calling the model, under Postgres advisory locks, so concurrent
    calls see each other's reservations. A tenant under its cap can make one call that ends slightly over;
    the next one is refused. Commits, so no transaction stays open during the AI call."""
    db.execute(text("SELECT pg_advisory_xact_lock(CAST(:key AS bigint))"), {"key": _tenant_lock(tenant_id)})
    if global_daily_cap is not None:
        db.execute(text("SELECT pg_advisory_xact_lock(CAST(:key AS bigint))"), {"key": GLOBAL_LOCK})
    if tokens_this_month(db, tenant_id) >= cap:
        db.rollback()
        raise AppError(429, "ai_cap_reached",
                       "You've used this month's AI allowance. It resets on the 1st, or upgrade your plan.")
    if global_daily_cap is not None and tokens_today_all_tenants(db) >= global_daily_cap:
        db.rollback()
        log.error("global daily AI budget reached")
        raise AppError(503, "ai_budget_reached", "The AI is resting until tomorrow. Everything else still works.")
    row = AIUsage(tenant_id=tenant_id, feature=f"{feature}:reserved", model="pending",
                  input_tokens=estimate, output_tokens=0)
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
