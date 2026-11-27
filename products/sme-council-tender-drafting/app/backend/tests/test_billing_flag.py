"""Prices off (T-185): with billing_enabled false (the tender app's default) no billing route exists."""
import pytest
from fastapi.testclient import TestClient

from app.billing import MockBilling
from app.config import Settings
from app.main import create_app

from .conftest import sign_up


def test_default_is_off():
    assert Settings(env="test", database_url="postgresql+psycopg://x:y@h/d").billing_enabled is False


@pytest.fixture
def off_client(settings, ai, outbox):
    off = settings.model_copy(update={"billing_enabled": False})
    application = create_app(off, ai=ai, email=outbox, billing_provider=MockBilling(off.billing_webhook_secret, off.app_base_url))
    with TestClient(application, base_url="https://testserver", headers={"X-Requested-With": "test"}) as client:
        yield client
    application.state.db.dispose()


@pytest.mark.parametrize("method,path", [("GET", "/api/billing/plans"), ("POST", "/api/billing/checkout"),
                                        ("POST", "/api/billing/portal"), ("POST", "/api/billing/webhook"),
                                        ("POST", "/api/billing/mock/complete/x")])
def test_billing_routes_are_not_mounted(off_client, method, path):
    sign_up(off_client)
    assert off_client.request(method, path).status_code == 404


def test_config_reports_billing_off_and_the_trial_still_works(off_client):
    assert off_client.get("/api/config").json()["billing_enabled"] is False
    sign_up(off_client)
    me = off_client.get("/api/auth/me").json()
    assert me["subscription"]["status"] == "trialing"


def test_config_reports_billing_on_when_enabled(new_client):
    assert new_client().get("/api/config").json()["billing_enabled"] is True  # the shared test settings turn it on
