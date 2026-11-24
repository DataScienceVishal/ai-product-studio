"""Settings come only from environment variables (or a local, gitignored .env)."""
from __future__ import annotations

import secrets
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .dbauth import validate_entra_url

MIN_WEBHOOK_SECRET = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "starter"
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
    ai_timeout_seconds: float = 20.0  # per attempt
    ai_deadline_seconds: float = 25.0  # whole call, retries included; below the frontend's 30 s abort
    ai_retries: int = 1
    # Responses-API reasoning tokens share max_output_tokens with the answer; this many are added to each call's
    # budget (and reserved) so thinking can't use up the answer's room. Chat completions ignore it.
    ai_reasoning_headroom: int = 1500
    ai_rate_limit_per_minute: int = Field(default=20, ge=1)
    # All tenants together, per UTC day. Protects the studio's $80 of Azure credit from farmed free trials.
    ai_global_daily_tokens: int = 100_000
    # Blended price in USD per million tokens (input and output together) of the configured deployment. The default
    # is the gpt-5-mini assumption. A bigger model needs a much smaller ai_global_daily_tokens (README).
    ai_price_per_million_tokens: float = 2.00
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

    @model_validator(mode="after")
    def _safe_settings(self) -> "Settings":
        if len(self.billing_webhook_secret) < MIN_WEBHOOK_SECRET:
            raise ValueError(f"BILLING_WEBHOOK_SECRET must be at least {MIN_WEBHOOK_SECRET} characters "
                             "(leave it unset with mock billing)")
        if self.billing_provider == "stripe" and not self.billing_webhook_secret.startswith("whsec_"):
            raise ValueError("BILLING_WEBHOOK_SECRET must be the Stripe endpoint secret (whsec_...) with BILLING_PROVIDER=stripe")
        if not self.require_email_verification and self.email_provider != "outbox":
            raise ValueError("REQUIRE_EMAIL_VERIFICATION can only be false while no real email is sent")
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
