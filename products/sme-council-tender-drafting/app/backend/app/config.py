"""Settings come only from environment variables (or a local, gitignored .env)."""
from __future__ import annotations

import secrets
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .aicost import DEFAULT_MONTHLY_BUDGET_USD, check_ai_budget
from .dbauth import validate_entra_url

MIN_WEBHOOK_SECRET = 32
# The one list of accepted values (ai.py imports it). gpt-5.4-pro rejects "low"; other deployments accept it.
REASONING_EFFORTS = ("low", "medium", "high", "xhigh")
FRONTEND_TIMEOUT_MARGIN_SECONDS = 2.0
MAX_TIMEOUT_SECONDS = 600.0  # the frontend also clamps to this (a larger setTimeout overflows and fires at once)


class Settings(BaseSettings):
    # hide_input_in_errors: a validation error must never echo the settings (API key, deployment name) into the logs
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "tender"
    database_url: str = "postgresql+psycopg://studio:studio@localhost:5432/starter_dev"
    # password: the URL carries the password. entra: no password in the URL, a managed-identity token is the password
    # (app/dbauth.py, README "Entra ID database sign-in"). AZURE_CLIENT_ID below picks a user-assigned identity.
    db_auth: Literal["password", "entra"] = "password"
    db_statement_timeout_ms: int = 10_000
    db_idle_in_transaction_timeout_ms: int = 15_000  # backstop: no request may sit in a transaction for long
    db_pool_size: int = 5
    db_max_overflow: int = 5
    app_base_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]
    trust_proxy_headers: bool = False  # true behind Azure Container Apps ingress (the image sets it)
    frontend_dist: str = ""  # folder with the built frontend (index.html, assets/); empty means API-only
    max_body_bytes: int = 1_000_000  # per request; the billing webhook has its own smaller limit

    # sessions and auth
    cookie_secure: bool = True
    session_days: int = 7
    reset_token_minutes: int = 30
    reset_requests_per_hour: int = Field(default=3, ge=1)  # per email address, so reset links can't bomb an inbox
    invite_days: int = 7
    invites_per_day: int = 50  # per tenant
    max_pending_invites: int = 50  # per tenant
    verify_hours: int = 48
    # Owners must verify their email before inviting people or checking out. Turn off only where no real
    # email leaves the system (local dev, tests, outbox-only demos): no email, no spam risk.
    require_email_verification: bool = True
    # Only the in-memory outbox exists today; a real provider (paid) needs approval. With real email,
    # skipping verification would turn invitations into a spam relay, so the validator refuses that.
    email_provider: Literal["outbox"] = "outbox"
    auth_rate_limit_per_minute: int = Field(default=10, ge=1)
    signups_per_ip_per_day: int = Field(default=20, ge=1)
    # Empty = in-memory limits (one replica). redis:// or rediss:// (TLS) shares them across replicas. Contains a
    # password, so it is a secret and is never logged. If Redis is down the app falls back to in-memory limits.
    rate_limit_redis_url: str = ""
    # Size of the limiter's own thread pool for Redis checks (kept apart from the shared worker threads).
    rate_limit_redis_threads: int = Field(default=8, ge=1)
    # Longest a gate waits for a free pool thread (seconds) before the in-memory check answers it and the breaker trips.
    rate_limit_redis_queue_timeout: float = Field(default=1.0, gt=0, le=30)
    new_trials_per_day: int = 200  # studio-wide, so farmed trials can't exhaust shared budgets

    # AI
    ai_provider: Literal["fake", "azure"] = "fake"
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-5-mini"
    azure_openai_api_key: str = ""  # placeholder; the network secret injects the real key
    azure_openai_api: Literal["auto", "chat", "responses"] = "auto"  # auto: responses if the endpoint ends /openai/v1/responses
    azure_openai_auth: Literal["key", "managed_identity"] = "key"
    azure_client_id: str = ""  # user-assigned identity; empty means the system-assigned one
    # The three timeouts are finite, positive and capped: nan or inf would silently switch the deadline or the guard off.
    ai_timeout_seconds: float = Field(default=20.0, gt=0, le=MAX_TIMEOUT_SECONDS, allow_inf_nan=False)  # per attempt
    # Whole call, retries included; must stay below the frontend's abort (below).
    ai_deadline_seconds: float = Field(default=25.0, gt=0, le=MAX_TIMEOUT_SECONDS, allow_inf_nan=False)
    # How long the browser waits before aborting a request. The backend serves this number at GET /api/config and the
    # SPA reads it once at startup, so this is the single source. The app refuses to start if ai_deadline_seconds +
    # FRONTEND_TIMEOUT_MARGIN_SECONDS exceeds it, because a call the browser has already abandoned is still billed.
    frontend_timeout_seconds: float = Field(default=30.0, gt=0, le=MAX_TIMEOUT_SECONDS, allow_inf_nan=False)
    # Optional reasoning effort for the Responses API: low, medium, high or xhigh (gpt-5.4-pro rejects low); empty means "not sent" (model default).
    # It is unset by default so each deployment uses its own default; medium is the cheapest value gpt-5.4-pro accepts.
    azure_openai_reasoning_effort: str = ""
    ai_retries: int = 1
    # Responses-API reasoning tokens share max_output_tokens with the answer; this many are added to each call's
    # budget (and reserved) so thinking can't use up the answer's room. Chat completions ignore it.
    ai_reasoning_headroom: int = 1500
    ai_rate_limit_per_minute: int = Field(default=20, ge=1)
    # All tenants together, per UTC day. Protects the studio's $80 of Azure credit from farmed free trials.
    ai_global_daily_tokens: int = 98_000  # x 31 x $2.00/M (gpt-5-mini) = $6.08 <= $6.10
    # Blended USD per million tokens of the configured deployment. Unset (empty) means "look the deployment up in the
    # price table in aicost.py"; an unknown deployment then needs this set. Set, it overrides the table. Only checked
    # with AI_PROVIDER=azure: the fake provider costs nothing.
    ai_price_per_million_tokens: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    # The app refuses to start when ai_global_daily_tokens x 31 x the price is above this (aicost.py). 6.10 is the
    # Azure OpenAI line in state/BUDGET.md, inside the studio's $80 credit. Raising it needs Vishal's approval.
    ai_monthly_budget_usd: float = Field(default=DEFAULT_MONTHLY_BUDGET_USD, gt=0, allow_inf_nan=False)
    ai_trial_share: float = 0.5  # all free trials together may use at most this share of the global budget
    ai_concurrent_calls: int = 8  # in-process cap, so slow AI calls can't take every request thread
    ai_calls_per_tenant_at_once: int = 2

    # billing (test mode only until `unlock selling`)
    billing_provider: Literal["mock", "stripe"] = "mock"
    # Unset means a random secret per process, which is right for the mock. Stripe needs its whsec_ value.
    billing_webhook_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(MIN_WEBHOOK_SECRET))
    stripe_secret_key: str = ""
    stripe_api_version: str = ""  # empty uses the account's default version
    # The demo "Pay (test)" button, only with BILLING_PROVIDER=mock. Off unless a demo turns it on: it grants
    # paid plans for free (each mock period lasts 30 days).
    mock_checkout_enabled: bool = False
    trial_days: int = 14

    log_level: str = "INFO"

    @field_validator("ai_price_per_million_tokens", mode="before")
    @classmethod
    def _blank_price_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value  # Bicep passes "" for "use the table"

    @model_validator(mode="after")
    def _safe_settings(self) -> "Settings":
        effort = self.azure_openai_reasoning_effort.strip().lower()
        if effort and effort not in REASONING_EFFORTS:
            raise ValueError(f"AZURE_OPENAI_REASONING_EFFORT must be one of {', '.join(REASONING_EFFORTS)} (or empty to leave it unset)")
        self.azure_openai_reasoning_effort = effort
        if self.ai_deadline_seconds + FRONTEND_TIMEOUT_MARGIN_SECONDS > self.frontend_timeout_seconds:
            raise ValueError(f"AI_DEADLINE_SECONDS ({self.ai_deadline_seconds:g}) must be at least "
                             f"{FRONTEND_TIMEOUT_MARGIN_SECONDS:g} s below FRONTEND_TIMEOUT_SECONDS "
                             f"({self.frontend_timeout_seconds:g}): the browser would give up before the AI call ends. "
                             "Lower the deadline, or raise FRONTEND_TIMEOUT_SECONDS (the browser reads it from /api/config)")
        if len(self.billing_webhook_secret) < MIN_WEBHOOK_SECRET:
            raise ValueError(f"BILLING_WEBHOOK_SECRET must be at least {MIN_WEBHOOK_SECRET} characters "
                             "(leave it unset with mock billing)")
        if self.billing_provider == "stripe" and not self.billing_webhook_secret.startswith("whsec_"):
            raise ValueError("BILLING_WEBHOOK_SECRET must be the Stripe endpoint secret (whsec_...) with BILLING_PROVIDER=stripe")
        if not self.require_email_verification and self.email_provider != "outbox":
            raise ValueError("REQUIRE_EMAIL_VERIFICATION can only be false while no real email is sent")
        if self.ai_provider == "azure":
            try:
                check_ai_budget(self.azure_openai_deployment, self.ai_price_per_million_tokens,
                                self.ai_global_daily_tokens, self.ai_monthly_budget_usd)
            except ValueError as exc:
                raise ValueError(f"AI cost guard: {exc}") from None
        if self.db_auth == "entra":
            validate_entra_url(self.database_url)  # a ValueError subclass; never echoes the URL
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS can't contain '*': with credentials, that would let any site call the API")
        if self.env == "prod":
            base = urlparse(self.app_base_url)
            if base.scheme != "https" or base.hostname in (None, "localhost", "127.0.0.1"):
                raise ValueError("APP_BASE_URL must be the public https address in prod (links in emails use it)")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in prod")
            if not self.trust_proxy_headers:
                raise ValueError("TRUST_PROXY_HEADERS must be true in prod (Container Apps ingress), or rate limits see one IP")
            if self.ai_provider == "azure" and not self.azure_openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT must be set when AI_PROVIDER=azure")
        return self
