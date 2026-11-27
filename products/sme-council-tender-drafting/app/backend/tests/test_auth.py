from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import AuthSession, PasswordReset, Subscription, User
from app.security import token_hash

from .conftest import PASSWORD, link_token, sign_up


def test_signup_creates_owner_tenant_and_trial(new_client, database):
    client = new_client()
    me = sign_up(client, email="New.Owner@Acme.TEST")
    assert me["user"]["email"] == "new.owner@acme.test"
    assert me["user"]["role"] == "owner"
    assert me["tenant"]["name"] == "Acme Ltd"
    assert me["subscription"]["status"] == "trialing"
    with database.sessions() as db:
        sub = db.scalar(select(Subscription))
        assert timedelta(days=13) < sub.trial_ends_at - datetime.now(timezone.utc) <= timedelta(days=14)


def test_session_cookie_is_httponly_secure_lax(new_client):
    client = new_client()
    response = client.post("/api/auth/signup", json={"company_name": "A", "email": "a@a.test", "password": PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie


def test_only_hashes_are_stored(owner, database):
    client, _ = owner
    token = client.cookies.get("__Host-session")
    with database.sessions() as db:
        row = db.scalar(select(AuthSession))
        user = db.scalar(select(User))
    assert row.token_hash == token_hash(token) and row.token_hash != token
    assert user.password_hash.startswith("$argon2id$")


def test_me_requires_sign_in(new_client):
    response = new_client().get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"
    assert response.json()["request_id"]


def test_duplicate_email_is_rejected_case_insensitively(new_client):
    sign_up(new_client(), email="dup@acme.test")
    response = new_client().post("/api/auth/signup",
                                 json={"company_name": "B", "email": "DUP@acme.test", "password": PASSWORD})
    assert response.status_code == 409
    assert response.json()["error"] == "email_taken"


def test_weak_password_and_bad_email(new_client):
    client = new_client()
    weak = client.post("/api/auth/signup", json={"company_name": "A", "email": "a@a.test", "password": "short"})
    assert weak.status_code == 422 and weak.json()["error"] == "weak_password"
    bad = client.post("/api/auth/signup", json={"company_name": "A", "email": "not-an-email", "password": PASSWORD})
    assert bad.status_code == 422 and bad.json()["error"] == "invalid_input"


def test_login_failures_look_the_same(owner, new_client):
    client = new_client()
    wrong = client.post("/api/auth/login", json={"email": "owner@acme.test", "password": "wrong password!"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@acme.test", "password": "wrong password!"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["message"] == unknown.json()["message"]


def test_login_then_logout_revokes_the_session(owner, new_client):
    client = new_client()
    assert client.post("/api/auth/login", json={"email": "OWNER@acme.test", "password": PASSWORD}).status_code == 200
    token = client.cookies.get("__Host-session")
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    replay = new_client()
    replay.cookies.set("__Host-session", token, domain="testserver")
    assert replay.get("/api/auth/me").status_code == 401


def test_expired_session_is_rejected(owner, database):
    client, _ = owner
    with database.sessions() as db:
        db.execute(update(AuthSession).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_writes_without_csrf_header_are_refused(new_client):
    client = new_client(csrf=False)
    response = client.post("/api/auth/signup", json={"company_name": "A", "email": "a@a.test", "password": PASSWORD})
    assert response.status_code == 403
    assert response.json()["error"] == "csrf_check_failed"


def test_password_reset_flow(owner, new_client, outbox):
    old_client, _ = owner
    client = new_client()
    assert client.post("/api/auth/password-reset/request", json={"email": "owner@acme.test"}).status_code == 202
    resets = [m for m in outbox.sent if "/reset-password?token=" in m.body]
    assert len(resets) == 1 and resets[0].to == "owner@acme.test"
    token = link_token(outbox, "reset-password")
    new_password = "a brand new passphrase"
    assert client.post("/api/auth/password-reset/confirm",
                       json={"token": token, "new_password": new_password}).status_code == 204
    assert old_client.get("/api/auth/me").status_code == 401  # signed out everywhere
    assert client.post("/api/auth/login", json={"email": "owner@acme.test", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "owner@acme.test", "password": new_password}).status_code == 200
    again = client.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "another passphrase"})
    assert again.status_code == 400  # single use


def test_reset_for_unknown_email_looks_the_same_and_sends_nothing(new_client, outbox):
    before = len(outbox.sent)
    response = new_client().post("/api/auth/password-reset/request", json={"email": "ghost@acme.test"})
    assert response.status_code == 202
    assert len(outbox.sent) == before


def test_newer_reset_link_replaces_older_one(owner, new_client, outbox):
    client = new_client()
    client.post("/api/auth/password-reset/request", json={"email": "owner@acme.test"})
    client.post("/api/auth/password-reset/request", json={"email": "owner@acme.test"})
    first = [m for m in outbox.sent if "/reset-password?token=" in m.body][0].body.split("token=")[1].split()[0]
    response = client.post("/api/auth/password-reset/confirm", json={"token": first, "new_password": "a brand new passphrase"})
    assert response.status_code == 400


def test_expired_reset_link_is_refused(owner, new_client, outbox, database):
    client = new_client()
    client.post("/api/auth/password-reset/request", json={"email": "owner@acme.test"})
    token = link_token(outbox, "reset-password")
    with database.sessions() as db:
        db.execute(update(PasswordReset).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    response = client.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "a brand new passphrase"})
    assert response.status_code == 400


def test_login_is_rate_limited(app, owner, new_client):
    app.state.settings.auth_rate_limit_per_minute = 3
    client = new_client()
    codes = [client.post("/api/auth/login", json={"email": "owner@acme.test", "password": "wrong password!"}).status_code
             for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    limited = client.post("/api/auth/login", json={"email": "owner@acme.test", "password": PASSWORD})
    assert limited.status_code == 429 and int(limited.headers["retry-after"]) >= 1
