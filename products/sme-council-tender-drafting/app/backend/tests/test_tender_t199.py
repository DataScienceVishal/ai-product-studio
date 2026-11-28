"""T-199 / T-201 leftovers: evidence purge horizon, abbreviation-safe trimming, GET draft payload, token reporting,
redraft lock order. Model calls: none (ScriptedFakeAI)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.maintenance import purge
from app.tender import draft as dr
from app.tender_models import AITask, Draft, EvidenceItem, SourceDocument

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
