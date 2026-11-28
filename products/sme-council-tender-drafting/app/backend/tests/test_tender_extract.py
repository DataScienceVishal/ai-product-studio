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
from app.tender_models import AITask, Requirement, TenderPack

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
    # the pack is not stuck in "extracting": the user can add items by hand and confirm
    assert client.get(f"/api/packs/{pid}/status").json()["pack"]["status"] == "uploaded"
    assert client.post(f"/api/packs/{pid}/requirements", json={"text": "Hand-added question"}).status_code == 201
    assert client.post(f"/api/packs/{pid}/confirm").status_code == 200
    assert sent == [] and not list(db.scalars(select(AIUsage).where(AIUsage.feature.like("extract%"))))


def test_a_failed_run_on_a_pack_with_items_goes_back_to_review(client, app, db):
    pid, _ = reqs_after(client, app, None)
    assert client.post(f"/api/packs/{pid}/extract").status_code == 202

    class Boom(ScriptedFakeAI):
        def complete(self, *a, **k):
            raise RuntimeError("down")
    run(app, Boom())
    assert client.get(f"/api/packs/{pid}/status").json()["pack"]["status"] == "review"


@pytest.mark.parametrize("status", ["drafting", "checking", "ready", "signed", "exported"])
def test_extract_is_409_once_the_checklist_is_confirmed_or_later(client, db, status):
    from app.tender_models import TenderPack
    pid = setup_pack(client)
    db.query(TenderPack).update({"status": status})
    db.commit()
    assert client.post(f"/api/packs/{pid}/extract").status_code == 409


def test_a_rerun_replaces_only_unedited_proposed_model_rows(client, app, db):
    pid, reqs = reqs_after(client, app, None)
    edited, removed, confirmed_like = reqs[0]["id"], reqs[1]["id"], reqs[2]["id"]
    client.patch(f"/api/requirements/{edited}", json={"text": "Describe your quality system (maximum 300 words). Edited"})
    client.patch(f"/api/requirements/{removed}", json={"status": "removed"})
    client.patch(f"/api/requirements/{confirmed_like}", json={"status": "confirmed"})
    mine = client.post(f"/api/packs/{pid}/requirements", json={"text": "My own item"}).json()["id"]
    assert client.post(f"/api/packs/{pid}/extract").status_code == 202
    run(app)
    rows = {r.id: r for r in db.scalars(select(Requirement).where(Requirement.pack_id == pid))}
    ids = {str(i) for i in rows}
    assert {edited, removed, confirmed_like, mine} <= ids  # nothing the user touched was deleted
    assert len(rows) == 4  # and the model's items were not added a second time
    assert [r.text for r in rows.values() if str(r.id) == edited][0].endswith("Edited")


def test_a_blank_ref_or_a_far_page_does_not_merge():
    a = {"ref": "", "text": "First thing to do here", "source_page": 1}
    b = {"ref": "", "text": "Second quite different matter", "source_page": 1}
    c = {"ref": "1", "text": "Same ref far away on another page entirely", "source_page": 9}
    d = {"ref": "1", "text": "A different question about pricing", "source_page": 1}
    assert ex.merge_items([a, b, c, d]) == [a, b, c, d]  # blank refs never match; ref 1 on page 9 is not ref 1 on page 1


# ---------- T-198: review leftovers ----------

def _exhaust(app, db, pid, kind):
    """Queue a task that has already used its attempts and let the runner find it."""
    from datetime import datetime, timezone
    t = db.scalar(select(AITask).where(AITask.kind == kind)) if kind == "extract" else None
    if t is None:
        pack = db.scalar(select(TenderPack).where(TenderPack.id == pid))
        t = AITask(tenant_id=pack.tenant_id, pack_id=pack.id, kind=kind, status="queued", attempts=runner.MAX_ATTEMPTS)
        db.add(t)
    t.status, t.attempts = "queued", runner.MAX_ATTEMPTS
    db.commit()
    runner.run_one(app.state.db.sessions, LEASE, provider=ScriptedFakeAI())  # False: the exhausted task is failed in claim
    db.refresh(t)
    assert t.status == "failed" and t.error_code == "attempts_exhausted"


def test_attempts_exhausted_extract_resets_the_pack(client, app, db):
    pid = setup_pack(client)
    assert client.post(f"/api/packs/{pid}/extract").status_code == 202
    assert client.get(f"/api/packs/{pid}/status").json()["pack"]["status"] == "extracting"
    _exhaust(app, db, pid, "extract")
    assert client.get(f"/api/packs/{pid}/status").json()["pack"]["status"] == "uploaded"
    assert client.post(f"/api/packs/{pid}/requirements", json={"text": "By hand"}).status_code == 201
    assert client.post(f"/api/packs/{pid}/confirm").status_code == 200


def test_attempts_exhausted_draft_resets_a_stuck_checking_pack(client, app, db):
    pid = setup_pack(client)
    client.post(f"/api/packs/{pid}/requirements", json={"text": "Q one", "kind": "question"})
    assert client.post(f"/api/packs/{pid}/confirm").status_code == 200
    pack = db.scalar(select(TenderPack).where(TenderPack.id == pid))
    pack.status = "checking"
    db.commit()
    _exhaust(app, db, pid, "draft")
    db.refresh(pack)
    assert pack.status == "drafting"


def test_a_crashing_failure_hook_does_not_break_the_runner(client, app, db, monkeypatch):
    pid = setup_pack(client)
    client.post(f"/api/packs/{pid}/extract")

    def boom(*a):
        raise RuntimeError("hook down")
    monkeypatch.setitem(runner.FAILURE_HOOKS, "extract", boom)
    _exhaust(app, db, pid, "extract")


def test_requirement_seq_is_unique_per_pack(client, app, db):
    from sqlalchemy.exc import IntegrityError
    pid = setup_pack(client)
    for i in range(3):
        assert client.post(f"/api/packs/{pid}/requirements", json={"text": f"Item {i}"}).status_code == 201
    seqs = [r["seq"] for r in client.get(f"/api/packs/{pid}/requirements").json()["requirements"]]
    assert seqs == [1, 2, 3]
    first = db.scalar(select(Requirement).where(Requirement.seq == 1))
    db.add(Requirement(tenant_id=first.tenant_id, pack_id=first.pack_id, seq=1, kind="other", text="dup"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_concurrent_adds_get_distinct_seqs(client, app):
    import threading
    pid = setup_pack(client)
    codes = []

    def add(i):
        codes.append(client.post(f"/api/packs/{pid}/requirements", json={"text": f"Item {i}"}).status_code)
    threads = [threading.Thread(target=add, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert codes == [201] * 6
    seqs = sorted(r["seq"] for r in client.get(f"/api/packs/{pid}/requirements").json()["requirements"])
    assert seqs == [1, 2, 3, 4, 5, 6]


def test_source_page_out_of_range_is_clamped_and_flagged():
    pages = {1: "1. Describe X (maximum 300 words).", 2: "2. Describe Y."}
    item = {"ref": "1", "kind": "question", "text": "Describe X", "word_limit": 300, "page_limit": None,
            "source_page": 9, "source_quote": "Describe X"}
    verified, flags = ex.check_item(item, pages)
    assert verified is False and "page_out_of_range" in flags
    assert ex.check_item({**item, "source_page": -3}, pages)[1] == ["page_out_of_range"]
    assert ex.check_item({**item, "source_page": 1}, pages) == (True, [])


def test_limit_check_ignores_a_neighbouring_questions_limit():
    page = ("1. Describe your quality system (maximum 500 words).\n\n2. State your insurance cover.\n\n"
            "3. Explain mobilisation (max 200 words).")
    assert ex.stated_word_limit(page, "State your insurance cover.") is None  # no limit of its own: no fallback guess
    assert ex.stated_word_limit(page, "Describe your quality system") == 500
    assert ex.stated_word_limit(page, "Explain mobilisation") == 200
    assert ex.stated_word_limit(page, "not on this page") == 500  # quote not located: the first limit on the page


def test_limit_check_survives_collapsed_whitespace_in_the_raw_page():
    page = "intro   text\n\n\n   1.   Describe   your   plan\n(maximum   250   words)."
    assert ex.stated_word_limit(page, "Describe your plan") == 250


def test_page_limit_wording_sides_of_a4():
    page = "2. Describe your approach. Answers must be no more than 2 sides of A4.\n3. Another. Max 3 pages."
    assert ex.stated_page_limit(page, "Describe your approach.") == 2
    item = {"ref": "2", "kind": "question", "text": "Describe your approach.", "word_limit": None, "page_limit": 5,
            "source_page": 1, "source_quote": "Describe your approach."}
    assert ex.check_item(item, {1: page}) == (True, ["limit_mismatch"])
    assert ex.check_item({**item, "page_limit": 2}, {1: page}) == (True, [])


# ---------- T-200: the heading limit window and the pack lock ----------

def test_a_limit_in_the_heading_before_the_quote_is_found():
    page = ("1. Quality system\nDescribe your quality system. (maximum 300 words)\n\n"
            "Q3 Social Value (max 500 words, 10%)\nDescribe the social value you will deliver.\n\n"
            "Q4 Mobilisation\nExplain your mobilisation plan. (maximum 200 words)")
    assert ex.stated_word_limit(page, "Describe the social value you will deliver.") == 500   # heading on the line above
    assert ex.stated_word_limit(page, "Explain your mobilisation plan.") == 200
    blank = "Q3 Social Value (max 500 words, 10%)\n\nDescribe the social value you will deliver."
    assert ex.stated_word_limit(blank, "Describe the social value you will deliver.") == 500   # heading block above
    assert ex.stated_word_limit(page, "Describe your quality system.") == 300


def test_the_heading_window_never_borrows_the_previous_questions_limit():
    page = ("Q2 Quality (max 300 words)\nDescribe your quality system.\n\n"
            "Q3 Insurance\nState your insurance cover.\n")
    assert ex.stated_word_limit(page, "State your insurance cover.") is None
    page2 = "2. Quality (maximum 300 words).\n\n3. State your insurance cover."
    assert ex.stated_word_limit(page2, "State your insurance cover.") is None  # previous block ends a sentence: not a heading
    numbered = "2. Quality (maximum 300 words)\nBody two.\n3. Insurance\nState your insurance cover."
    assert ex.stated_word_limit(numbered, "State your insurance cover.") is None


def test_an_unnumbered_one_line_previous_question_is_not_taken_as_the_next_heading():
    """T-201 item 7: the previous question's own limit must not become the next question's window."""
    page = "Describe your approach in no more than 200 words\n\nDescribe your staffing plan."
    assert ex.stated_word_limit(page, "Describe your staffing plan.") is None
    same_block = "Describe your approach in no more than 200 words\nDescribe your staffing plan."
    assert ex.stated_word_limit(same_block, "Describe your staffing plan.") is None
    # a real heading still counts, also one that starts with a question word
    assert ex.stated_word_limit("How we deliver social value (max 300 words)\n\nDescribe the social value you will deliver.",
                                "Describe the social value you will deliver.") == 300
    assert ex.stated_word_limit("Staffing (max 150 words)\n\nDescribe your staffing plan.", "Describe your staffing plan.") == 150


def test_a_wrong_limit_is_flagged_when_the_limit_is_in_the_heading():
    page = {1: "Q3 Social Value (max 500 words, 10%)\nDescribe the social value you will deliver."}
    item = {"ref": "Q3", "kind": "question", "text": "Describe the social value you will deliver.", "word_limit": 300,
            "page_limit": None, "source_page": 1, "source_quote": "Describe the social value you will deliver."}
    assert "limit_mismatch" in ex.check_item(item, page)[1]
    assert "limit_mismatch" not in ex.check_item(item | {"word_limit": 500}, page)[1]


def test_extraction_write_takes_the_pack_lock_first_so_a_concurrent_user_row_is_not_duplicated(client, app, db):
    """T-200 F1: a user row committed while the extraction waits for the pack lock is seen by its dedupe."""
    import threading
    import time
    from app.tender import extract as extract_mod
    pid = setup_pack(client, [["1. Describe your quality system (maximum 300 words)."]])
    assert client.post(f"/api/packs/{pid}/extract").status_code == 202
    sessions = app.state.db.sessions
    holder = sessions()
    tenant_id = holder.scalar(select(TenderPack.tenant_id).where(TenderPack.id == pid))
    holder.execute(select(TenderPack.id).where(TenderPack.id == pid).with_for_update())  # the user's transaction holds the pack
    worker = threading.Thread(target=lambda: run(app))
    worker.start()
    time.sleep(2.0)  # the extraction has made its (instant) model calls and now waits for the pack row
    assert worker.is_alive(), "the extraction write did not wait for the pack lock"
    holder.add(Requirement(tenant_id=tenant_id, pack_id=pid, seq=1, ref="1", kind="question", origin="user",
                           text="Describe your quality system (maximum 300 words).", source_page=1, status="proposed"))
    holder.commit()
    holder.close()
    worker.join(timeout=30)
    assert not worker.is_alive()
    db.expire_all()
    rows = list(db.scalars(select(Requirement).where(Requirement.pack_id == pid)))
    assert len(rows) == 1 and rows[0].origin == "user"  # no duplicate proposal beside the user's row


def test_a_bidder_addressed_heading_with_a_bracketed_limit_and_a_body_paragraph_is_a_heading():
    """T-207 (a): "How you will deliver ..." says you, so the question-verb rule used to refuse it."""
    q = "Describe the social value you will deliver."
    assert ex.stated_word_limit("How you will deliver social value (max 300 words)\n\n" + q, q) == 300
    assert ex.stated_word_limit("What we need from you (max 300 words)\n\nDescribe your mobilisation plan.",
                                "Describe your mobilisation plan.") == 300
    # still not borrowed: the previous question's limit not in brackets, or a sentence ending in a full stop
    assert ex.stated_word_limit("Describe your approach in no more than 200 words\n\nDescribe your staffing plan.",
                                "Describe your staffing plan.") is None
    assert ex.stated_word_limit("Tell us about you (max 300 words).\n\nDescribe your staffing plan.",
                                "Describe your staffing plan.") is None
    # a bracket with no word limit is not a heading
    assert ex.stated_word_limit("How you will deliver (see appendix 3)\n\nDescribe your staffing plan.",
                                "Describe your staffing plan.") is None


def test_known_limit_cases_hold():
    """The cases in eval/extraction_known_limits.json (EVAL.md "Known limits") say what the rule does today."""
    import json
    from pathlib import Path
    f = Path(__file__).resolve().parents[3] / "eval" / "extraction_known_limits.json"
    cases = json.loads(f.read_text())["cases"]
    assert len(cases) >= 4
    for c in cases:
        assert ex.stated_word_limit(c["page"], c["quote"]) == c["expected_today"], c["id"]
        if c["status"] == "fixed":
            assert c["expected_today"] == c["ideal"], c["id"]
