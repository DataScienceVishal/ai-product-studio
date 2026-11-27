from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.models import EmailVerification

from .conftest import link_token, sign_up, verify_email


def test_signup_sends_a_link_and_verifying_flips_the_flag(new_client, outbox):
    client = new_client()
    me = sign_up(client)
    assert me["user"]["email_verified"] is False
    assert outbox.sent[-1].to == "owner@acme.test" and "/verify-email?token=" in outbox.sent[-1].body
    verify_email(client, outbox)
    assert client.get("/api/auth/me").json()["user"]["email_verified"] is True


def test_verification_needs_the_right_signed_in_account_and_is_single_use(new_client, outbox):
    owner = new_client()
    sign_up(owner)
    token = link_token(outbox, "verify-email")
    assert new_client().post("/api/auth/verify-email", json={"token": token}).status_code == 401  # signed out
    someone_else = new_client()
    sign_up(someone_else, email="other@beta.test", company="Beta")
    assert someone_else.post("/api/auth/verify-email", json={"token": token}).status_code == 400  # wrong account
    assert owner.post("/api/auth/verify-email", json={"token": token}).status_code == 204
    assert owner.post("/api/auth/verify-email", json={"token": token}).status_code == 400  # used


def test_expired_link_fails(new_client, outbox, database):
    client = new_client()
    sign_up(client)
    token = link_token(outbox, "verify-email")
    with database.sessions() as db:
        db.execute(update(EmailVerification).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 400


def test_resend_replaces_the_old_link_and_is_rate_limited(new_client, outbox):
    client = new_client()
    sign_up(client)
    first = link_token(outbox, "verify-email")
    assert client.post("/api/auth/verify-email/resend").status_code == 202
    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 400
    codes = [client.post("/api/auth/verify-email/resend").status_code for _ in range(3)]
    assert codes == [202, 202, 429]


def test_unverified_owner_cannot_invite_or_check_out(new_client, outbox):
    client = new_client()
    sign_up(client)
    for path, body in (("/api/team/invitations", {"email": "x@acme.test"}), ("/api/billing/checkout", {"plan": "pro"})):
        response = client.post(path, json=body)
        assert response.status_code == 403 and response.json()["error"] == "email_not_verified"
    assert not any("/accept-invite?token=" in m.body for m in outbox.sent)
    assert client.post("/api/vehicle", json={"title": "still usable"}).status_code == 201  # the product itself works


def test_unverified_owner_cannot_open_the_billing_portal(new_client, outbox, app, database):
    from sqlalchemy import update as sql_update
    from app.models import Subscription
    client = new_client()
    sign_up(client)
    with database.sessions() as db:  # a customer exists, so only the verification gate can refuse
        db.execute(sql_update(Subscription).values(provider="mock", provider_customer="cus_1"))
        db.commit()
    response = client.post("/api/billing/portal")
    assert response.status_code == 403 and response.json()["error"] == "email_not_verified"
    verify_email(client, outbox)
    assert client.post("/api/billing/portal").status_code == 200


def test_accepting_an_invite_and_resetting_a_password_verify_the_email(owner, new_client, outbox):
    owner_client, _ = owner
    owner_client.post("/api/team/invitations", json={"email": "crew@acme.test"})
    member = new_client()
    joined = member.post("/api/invitations/accept", json={"token": link_token(outbox, "accept-invite"),
                                                          "password": "member passphrase 1"}).json()
    assert joined["user"]["email_verified"] is True

    other = new_client()
    sign_up(other, email="forgetful@beta.test", company="Beta")
    other.post("/api/auth/password-reset/request", json={"email": "forgetful@beta.test"})
    other.post("/api/auth/password-reset/confirm", json={"token": link_token(outbox, "reset-password"),
                                                         "new_password": "a brand new passphrase"})
    other.post("/api/auth/login", json={"email": "forgetful@beta.test", "password": "a brand new passphrase"})
    assert other.get("/api/auth/me").json()["user"]["email_verified"] is True


def test_resend_when_already_verified(owner):
    client, _ = owner
    response = client.post("/api/auth/verify-email/resend")
    assert response.status_code == 202 and "already verified" in response.json()["status"]


def test_gate_can_be_switched_off_where_no_real_email_is_sent(app, new_client):
    app.state.settings.require_email_verification = False
    client = new_client()
    sign_up(client)
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 200



def test_me_exposes_the_verification_gate(app, new_client):
    client = new_client()
    sign_up(client)
    assert client.get("/api/auth/me").json()["user"]["email_verification_required"] is True
    app.state.settings.require_email_verification = False
    assert client.get("/api/auth/me").json()["user"]["email_verification_required"] is False
