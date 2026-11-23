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
from sqlalchemy import func, select
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
    def __init__(self, message: str = "The AI service is busy right now. Please try again in a minute."):
        super().__init__(503, "ai_unavailable", message)


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


class AzureOpenAI:
    name = "azure"

    def __init__(self, endpoint: str, deployment: str, api_key: str, timeout: float = 30.0,
                 client: httpx.Client | None = None, retries: int = 3):
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
        self.url = endpoint.rstrip("/") + "/openai/v1/chat/completions"
        self.deployment = deployment
        self.headers = {"api-key": api_key or "proxy-injected", "Content-Type": "application/json"}
        self.client = client or httpx.Client(timeout=timeout)
        self.retries = retries

    def complete(self, system: str, user: str, max_output_tokens: int = 1200) -> AIResult:
        payload = {"model": self.deployment, "max_completion_tokens": max_output_tokens,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        for attempt in range(self.retries + 1):
            try:
                response = self.client.post(self.url, json=payload, headers=self.headers)
            except httpx.TransportError as error:  # timeouts and connection problems
                log.warning("ai call failed", extra={"attempt": attempt, "kind": type(error).__name__})
                if attempt == self.retries:
                    raise AIUnavailable() from error
                time.sleep(min(2 ** attempt, 8))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                log.warning("ai call throttled or failed", extra={"attempt": attempt, "status": response.status_code})
                if attempt == self.retries:
                    raise AIUnavailable()
                try:
                    wait = float(response.headers.get("retry-after", 2 ** attempt))
                except ValueError:
                    wait = 2 ** attempt
                time.sleep(min(wait, 8))
                continue
            if response.status_code in (401, 403):
                log.error("ai credentials rejected", extra={"status": response.status_code})
                raise AIUnavailable("The AI service isn't configured correctly. The team has been notified.")
            if response.status_code >= 400:
                log.error("ai request rejected", extra={"status": response.status_code})
                raise AppError(502, "ai_rejected", "The AI service couldn't handle that request.")
            return self._parse(response.json())
        raise AIUnavailable()  # unreachable, keeps type checkers calm

    def _parse(self, data: dict) -> AIResult:
        choice = (data.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content") or "").strip()
        usage = data.get("usage") or {}
        if not text:
            reason = choice.get("finish_reason")
            log.warning("ai returned no text", extra={"finish_reason": reason})
            raise AIUnavailable("The AI ran out of room before answering. Try a shorter input.")
        return AIResult(text=text, input_tokens=int(usage.get("prompt_tokens", 0)),
                        output_tokens=int(usage.get("completion_tokens", 0)), model=data.get("model", self.deployment))


def build_provider(settings) -> AIProvider:
    if settings.ai_provider == "azure":
        return AzureOpenAI(settings.azure_openai_endpoint, settings.azure_openai_deployment,
                           settings.azure_openai_api_key, settings.ai_timeout_seconds)
    return FakeAI()


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def tokens_this_month(db: Session, tenant_id: uuid.UUID) -> int:
    used = db.scalar(select(func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0))
                     .where(AIUsage.tenant_id == tenant_id, AIUsage.created_at >= month_start()))
    return int(used or 0)


def ensure_within_cap(db: Session, tenant_id: uuid.UUID, cap: int) -> None:
    """Checked before each call. Two concurrent calls can overshoot by one call's tokens; accepted."""
    if tokens_this_month(db, tenant_id) >= cap:
        raise AppError(429, "ai_cap_reached",
                       "You've used this month's AI allowance. It resets on the 1st, or upgrade your plan.")


def record_usage(db: Session, tenant_id: uuid.UUID, feature: str, result: AIResult) -> None:
    db.add(AIUsage(tenant_id=tenant_id, feature=feature, model=result.model,
                   input_tokens=result.input_tokens, output_tokens=result.output_tokens))
    log.info("ai usage", extra={"feature": feature, "input_tokens": result.input_tokens,
                                "output_tokens": result.output_tokens, "model": result.model})
