from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import Invitation, User
from app.security import token_hash

from .conftest import PASSWORD, link_token, sign_up

MEMBER_PASSWORD = "member passphrase 1"


def _invite(owner_client, outbox, email="member@acme.test"):
    response = owner_client.post("/api/team/invitations", json={"email": email})
    assert response.status_code == 201, response.text
    return response.json(), link_token(outbox, "accept-invite")


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
    assert response.status_code == 409
    assert not any("/accept-invite?token=" in m.body for m in outbox.sent)


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
    message = [m for m in outbox.sent if "/accept-invite?token=" in m.body][-1]
    assert message.to == "member@acme.test" and "Acme Ltd" in message.subject
    assert f"{settings.app_base_url}/accept-invite?token=" in message.body
    weak = _accept(new_client(), token, password="short")
    assert weak.status_code == 422 and weak.json()["error"] == "weak_password"


# --- T-72 triage of T-70 suspicion: a signed-in user accepting another tenant's invitation ---

def test_signed_in_user_accepting_an_invite_does_not_orphan_their_own_tenant(owner, new_client, outbox):
    """NOT a bug. Accept always creates a NEW user for the invited email; the signed-in user is never moved,
    and an invite for an email that already has an account is refused (409), so no tenant loses its owner."""
    owner_a, _ = owner
    b = new_client()
    sign_up(b, email="b@beta.test", company="Beta")
    b.post("/api/notes", json={"title": "Beta note"})
    _, token = _invite(owner_a, outbox, "other@acme.test")
    joined = _accept(b, token)  # B is signed in on this client while accepting someone else's invite
    assert joined.status_code == 201 and joined.json()["user"]["email"] == "other@acme.test"
    # B's own account and tenant are untouched and still reachable by B's credentials
    again = new_client()
    login = again.post("/api/auth/login", json={"email": "b@beta.test", "password": PASSWORD})
    assert login.status_code == 200, login.text
    assert login.json()["tenant"]["name"] == "Beta" and login.json()["user"]["role"] == "owner"
    assert [n["title"] for n in again.get("/api/notes").json()["items"]] == ["Beta note"]


def test_invite_for_an_email_that_already_has_an_account_is_refused(owner, new_client):
    owner_a, _ = owner
    sign_up(new_client(), email="b@beta.test", company="Beta")
    assert owner_a.post("/api/team/invitations", json={"email": "b@beta.test"}).status_code == 409


# --- T-172 B6: resending an invite ---

def test_resend_at_the_pending_cap_replaces_the_old_invite(app, owner, new_client, outbox):
    owner_client, _ = owner
    app.state.settings.max_pending_invites = 2
    _, first = _invite(owner_client, outbox, "a@acme.test")
    _invite(owner_client, outbox, "b@acme.test")
    assert owner_client.post("/api/team/invitations", json={"email": "c@acme.test"}).status_code == 409
    _, again = _invite(owner_client, outbox, "A@acme.test")  # resend, at the cap
    assert _accept(new_client(), first).status_code == 400  # old link is dead
    assert len(owner_client.get("/api/team").json()["invitations"]) == 2
    assert _accept(new_client(), again).status_code == 201


def test_daily_invite_quota_counts_resends(app, owner, outbox):
    owner_client, _ = owner
    app.state.settings.invites_per_day = 3
    for _ in range(3):
        _invite(owner_client, outbox, "same@acme.test")  # each resend revokes the previous row
    assert owner_client.post("/api/team/invitations", json={"email": "same@acme.test"}).status_code == 429


def test_resend_exemption_is_tenant_scoped(app, owner, new_client, outbox):
    from .conftest import verify_email
    owner_client, _ = owner
    other = new_client()
    sign_up(other, email="boss@beta.test", company="Beta")
    verify_email(other, outbox)
    _, token_b = _invite(other, outbox, "x@x.test")  # tenant B's pending invite
    app.state.settings.max_pending_invites = 1
    _invite(owner_client, outbox, "fill@acme.test")  # tenant A is at its cap
    response = owner_client.post("/api/team/invitations", json={"email": "x@x.test"})
    assert response.status_code == 409 and response.json()["error"] == "too_many_pending"
    assert _accept(new_client(), token_b).status_code == 201  # B's invite is untouched


# --- T-172 B7: accepting revokes other tenants' pending invites for the address ---

def test_accepting_revokes_other_tenants_pending_invites_for_that_email(owner, new_client, outbox, database):
    from .conftest import verify_email
    owner_client, _ = owner
    other = new_client()
    sign_up(other, email="boss@beta.test", company="Beta")
    verify_email(other, outbox)
    _, token_a = _invite(owner_client, outbox, "m@x.test")
    assert other.post("/api/team/invitations", json={"email": "M@x.test"}).status_code == 201
    token_b = link_token(outbox, "accept-invite")
    old = datetime(2026, 1, 2, tzinfo=timezone.utc)
    with database.sessions() as db:  # a revoked and an expired invite for the same address in tenant B: audit rows
        tenant_b = db.scalar(select(Invitation.tenant_id).where(Invitation.token_hash == token_hash(token_b)))
        for name, kw in (("rev", {"revoked_at": old, "expires_at": old + timedelta(days=99999)}),
                         ("exp", {"expires_at": old})):
            db.add(Invitation(tenant_id=tenant_b, email="m@x.test", token_hash=token_hash(name * 20), **kw))
        db.commit()
    assert _accept(new_client(), token_a).status_code == 201
    assert other.get("/api/team").json()["invitations"] == []
    assert _accept(new_client(), token_b).status_code == 400
    with database.sessions() as db:  # the B7 UPDATE touches pending rows only: audit timestamps are untouched
        rows = {i.token_hash: i for i in db.scalars(select(Invitation).where(Invitation.tenant_id == tenant_b))}
        assert rows[token_hash("rev" * 20)].revoked_at == old
        assert rows[token_hash("exp" * 20)].revoked_at is None


# --- T-173: races (real Postgres; deterministic, driven by a row lock held in a second connection) ---

import threading  # noqa: E402
import time  # noqa: E402

from sqlalchemy import text  # noqa: E402


def _in_thread(fn):
    box = {}

    def run():
        try:
            box["r"] = fn()
        except Exception as exc:  # noqa: BLE001 - surfaced by the test's own assertions
            box["error"] = exc

    thread = threading.Thread(target=run)
    thread.start()
    return thread, box


def _wait_for_lock_waiters(app, count, timeout=8.0):
    """Poll until `count` backends of this database wait on a lock; False on timeout (no fixed sleeps).
    Stay under the 15 s idle-in-transaction timeout that would kill the side connection the callers hold."""
    deadline = time.monotonic() + timeout
    with app.state.db.engine.connect() as conn:
        while time.monotonic() < deadline:
            waiting = conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock' "
                                        "AND datname = current_database()")).scalar()
            conn.rollback()
            if waiting >= count:
                return True
            time.sleep(0.02)
    return False


def test_invites_for_one_tenant_are_serialised(app, owner, outbox):
    """A second invite must wait while another invite holds the tenant row lock, so concurrent resends of one
    address cannot both pass the checks. The lock is NO KEY UPDATE: the FK insert only takes KEY SHARE, which would not block."""
    owner_client, me = owner
    with app.state.db.engine.connect() as side:
        side.execute(text("SELECT id FROM tenants WHERE id = :t FOR NO KEY UPDATE"), {"t": me["tenant"]["id"]})
        thread, box = _in_thread(lambda: owner_client.post("/api/team/invitations", json={"email": "r@acme.test"}))
        blocked = _wait_for_lock_waiters(app, 1)
        side.rollback()
    thread.join(10)
    assert blocked, "invite did not wait for the tenant lock"
    assert box["r"].status_code == 201


def test_concurrent_resends_leave_one_live_link(app, owner, outbox, new_client):
    """Two resends of one address start while the tenant lock is held elsewhere. With the lock both queue up
    (two lock waiters) and run one after the other; without it they never wait and this test fails."""
    owner_client, me = owner
    _invite(owner_client, outbox, "dup@acme.test")
    other = new_client()
    other.cookies.update(owner_client.cookies)
    with app.state.db.engine.connect() as side:
        side.execute(text("SELECT id FROM tenants WHERE id = :t FOR NO KEY UPDATE"), {"t": me["tenant"]["id"]})
        threads = [_in_thread(lambda c=c: c.post("/api/team/invitations", json={"email": "dup@acme.test"}))
                   for c in (owner_client, other)]
        both_waiting = _wait_for_lock_waiters(app, 2)
        side.rollback()
    for thread, _ in threads:
        thread.join(15)
    assert both_waiting, "the resends did not both queue behind the tenant lock"
    assert [box["r"].status_code for _, box in threads] == [201, 201]
    with app.state.db.engine.connect() as conn:
        live = conn.execute(text("SELECT count(*) FROM invitations WHERE email = 'dup@acme.test' "
                                 "AND revoked_at IS NULL AND accepted_at IS NULL")).scalar()
    assert live == 1


def test_accept_waits_for_a_concurrent_revoke_and_then_fails(app, owner, new_client, outbox):
    """A link revoked (or replaced) while an accept is in flight must not create an account."""
    owner_client, _ = owner
    invite, token = _invite(owner_client, outbox, "late@acme.test")
    joiner = new_client()
    with app.state.db.engine.connect() as side:
        side.execute(text("SELECT id FROM invitations WHERE id = :i FOR UPDATE"), {"i": invite["id"]})
        thread, box = _in_thread(lambda: _accept(joiner, token))
        waiting = _wait_for_lock_waiters(app, 1)
        side.execute(text("UPDATE invitations SET revoked_at = now() WHERE id = :i"), {"i": invite["id"]})
        side.commit()
    thread.join(15)
    assert waiting, "accept did not wait for the invitation lock"
    assert box["r"].status_code == 400
    with app.state.db.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users WHERE email = 'late@acme.test'")).scalar() == 0


def _hold_email_slot(side, tenant_id, email):
    """An uncommitted user row: anything inserting the same email waits on the unique index until we end."""
    side.execute(text("INSERT INTO users (id, tenant_id, email, password_hash, role, created_at) "
                      "VALUES (gen_random_uuid(), :t, :e, 'x', 'member', now())"), {"t": tenant_id, "e": email})


def test_tenant_lock_is_no_key_update_so_a_resend_does_not_deadlock_with_an_accept(app, owner, new_client, outbox):
    """Guards key_share=True on the tenant lock. An accept holds the invitation row and waits for the email slot;
    a resend of that address takes the tenant lock and waits for the invitation row. When the accept goes on it
    needs a KEY SHARE lock on the tenant for the user's foreign key: a plain FOR UPDATE would deadlock (40P01, 500)."""
    owner_client, me = owner
    _, token = _invite(owner_client, outbox, "p1@acme.test")
    joiner = new_client()
    with app.state.db.engine.connect() as side:
        _hold_email_slot(side, me["tenant"]["id"], "p1@acme.test")
        accepting = _in_thread(lambda: _accept(joiner, token))
        assert _wait_for_lock_waiters(app, 1), "accept did not reach the email slot"
        resending = _in_thread(lambda: owner_client.post("/api/team/invitations", json={"email": "p1@acme.test"}))
        assert _wait_for_lock_waiters(app, 2), "the resend did not queue behind the accept"
        side.rollback()
    for thread, _ in (accepting, resending):
        thread.join(20)
    assert "error" not in accepting[1] and "error" not in resending[1]
    assert accepting[1]["r"].status_code == 201
    assert resending[1]["r"].status_code == 201


def test_cross_tenant_double_accept_answers_409_not_500(owner, new_client, outbox, app):
    """One person accepts links from two tenants at the same moment: Postgres can abort one transaction with a
    deadlock (40P01). That must read as 'email taken' (409), never a 500."""
    from .conftest import verify_email
    owner_client, me = owner
    other = new_client()
    sign_up(other, email="boss@beta.test", company="Beta")
    verify_email(other, outbox)
    _, token_a = _invite(owner_client, outbox, "dbl@x.test")
    assert other.post("/api/team/invitations", json={"email": "dbl@x.test"}).status_code == 201
    token_b = link_token(outbox, "accept-invite")
    joiners = [new_client(), new_client()]
    with app.state.db.engine.connect() as side:
        _hold_email_slot(side, me["tenant"]["id"], "dbl@x.test")
        runs = [_in_thread(lambda c=c, t=t: _accept(c, t)) for c, t in zip(joiners, (token_a, token_b))]
        assert _wait_for_lock_waiters(app, 2), "both accepts should wait for the email slot"
        side.rollback()
    for thread, _ in runs:
        thread.join(20)
    assert all("error" not in box for _, box in runs)
    assert sorted(box["r"].status_code for _, box in runs) == [201, 409]
    with app.state.db.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users WHERE email = 'dbl@x.test'")).scalar() == 1


def test_a_deadlock_during_accept_is_a_409_email_taken(owner, new_client, outbox, monkeypatch):
    """The same answer when the database error is injected, so it does not depend on lock timing."""
    from psycopg import errors
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session
    owner_client, _ = owner
    _, token = _invite(owner_client, outbox, "inj@acme.test")
    real_flush = Session.flush

    def flush(self, *args, **kwargs):
        if any(isinstance(o, User) for o in self.new):
            raise OperationalError("INSERT", {}, errors.DeadlockDetected("deadlock detected"))
        return real_flush(self, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", flush)
    response = _accept(new_client(), token)
    assert response.status_code == 409 and response.json()["error"] == "email_taken"


def test_invitation_email_is_indexed(database):
    with database.engine.connect() as conn:
        defs = [r[0] for r in conn.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename = 'invitations'"))]
    assert any("(email)" in d for d in defs), defs
