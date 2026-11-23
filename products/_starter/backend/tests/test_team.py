from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.models import Invitation

from .conftest import sign_up

MEMBER_PASSWORD = "member passphrase 1"


def _invite(owner_client, outbox, email="member@acme.test"):
    response = owner_client.post("/api/team/invitations", json={"email": email})
    assert response.status_code == 201, response.text
    return response.json(), outbox.sent[-1].body.split("token=")[1].split()[0]


def _accept(client, token, password=MEMBER_PASSWORD):
    return client.post("/api/invitations/accept", json={"token": token, "password": password})


def test_invited_member_joins_the_same_tenant(owner, new_client, outbox):
    owner_client, me = owner
    owner_client.post("/api/notes", json={"title": "Shared note"})
    _, token = _invite(owner_client, outbox, "Member@Acme.test")
    member = new_client()
    joined = _accept(member, token)
    assert joined.status_code == 201
    body = joined.json()
    assert body["user"]["role"] == "member" and body["user"]["email"] == "member@acme.test"
    assert body["tenant"]["id"] == me["tenant"]["id"]
    assert [n["title"] for n in member.get("/api/notes").json()["items"]] == ["Shared note"]
    assert member.post("/api/auth/login", json={"email": "member@acme.test", "password": MEMBER_PASSWORD}).status_code == 200


def test_members_cannot_use_owner_only_actions(owner, new_client, outbox):
    owner_client, _ = owner
    _, token = _invite(owner_client, outbox)
    member = new_client()
    _accept(member, token)
    assert member.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 403
    assert member.get("/api/account/export").status_code == 403
    assert member.request("DELETE", "/api/account", json={"password": MEMBER_PASSWORD, "confirm": "DELETE"}).status_code == 403
    assert member.post("/api/team/invitations", json={"email": "x@acme.test"}).status_code == 403
    team = member.get("/api/team").json()
    assert "invitations" not in team and len(team["members"]) == 2


def test_invitation_links_are_single_use(owner, new_client, outbox):
    owner_client, _ = owner
    _, token = _invite(owner_client, outbox)
    assert _accept(new_client(), token).status_code == 201
    assert _accept(new_client(), token).status_code == 400


def test_expired_and_revoked_invitations_fail(owner, new_client, outbox, database):
    owner_client, _ = owner
    _, expired = _invite(owner_client, outbox, "late@acme.test")
    with database.sessions() as db:
        db.execute(update(Invitation).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    assert _accept(new_client(), expired).status_code == 400
    invitation, revoked = _invite(owner_client, outbox, "nope@acme.test")
    assert owner_client.delete(f"/api/team/invitations/{invitation['id']}").status_code == 204
    assert _accept(new_client(), revoked).status_code == 400


def test_reinviting_replaces_the_older_link(owner, new_client, outbox):
    owner_client, _ = owner
    _, first = _invite(owner_client, outbox)
    _, second = _invite(owner_client, outbox)
    assert _accept(new_client(), first).status_code == 400
    assert _accept(new_client(), second).status_code == 201
    assert len(owner_client.get("/api/team").json()["invitations"]) == 0


def test_cannot_invite_an_existing_account(owner, new_client, outbox):
    owner_client, _ = owner
    sign_up(new_client(), email="taken@beta.test", company="Beta")
    response = owner_client.post("/api/team/invitations", json={"email": "taken@beta.test"})
    assert response.status_code == 409 and outbox.sent == []


def test_email_registered_after_invite_cannot_accept(owner, new_client, outbox):
    owner_client, _ = owner
    _, token = _invite(owner_client, outbox, "race@acme.test")
    sign_up(new_client(), email="race@acme.test", company="Elsewhere")
    assert _accept(new_client(), token).status_code == 409


def test_other_tenants_cannot_touch_my_invitations_or_members(owner, new_client, outbox):
    owner_client, _ = owner
    invitation, token = _invite(owner_client, outbox)
    member = new_client()
    member_id = _accept(member, token).json()["user"]["id"]
    other = new_client()
    sign_up(other, email="boss@beta.test", company="Beta")
    assert other.delete(f"/api/team/invitations/{invitation['id']}").status_code == 404
    assert other.delete(f"/api/team/members/{member_id}").status_code == 404
    assert [m["email"] for m in other.get("/api/team").json()["members"]] == ["boss@beta.test"]


def test_removing_a_member_signs_them_out(owner, new_client, outbox):
    owner_client, me = owner
    _, token = _invite(owner_client, outbox)
    member = new_client()
    member_id = _accept(member, token).json()["user"]["id"]
    assert owner_client.delete(f"/api/team/members/{me['user']['id']}").status_code == 422
    assert owner_client.delete(f"/api/team/members/{member_id}").status_code == 204
    assert member.get("/api/auth/me").status_code == 401


def test_invite_email_link_and_weak_password(owner, new_client, outbox, settings):
    owner_client, _ = owner
    _, token = _invite(owner_client, outbox)
    message = outbox.sent[-1]
    assert message.to == "member@acme.test" and "Acme Ltd" in message.subject
    assert f"{settings.app_base_url}/accept-invite?token=" in message.body
    weak = _accept(new_client(), token, password="short")
    assert weak.status_code == 422 and weak.json()["error"] == "weak_password"
