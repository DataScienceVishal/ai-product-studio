"""Session cookie clears carry the same attributes as the cookie that was set, and the selling lock lists agree."""
from __future__ import annotations

from typing import get_args

import pytest
from fastapi.testclient import TestClient

from app.billing import MockBilling, StripeBilling
from app.config import Settings
from app.main import create_app

from .conftest import PASSWORD, link_token, sign_up, verify_email

MEMBER_PASSWORD = "member passphrase 1"


def _session_cookies(response) -> list[str]:
    return [h for h in response.headers.get_list("set-cookie") if h.lower().lstrip().startswith(("__host-session=", "session="))]


def _attrs(header: str) -> set[str]:
    return {part.strip().lower() for part in header.split(";")[1:]}


def _assert_clear_matches_set(set_header: str, clear_header: str, name: str):
    assert set_header.startswith(f"{name}=") and clear_header.startswith(f"{name}=")
    assert clear_header.startswith(f'{name}=""') or clear_header.startswith(f"{name}=;")  # emptied
    clear = _attrs(clear_header)
    assert "path=/" in clear and "max-age=0" in clear
    for attr in ("secure", "httponly", "samesite=lax", "path=/"):
        assert (attr in _attrs(set_header)) == (attr in clear), f"{attr} differs between set and clear"
    assert not any(a.startswith("domain") for a in clear)  # __Host- forbids Domain


@pytest.fixture(params=[True, False], ids=["secure", "plain-http-dev"])
def cookie_world(request, settings, ai, outbox):
    """An app plus a way to make clients, with cookie_secure on and off."""
    secure = request.param
    cfg = settings.model_copy(update={"cookie_secure": secure})
    application = create_app(cfg, ai=ai, email=outbox, billing_provider=MockBilling(cfg.billing_webhook_secret, cfg.app_base_url))
    clients = []

    def make():
        client = TestClient(application, base_url="https://testserver" if secure else "http://testserver",
                            headers={"X-Requested-With": "test"})
        clients.append(client)
        return client

    yield secure, ("__Host-session" if secure else "session"), make, outbox
    for client in clients:
        client.close()
    application.state.db.dispose()


def _signup(make, email="owner@acme.test"):
    client = make()
    response = client.post("/api/auth/signup", json={"company_name": "Acme", "email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return client, response


def test_logout_clear_matches_how_the_cookie_was_set(cookie_world):
    secure, name, make, _ = cookie_world
    client, signup = _signup(make)
    (set_header,) = _session_cookies(signup)
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    (clear_header,) = _session_cookies(response)
    _assert_clear_matches_set(set_header, clear_header, name)
    assert ("secure" in _attrs(clear_header)) is secure


def test_account_deletion_clear_matches_how_the_cookie_was_set(cookie_world):
    secure, name, make, outbox = cookie_world
    client, signup = _signup(make)
    (set_header,) = _session_cookies(signup)
    response = client.request("DELETE", "/api/account", json={"password": PASSWORD, "confirm": "DELETE"})
    assert response.status_code == 204, response.text
    (clear_header,) = _session_cookies(response)
    _assert_clear_matches_set(set_header, clear_header, name)
    assert ("secure" in _attrs(clear_header)) is secure


def test_member_leaving_clear_matches_how_the_cookie_was_set(cookie_world):
    secure, name, make, outbox = cookie_world
    owner, _ = _signup(make)
    verify_email(owner, outbox)
    assert owner.post("/api/team/invitations", json={"email": "member@acme.test"}).status_code == 201
    member = make()
    accepted = member.post("/api/invitations/accept", json={"token": link_token(outbox, "accept-invite"), "password": MEMBER_PASSWORD})
    assert accepted.status_code in (200, 201), accepted.text
    (set_header,) = _session_cookies(accepted)
    response = member.request("DELETE", "/api/account/me", json={"password": MEMBER_PASSWORD, "confirm": "DELETE"})
    assert response.status_code == 204, response.text
    (clear_header,) = _session_cookies(response)
    _assert_clear_matches_set(set_header, clear_header, name)


# --- the selling lock: LIMITED_PROVIDERS and the live-key refusal must agree ---------------------------

def _refuses_live_keys(provider: str) -> bool:
    """True if constructing that billing provider with a live key is refused."""
    builders = {"mock": lambda: MockBilling("s" * 40, "https://app.test"),  # takes no API key: nothing to refuse
                "stripe": lambda: StripeBilling("sk_live_abc", "whsec_" + "x" * 40)}
    assert set(builders) == set(get_args(Settings.model_fields["billing_provider"].annotation)), (
        "A billing provider was added to Settings.billing_provider: add it here and decide whether it is in "
        "LIMITED_PROVIDERS (every provider that refuses live keys must be)")
    try:
        builders[provider]()
    except ValueError:
        return True
    return False


def test_every_provider_that_refuses_live_keys_is_trial_limited_and_back():
    from app.routes.notes import LIMITED_PROVIDERS
    providers = set(get_args(Settings.model_fields["billing_provider"].annotation))
    refusing = {p for p in providers if _refuses_live_keys(p)}
    assert refusing == {"stripe"}  # today only Stripe takes keys, and it is test-mode only
    assert refusing <= LIMITED_PROVIDERS, "a provider that refuses live keys must be in LIMITED_PROVIDERS"
    assert LIMITED_PROVIDERS <= providers, "LIMITED_PROVIDERS names a provider that does not exist"
    # stripe leaves LIMITED_PROVIDERS only in the same change that stops refusing live keys
    assert ("stripe" in LIMITED_PROVIDERS) == _refuses_live_keys("stripe")
