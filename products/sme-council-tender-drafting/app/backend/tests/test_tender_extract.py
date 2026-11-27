"""S4: chunking, extraction on ScriptedFakeAI, amber quotes, limit cross-check, merge, checklist API, cost refusal."""
import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.ai import AIResult
from app.models import AIUsage
from app.tender import extract as ex
from app.tender import runner
from app.tender.scripted_ai import ScriptedFakeAI
from app.tender_models import AITask, Requirement

from .conftest import sign_up
from .tender_files import pdf
from .test_tender_ingest import make_pack, tender_url, up

LEASE = timedelta(minutes=10)
QUESTIONS = [["1. Describe your quality system (maximum 300 words)."], ["2. State your insurance cover."],
             ["3) Explain your mobilisation plan (maximum 500 words)."]]


@pytest.fixture
def client(new_client):
    c = new_client()
    sign_up(c)
    return c


@pytest.fixture
def db(app):
    s = app.state.db.sessions()
    yield s
    s.close()


def setup_pack(client, pages=QUESTIONS):
    pid = make_pack(client)
    r = up(client, tender_url(pid), pdf(pages))
    assert r.status_code == 201, r.text
    return pid


def run(app, provider=None):
    return runner.run_one(app.state.db.sessions, LEASE, provider=provider or ScriptedFakeAI())


def test_chunks_overlap_by_one_page():
    pages = [(n, f"t{n}") for n in range(1, 8)]
    chunks = ex.make_chunks(pages, size=3, overlap=1)
    assert [[n for n, _ in c] for c in chunks] == [[1, 2, 3], [3, 4, 5], [5, 6, 7]]
    assert ex.make_chunks(pages[:2], size=3, overlap=1) == [pages[:2]]
    assert ex.make_chunks([]) == []


def test_extract_on_the_scripted_fake_builds_the_checklist(client, app):
    pid = setup_pack(client)
    r = client.post(f"/api/packs/{pid}/extract")
    assert r.status_code == 202
    assert client.post(f"/api/packs/{pid}/extract").json()["id"] == r.json()["id"]  # idempotent
    assert run(app)
    status = client.get(f"/api/packs/{pid}/status").json()
    assert status["pack"]["status"] == "review" and status["tasks"][0]["status"] == "done"
    reqs = client.get(f"/api/packs/{pid}/requirements").json()["requirements"]
    assert [(q["ref"], q["word_limit"], q["source_page"], q["quote_verified"], q["flags"]) for q in reqs] == [
        ("1", 300, 1, True, []), ("2", None, 2, True, []), ("3", 500, 3, True, [])]


class Tweak(ScriptedFakeAI):
    """The heuristic answer, then changed by a function: stands in for a model that gets things wrong."""
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def complete(self, system, user, max_output_tokens=1200, *, json_schema=None, effort=None):
        res = super().complete(system, user, max_output_tokens, json_schema=json_schema, effort=effort)
        data = self.fn(json.loads(res.text))
        return AIResult(json.dumps(data), res.input_tokens, res.output_tokens, res.model)


def reqs_after(client, app, provider):
    pid = setup_pack(client)
    client.post(f"/api/packs/{pid}/extract")
    run(app, provider)
    return pid, client.get(f"/api/packs/{pid}/requirements").json()["requirements"]


def test_a_quote_not_on_the_page_is_amber_but_kept(client, app):
    def bad(d):
        d["items"][0]["source_quote"] = "A sentence the buyer never wrote"
        return d
    _, reqs = reqs_after(client, app, Tweak(bad))
    assert [q["quote_verified"] for q in reqs] == [False, True, True] and len(reqs) == 3


def test_a_limit_that_disagrees_with_the_page_is_flagged(client, app):
    def bad(d):
        d["items"][0]["word_limit"] = 250  # the page says 300
        d["items"][1]["word_limit"] = 100  # the page states none: no flag
        return d
    _, reqs = reqs_after(client, app, Tweak(bad))
    assert [q["flags"] for q in reqs] == [["limit_mismatch"], [], []]


def test_a_duplicate_across_the_overlap_is_merged(client, app, monkeypatch):
    orig = ex.make_chunks
    monkeypatch.setattr(ex, "make_chunks", lambda pages, size=2, overlap=1: orig(pages, 2, 1))
    provider = ScriptedFakeAI()
    _, reqs = reqs_after(client, app, provider)
    assert len(provider.calls) == 2 and [q["ref"] for q in reqs] == ["1", "2", "3"]


def test_merge_by_similarity_when_refs_differ():
    a = {"ref": "", "text": "Describe how you will manage subcontractors.", "source_page": 2}
    b = {"ref": "Q9", "text": "Describe how you will manage subcontractors", "source_page": 3}
    c = {"ref": "", "text": "Provide three references.", "source_page": 3}
    assert ex.merge_items([a, b, c]) == [a, c]


def test_model_json_is_kept_and_user_edits_do_not_change_it(client, app, db):
    pid, reqs = reqs_after(client, app, None)
    rid = reqs[0]["id"]
    r = client.patch(f"/api/requirements/{rid}", json={"text": "Edited text", "word_limit": 350})
    assert r.status_code == 200 and r.json()["edited"] and r.json()["origin"] == "model"
    row = db.scalar(select(Requirement).where(Requirement.id == rid))
    assert row.model_json["word_limit"] == 300 and row.model_json["text"].startswith("Describe")
    assert client.patch(f"/api/requirements/{rid}", json={"text": None}).status_code == 422


def test_add_confirm_and_cross_tenant_404(client, app, new_client):
    pid, reqs = reqs_after(client, app, None)
    added = client.post(f"/api/packs/{pid}/requirements", json={"text": "Provide a business continuity plan", "kind": "mandatory"})
    assert added.status_code == 201 and added.json()["origin"] == "user"
    client.patch(f"/api/requirements/{reqs[1]['id']}", json={"status": "removed"})
    done = client.post(f"/api/packs/{pid}/confirm").json()
    assert done["confirmed"] == 3 and done["pack"]["status"] == "drafting"
    listed = client.get(f"/api/packs/{pid}/requirements").json()["requirements"]
    assert len(listed) == 3 and {q["status"] for q in listed} == {"confirmed"}
    other = new_client()
    sign_up(other, email="b@b.test", company="B Ltd")
    assert other.get(f"/api/packs/{pid}/requirements").status_code == 404
    assert other.patch(f"/api/requirements/{reqs[0]['id']}", json={"text": "x"}).status_code == 404
    assert other.post(f"/api/packs/{pid}/extract").status_code == 404
    assert other.post(f"/api/packs/{pid}/confirm").status_code == 404


def test_extract_needs_a_document_and_confirm_needs_a_list(client):
    pid = make_pack(client)
    assert client.post(f"/api/packs/{pid}/extract").status_code == 409
    assert client.post(f"/api/packs/{pid}/confirm").status_code == 409


def test_with_azure_settings_the_reservation_is_refused_not_sent(client, app, db):
    """R3: a real chunk reserves more than the 30k trial daily cap, so the call is refused before it is sent."""
    pages = [[f"{i}. Question number {i} " + "word " * 40] for i in range(1, 4)]
    pid = setup_pack(client, pages)
    client.post(f"/api/packs/{pid}/extract")
    sent = []

    class AzureLike(ScriptedFakeAI):
        name = "azure"
        output_headroom = 1500

        def complete(self, *a, **k):
            sent.append(1)
            return super().complete(*a, **k)
    # a big page makes the reservation exceed the trial daily cap
    from app.tender_models import DocumentPage
    for p in db.scalars(select(DocumentPage)):
        p.text = p.text + " filler" * 6000
    db.commit()
    run(app, AzureLike())
    t = db.scalar(select(AITask))
    db.refresh(t)
    assert t.status == "failed" and t.error_code in ("ai_daily_cap_reached", "ai_cap_reached")
    assert sent == [] and not list(db.scalars(select(AIUsage).where(AIUsage.feature.like("extract%"))))
