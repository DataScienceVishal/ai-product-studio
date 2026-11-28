"""T-199 / T-201 leftovers: evidence purge horizon, abbreviation-safe trimming, GET draft payload, token reporting,
redraft lock order. Model calls: none (ScriptedFakeAI)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.maintenance import purge
from app.tender import draft as dr
from app.tender_models import AITask, Claim, Draft, EvidenceItem, SourceDocument

from .conftest import sign_up
from .test_tender_claimcheck import client, db, evidence_doc  # noqa: F401
from .test_tender_draft import confirmed_pack, draft_now, latest
from .test_tender_export import signed_pack
from .test_tender_review import ready_pack


def _soft_delete(client, db, days_ago):
    doc = evidence_doc(client)[0]
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    db.expire_all()
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    d = db.get(SourceDocument, doc["id"])
    d.deleted_at = when
    for i in db.scalars(select(EvidenceItem).where(EvidenceItem.document_id == d.id)):
        i.deleted_at = when
    db.commit()
    return doc["id"]


def _docs(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(SourceDocument).where(SourceDocument.kind == "evidence")), \
        db.scalar(select(func.count()).select_from(EvidenceItem))


def test_purge_removes_evidence_deleted_over_90_days_ago_and_its_passages(client, app, db):
    pid, _ = ready_pack(client, app)
    _soft_delete(client, db, 91)
    assert _docs(db)[0] == 1
    counts = purge(db)
    assert counts["soft_deleted_evidence"] == 1 and _docs(db) == (0, 0)


def test_purge_keeps_recently_deleted_and_live_evidence(client, app, db):
    ready_pack(client, app)
    _soft_delete(client, db, 89)
    assert purge(db)["soft_deleted_evidence"] == 0 and _docs(db)[0] == 1
    # a live document is never purged however old
    d = db.scalar(select(SourceDocument).where(SourceDocument.kind == "evidence"))
    d.deleted_at = None
    d.created_at = datetime.now(timezone.utc) - timedelta(days=500)
    db.commit()
    assert purge(db)["soft_deleted_evidence"] == 0


def test_purge_keeps_evidence_cited_by_an_exported_pack(client, app, db):
    pid, _ = signed_pack(client, app)
    assert client.get(f"/api/packs/{pid}/export", headers={"X-Requested-With": "fetch"}).status_code == 200
    _soft_delete(client, db, 200)
    assert purge(db)["soft_deleted_evidence"] == 0
    assert _docs(db)[0] == 1 and _docs(db)[1] > 0  # the appendix text stays while an export cites it


def test_purge_removes_aged_evidence_when_the_pack_was_never_exported(client, app, db):
    pid, _ = signed_pack(client, app)  # signed, but no exports row
    _soft_delete(client, db, 200)
    assert purge(db)["soft_deleted_evidence"] == 1


def test_purge_keeps_evidence_cited_only_through_outside_ids_or_the_text(client, app, db):
    """Review M1: the appendix prints every [E-n] in the text and every claim citation, not only cited_ids."""
    from sqlalchemy import update
    pid, _ = signed_pack(client, app)
    assert client.get(f"/api/packs/{pid}/export", headers={"X-Requested-With": "fetch"}).status_code == 200
    no = db.scalar(select(EvidenceItem.display_no).order_by(EvidenceItem.display_no).limit(1))
    # the exported draft cites it only as an outside id (stored copy and text marker), never in cited_ids
    for d in db.scalars(select(Draft)):
        d.cited_ids, d.outside_ids, d.text = [], [no], f"We take quality seriously [E-{no}]."
    for c in db.scalars(select(Claim)):
        c.cited_ids = []
    db.commit()
    _soft_delete(client, db, 200)
    assert purge(db)["soft_deleted_evidence"] == 0
    # only the text marker remains
    for d in db.scalars(select(Draft)):
        d.outside_ids = []
    db.commit()
    assert purge(db)["soft_deleted_evidence"] == 0
    # only a claim's citation remains
    for d in db.scalars(select(Draft)):
        d.text = "No marker here."
    for c in db.scalars(select(Claim)):
        c.cited_ids = [no]
    db.commit()
    assert purge(db)["soft_deleted_evidence"] == 0
    for c in db.scalars(select(Claim)):
        c.cited_ids = []
    db.commit()
    assert purge(db)["soft_deleted_evidence"] == 1


def test_one_tenants_export_does_not_protect_another_tenants_evidence_with_the_same_number(client, app, db, new_client):
    other = new_client()
    sign_up(other, email="b@acme.test", company="Beta Ltd")
    pid, _ = signed_pack(client, app)
    assert client.get(f"/api/packs/{pid}/export", headers={"X-Requested-With": "fetch"}).status_code == 200
    # tenant B: same evidence text, so the same display number, a ready pack that was never exported
    ready_pack(other, app)
    assert {i.display_no for i in db.scalars(select(EvidenceItem).where(EvidenceItem.tenant_id == db.scalar(
        select(SourceDocument.tenant_id).order_by(SourceDocument.created_at.desc()).limit(1))))}
    doc_b = evidence_doc(other)[0]
    assert other.delete(f"/api/documents/{doc_b['id']}").status_code == 204
    db.expire_all()
    d = db.get(SourceDocument, doc_b["id"])
    when = datetime.now(timezone.utc) - timedelta(days=200)
    d.deleted_at = when
    for i in db.scalars(select(EvidenceItem).where(EvidenceItem.document_id == d.id)):
        i.deleted_at = when
    db.commit()
    nos_a = {i.display_no for i in db.scalars(select(EvidenceItem).where(EvidenceItem.tenant_id != d.tenant_id))}
    nos_b = {i.display_no for i in db.scalars(select(EvidenceItem).where(EvidenceItem.tenant_id == d.tenant_id))}
    assert nos_a & nos_b  # the numbers really collide across tenants
    assert purge(db)["soft_deleted_evidence"] == 1  # B's document goes; A's export protects only A's rows
    assert db.get(SourceDocument, doc_b["id"]) is None
    assert db.scalar(select(func.count()).select_from(SourceDocument).where(SourceDocument.kind == "evidence")) == 1


# ---------- T-189 nits ----------

def test_trimming_does_not_split_on_abbreviations():
    s = "We hold ISO certificates e.g. 9001 and 14001. Our subcontractor is Acme Ltd. and it is vetted. See Contract No. 5 for details."
    parts = dr.split_sentences(s)
    assert len(parts) == 3, parts
    assert parts[0].endswith("14001.") and "Ltd. and" in parts[1] and "No. 5" in parts[2]
    out = dr.fit_to_limit(s, 18)
    assert out in (parts[0], " ".join(parts[:2])) and dr.count_words(out) <= 18


def test_get_draft_returns_the_chosen_version_text_and_a_light_version_list(client, app):
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    client.put(f"/api/requirements/{rid}/draft", json={"text": "Edited answer one.", "base_version": 1})
    r = latest(client, rid)
    assert r["draft"]["version"] == 2 and r["draft"]["text"] == "Edited answer one."
    assert [v["version"] for v in r["versions"]] == [2, 1] and all("text" not in v for v in r["versions"])
    old = client.get(f"/api/requirements/{rid}/draft?version=1").json()
    assert old["draft"]["version"] == 1 and old["draft"]["author"] == "ai"
    assert client.get(f"/api/requirements/{rid}/draft?version=9").status_code == 404


def test_tokens_used_before_a_failure_are_kept_on_the_task(client, app, db):
    """T-189 nit 9: a pack-wide task that fails on question 2 still reports the tokens of question 1."""
    from app.errors import AppError
    from app.tender.scripted_ai import ScriptedFakeAI
    pid, rid = confirmed_pack(client, app)
    real = dr.draft_answer
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 2:
            raise AppError(429, "ai_daily_cap_reached", "x")
        out = real(*a, **k)
        out.input_tokens, out.output_tokens = 100, 50
        return out
    # a second confirmed question
    assert client.post(f"/api/packs/{pid}/requirements", json={"kind": "question", "text": "Describe your training.",
                                                                "word_limit": 100}).status_code in (200, 201)
    client.post(f"/api/packs/{pid}/confirm")
    dr_mod = dr
    orig = dr_mod.draft_answer
    dr_mod.draft_answer = flaky
    try:
        draft_now(client, app, pid)
    finally:
        dr_mod.draft_answer = orig
    db.expire_all()
    t = db.scalar(select(AITask).where(AITask.kind == "draft").order_by(AITask.created_at.desc()))
    assert t.status == "failed" and t.error_code == "ai_daily_cap_reached" and (t.input_tokens, t.output_tokens) == (100, 50)


def test_tokens_spent_inside_a_draft_call_that_then_fails_are_kept_on_the_task(client, app, db):
    """T-207: the first model call returns an invalid answer (100 in, 50 out), the repair call is invalid too, so run_task
    raises ai_invalid_output. Both calls were billed; the task must report them (before: 0)."""
    import json
    from app.ai import AIResult
    from app.tender.scripted_ai import ScriptedFakeAI

    class Bad(ScriptedFakeAI):
        calls = 0

        def complete(self, *a, **k):
            Bad.calls += 1
            return AIResult("{not json", 100, 50, "fake")
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid, Bad())
    assert Bad.calls == 2
    db.expire_all()
    t = db.scalar(select(AITask).where(AITask.kind == "draft").order_by(AITask.created_at.desc()))
    assert t.status == "failed" and t.error_code == "ai_invalid_output" and (t.input_tokens, t.output_tokens) == (200, 100)


def test_a_failed_shorten_retry_keeps_the_draft_and_counts_its_tokens(client, app, db):
    """T-207: the draft call succeeds (known tokens), the shorten retry then raises; the draft is kept (sentence drop) and the
    failed retry's billed tokens are in the task total."""
    import json
    from app.ai import AIResult
    from app.tender.scripted_ai import ScriptedFakeAI

    class Long(ScriptedFakeAI):
        def complete(self, system, user, *a, **k):
            if "previous_answer" in user:  # the shorten call
                return AIResult("{not json", 7, 3, "fake")
            long_answer = " ".join(["word"] * 400) + ". End."
            return AIResult(json.dumps({"answer": long_answer, "gaps": [], "used_ids": []}), 100, 50, "fake")
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid, Long())
    db.expire_all()
    t = db.scalar(select(AITask).where(AITask.kind == "draft").order_by(AITask.created_at.desc()))
    assert t.status == "done" and (t.input_tokens, t.output_tokens) == (100 + 14, 50 + 6)  # the shorten step makes a call and one repair call, 7 in and 3 out each
