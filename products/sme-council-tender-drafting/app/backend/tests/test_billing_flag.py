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


@pytest.fixture
def off_vehicle_client(settings, ai, outbox):
    from . import vehicle
    off = settings.model_copy(update={"billing_enabled": False})
    application = create_app(off, ai=ai, email=outbox, extra_routers=(vehicle.router,),
                             billing_provider=MockBilling(off.billing_webhook_secret, off.app_base_url))
    with TestClient(application, base_url="https://testserver", headers={"X-Requested-With": "test"}) as client:
        yield client
    application.state.db.dispose()


def test_trial_does_not_lapse_with_billing_off_but_ai_caps_still_apply(off_vehicle_client, database, outbox):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select, update

    from app.models import AIUsage, Subscription, Tenant
    from .conftest import verify_email
    client = off_vehicle_client
    sign_up(client)
    verify_email(client, outbox)
    item = client.post("/api/vehicle", json={"title": "T", "body": "text"}).json()
    with database.sessions() as db:  # the 14-day trial ran out long ago
        db.execute(update(Subscription).values(trial_ends_at=datetime.now(timezone.utc) - timedelta(days=30)))
        db.commit()
    assert client.post(f"/api/vehicle/{item['id']}/summarize").status_code == 200  # no "Choose a plan" refusal
    with database.sessions() as db:  # the daily AI cap still applies
        tenant = db.scalar(select(Tenant))
        db.add(AIUsage(tenant_id=tenant.id, feature="x", model="fake", input_tokens=29_500, output_tokens=0))
        db.commit()
    response = client.post(f"/api/vehicle/{item['id']}/summarize")
    assert response.status_code == 429 and response.json()["error"] == "ai_daily_cap_reached"


def test_has_access_ignores_the_trial_end_only_when_billing_is_off():
    from datetime import datetime, timedelta, timezone

    from app.billing import has_access
    past = datetime.now(timezone.utc) - timedelta(days=1)
    assert not has_access("trialing", past)
    assert has_access("trialing", past, billing_enabled=False)
    assert not has_access("canceled", past, billing_enabled=False)
