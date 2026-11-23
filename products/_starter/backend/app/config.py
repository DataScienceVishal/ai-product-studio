"""Settings come only from environment variables (or a local, gitignored .env)."""
from __future__ import annotations

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_WEBHOOK_SECRET = "dev-only-mock-webhook-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "starter"
    database_url: str = "postgresql+psycopg://studio:studio@localhost:5432/starter_dev"
    db_statement_timeout_ms: int = 10_000
    app_base_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]
    trust_proxy_headers: bool = False  # true behind Azure Container Apps ingress

    # sessions and auth
    cookie_secure: bool = True
    session_days: int = 7
    reset_token_minutes: int = 30
    invite_days: int = 7
    verify_hours: int = 48
    # Owners must verify their email before inviting people or checking out. Turn off only where no real
    # email leaves the system (local dev, tests, outbox-only demos): no email, no spam risk.
    require_email_verification: bool = True
    auth_rate_limit_per_minute: int = 10

    # AI
    ai_provider: Literal["fake", "azure"] = "fake"
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-5-mini"
    azure_openai_api_key: str = ""  # placeholder; the network secret injects the real key
    ai_timeout_seconds: float = 30.0
    ai_rate_limit_per_minute: int = 20

    # billing (test mode only until `unlock selling`)
    billing_provider: Literal["mock", "stripe"] = "mock"
    billing_webhook_secret: str = DEV_WEBHOOK_SECRET
    stripe_secret_key: str = ""
    trial_days: int = 14

    log_level: str = "INFO"

    @model_validator(mode="after")
    def _safe_for_prod(self) -> "Settings":
        if self.env == "prod":
            if self.billing_webhook_secret == DEV_WEBHOOK_SECRET:
                raise ValueError("BILLING_WEBHOOK_SECRET must be set in prod")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in prod")
            if self.ai_provider == "azure" and not self.azure_openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT must be set when AI_PROVIDER=azure")
        return self
