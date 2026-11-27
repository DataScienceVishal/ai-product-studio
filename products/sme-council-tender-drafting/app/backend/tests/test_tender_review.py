"""S7 backend routes: one pack, cited passages, coverage and sign-off (T-191), and the T-201 items done with them."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.tender import gate
from app.tender_models import Signoff, TenderPack

from .conftest import sign_up
from .test_tender_claimcheck import Judge, check_now, client, db, evidence_doc, honest, pack_status  # noqa: F401
from .test_tender_draft import confirmed_pack, draft_now, latest


def ready_pack(client, app):
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    check_now(client, app, pid, Judge(honest))
    assert pack_status(client, pid) == "ready"
    return pid, rid


SIGN = {"reviewer_name": "Ann Lee", "accept_statement": True, "statement_version": gate.STATEMENT_VERSION}


def test_get_pack_and_the_draft_reply_carry_what_the_screens_need(client, app):
    pid, rid = confirmed_pack(client, app)
    p = client.get(f"/api/packs/{pid}")
    assert p.status_code == 200 and p.json()["id"] == pid
    d = client.get(f"/api/requirements/{rid}/draft").json()
    assert d["requirement"]["id"] == rid and d["requirement"]["pack_id"] == pid


def test_coverage_lists_confirmed_rows_the_gate_verdict_and_the_statement(client, app):
    pid, rid = ready_pack(client, app)
    c = client.get(f"/api/packs/{pid}/coverage").json()
    assert [r["requirement_id"] for r in c["rows"]] == [rid]
    row = c["rows"][0]
    assert row["answered"] is True and row["checked"] is True and row["within_limit"] is True and row["claims"]["supported"] >= 1
    assert [r.split(":")[0] for r in c["export"]["reasons"]] == ["no_signoff"]
    assert c["statement"] == {"version": gate.STATEMENT_VERSION, "text": gate.STATEMENT_TEXT} and c["signoff"] is None
    assert "not" in c["notice"] and "compliant" in c["notice"]


def test_coverage_shows_an_unanswered_question(client, app):
    pid, rid = confirmed_pack(client, app)
    row = client.get(f"/api/packs/{pid}/coverage").json()["rows"][0]
    assert row["answered"] is False and row["words"] is None and row["checked"] is False


def test_signoff_records_a_named_sign_off_and_opens_the_gate(client, app, db):
    pid, rid = ready_pack(client, app)
    r = client.post(f"/api/packs/{pid}/signoff", json=SIGN)
    assert r.status_code == 201 and r.json()["pack"]["status"] == "signed" and r.json()["reviewer_name"] == "Ann Lee"
    so = db.scalar(select(Signoff))
    assert so.reviewer_name == "Ann Lee" and so.reviewer_user_id is not None and so.statement_version == "v1" and so.drafts_digest
    assert client.get(f"/api/packs/{pid}/export-check").json() == {"allowed": True, "reasons": []}
    assert client.get(f"/api/packs/{pid}/coverage").json()["signoff"]["reviewer_name"] == "Ann Lee"
    assert client.post(f"/api/packs/{pid}/signoff", json=SIGN).status_code == 409  # already signed
    assert client.put(f"/api/requirements/{rid}/draft", json={"text": "Changed."}).status_code == 409  # locked


@pytest.mark.parametrize("body", [
    {"reviewer_name": "Ann", "accept_statement": False, "statement_version": "v1"},
    {"reviewer_name": "Ann", "statement_version": "v1"},
    {"reviewer_name": "Ann", "accept_statement": True, "statement_version": "v0"},
    {"reviewer_name": "Ann", "accept_statement": True},
])
def test_signoff_needs_the_tick_and_the_current_statement_version(client, app, db, body):
    pid, _ = ready_pack(client, app)
    r = client.post(f"/api/packs/{pid}/signoff", json=body)
    assert r.status_code == 422 and r.json()["error"] == "statement_required"
    assert db.scalar(select(Signoff)) is None and pack_status(client, pid) == "ready"


def test_signoff_needs_a_name(client, app):
    pid, _ = ready_pack(client, app)
    assert client.post(f"/api/packs/{pid}/signoff", json=SIGN | {"reviewer_name": "   "}).status_code == 422


def test_signoff_is_refused_before_the_pack_is_ready(client, app, db):
    pid, _ = confirmed_pack(client, app)
    r = client.post(f"/api/packs/{pid}/signoff", json=SIGN)
    assert r.status_code == 409 and r.json()["error"] == "not_ready" and db.scalar(select(Signoff)) is None


def test_signoff_reruns_the_gate_on_the_server_even_if_the_pack_says_ready(client, app, db):
    """A status of `ready` is not trusted: the pure gate runs on the current rows with the sign-off the request would make."""
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    check_now(client, app, pid, Judge(lambda d, p: [dict(c, evidence_quote="We hold every accreditation known to man") for c in honest(d, p)]))
    assert pack_status(client, pid) == "drafting"
    db.execute(TenderPack.__table__.update().values(status="ready"))  # a stale or wrong flag
    db.commit()
    r = client.post(f"/api/packs/{pid}/signoff", json=SIGN)
    assert r.status_code == 409 and r.json()["error"] == "export_blocked" and "claims_blocked" in r.json()["message"]
    db.expire_all()
    assert db.scalar(select(Signoff)) is None and db.scalar(select(TenderPack.status)) == "ready"


def test_signoff_is_refused_when_cited_evidence_was_deleted_and_the_flag_is_stale(client, app, db):
    pid, _ = ready_pack(client, app)
    client.delete(f"/api/documents/{evidence_doc(client)[0]['id']}")
    db.execute(TenderPack.__table__.update().values(status="ready"))
    db.commit()
    r = client.post(f"/api/packs/{pid}/signoff", json=SIGN)
    assert r.status_code == 409 and "evidence_removed" in r.json()["message"] and db.scalar(select(Signoff)) is None


def test_other_tenants_get_404_everywhere_and_nothing_is_signed(client, app, new_client, db):
    pid, rid = ready_pack(client, app)
    other = new_client()
    sign_up(other, email="o7@o.test", company="O7")
    for method, url, kw in [("get", f"/api/packs/{pid}", {}), ("get", f"/api/packs/{pid}/coverage", {}),
                            ("post", f"/api/packs/{pid}/signoff", {"json": SIGN}), ("post", f"/api/packs/{pid}/check", {})]:
        assert getattr(other, method)(url, **kw).status_code == 404, url
    assert db.scalar(select(Signoff)) is None and pack_status(client, pid) == "ready"


def test_signoff_needs_a_session(client, app, new_client):
    pid, _ = ready_pack(client, app)
    assert new_client().post(f"/api/packs/{pid}/signoff", json=SIGN).status_code == 401


def test_passages_show_text_with_document_and_page_and_hide_removed_text(client, app):
    pid, rid = ready_pack(client, app)
    cited = latest(client, rid)["draft"]["cited_ids"]
    assert cited
    ids = ",".join(map(str, cited))
    got = client.get("/api/evidence/passages", params={"ids": ids}).json()["passages"]
    assert [p["display_no"] for p in got] == sorted(cited)
    assert got[0]["document"] == "quality.txt" and got[0]["page_from"] == 1 and got[0]["text"] and got[0]["removed"] is False
    client.delete(f"/api/documents/{evidence_doc(client)[0]['id']}")
    gone = client.get("/api/evidence/passages", params={"ids": ids}).json()["passages"]
    assert gone and all(p["removed"] and p["text"] == "" for p in gone)


def test_passages_are_tenant_scoped_and_validate_ids(client, app, new_client):
    ready_pack(client, app)
    other = new_client()
    sign_up(other, email="o8@o.test", company="O8")
    assert other.get("/api/evidence/passages", params={"ids": "1,2,3,4,5"}).json() == {"passages": []}
    assert client.get("/api/evidence/passages", params={"ids": "1;DROP"}).status_code == 422
    assert client.get("/api/evidence/passages", params={"ids": ""}).status_code == 422


def test_evidence_deleted_during_the_check_does_not_leave_the_pack_ready(client, app):
    """T-201 item 5: the passages were live when the model was asked, gone when the check finished."""
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    doc_id = evidence_doc(client)[0]["id"]

    class DeletesMidCheck(Judge):
        def complete(self, *a, **k):
            res = super().complete(*a, **k)
            if (k.get("json_schema") or {}).get("title") == "ClaimcheckOutput":
                assert client.delete(f"/api/documents/{doc_id}").status_code == 204
            return res
    check_now(client, app, pid, DeletesMidCheck(honest))
    assert pack_status(client, pid) == "drafting"
    gate_view = client.get(f"/api/packs/{pid}/export-check").json()
    assert not gate_view["allowed"] and any(r.startswith("evidence_removed") for r in gate_view["reasons"])
    assert client.post(f"/api/packs/{pid}/signoff", json=SIGN).status_code == 409


def test_queue_check_still_works_with_the_pack_row_locked(client, app):
    pid, _ = confirmed_pack(client, app)
    draft_now(client, app, pid)
    first = client.post(f"/api/packs/{pid}/check")
    again = client.post(f"/api/packs/{pid}/check")
    assert first.status_code == 202 and again.status_code == 202 and first.json()["id"] == again.json()["id"]
