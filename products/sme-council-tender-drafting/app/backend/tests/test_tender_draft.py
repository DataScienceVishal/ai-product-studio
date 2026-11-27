"""S5: drafting on ScriptedFakeAI: gap path (no model call), citations vs the retrieved set, word-limit retry then
sentence drop, versioning on edit, redraft limits, cross-tenant 404s, and the app-path pair sizing (R3)."""
import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.ai import AIResult
from app.models import AIUsage
from app.tender import draft as dr
from app.tender import runner
from app.tender.scripted_ai import ScriptedFakeAI
from app.tender_models import AITask, Draft

from .conftest import sign_up
from .tender_files import pdf
from .test_tender_ingest import make_pack, tender_url, up

LEASE = timedelta(minutes=10)
EVIDENCE = ("Our cleaning teams are trained to BICSc standards and hold ISO 9001 certification across all sites. "
            "We have delivered cleaning for forty schools since 2019.\n\n")


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


def run(app, provider=None):
    return runner.run_one(app.state.db.sessions, LEASE, provider=provider or ScriptedFakeAI())


class Tweak(ScriptedFakeAI):
    """Heuristic answer changed by fn(data, user_text); counts calls."""
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def complete(self, system, user, max_output_tokens=1200, *, json_schema=None, effort=None):
        res = super().complete(system, user, max_output_tokens, json_schema=json_schema, effort=effort)
        return AIResult(json.dumps(self.fn(json.loads(res.text), user)), res.input_tokens, res.output_tokens, res.model)


def confirmed_pack(client, app, question="1. Describe your cleaning quality system and accreditations (maximum 300 words).",
                   evidence=True):
    pid = make_pack(client)
    assert up(client, tender_url(pid), pdf([[question]])).status_code == 201
    if evidence:
        r = up(client, "/api/evidence/documents", (EVIDENCE * 3).encode(), "quality.txt", category="policy")
        assert r.status_code == 201, r.text
    client.post(f"/api/packs/{pid}/extract")
    run(app)
    assert client.post(f"/api/packs/{pid}/confirm").status_code == 200
    rid = client.get(f"/api/packs/{pid}/requirements").json()["requirements"][0]["id"]
    return pid, rid


def draft_now(client, app, pid, provider=None):
    r = client.post(f"/api/packs/{pid}/draft")
    assert r.status_code == 202, r.text
    run(app, provider)


def latest(client, rid):
    return client.get(f"/api/requirements/{rid}/draft").json()


def test_empty_retrieval_writes_a_gap_marker_and_never_calls_the_model(client, app, db):
    pid, rid = confirmed_pack(client, app, "1. Describe your wind turbine maintenance regime.", evidence=False)
    assert client.get(f"/api/requirements/{rid}/evidence").json() == {"results": [], "message": "No evidence found"}

    class Boom(ScriptedFakeAI):
        def complete(self, *a, **k):
            raise AssertionError("the model must not be called")
    draft_now(client, app, pid, Boom())
    d = latest(client, rid)["draft"]
    assert d["text"] == dr.GAP_TEXT and d["gap_count"] == 1 and d["flags"] == ["no_evidence"] and d["model"] is None
    assert d["version"] == 1 and d["retrieved_ids"] == [] and d["cited_ids"] == []
    assert not list(db.scalars(select(AIUsage).where(AIUsage.feature.like("draft%"))))
    t = db.scalar(select(AITask).where(AITask.kind == "draft"))
    assert t.status == "done"


def test_a_draft_cites_the_retrieved_passages(client, app):
    pid, rid = confirmed_pack(client, app)
    found = client.get(f"/api/requirements/{rid}/evidence").json()["results"]
    assert found
    draft_now(client, app, pid)
    d = latest(client, rid)["draft"]
    assert d["author"] == "ai" and d["outside_ids"] == [] and d["cited_ids"] and set(d["cited_ids"]) <= set(d["retrieved_ids"])
    assert d["word_limit"] == 300 and "[E-" in d["text"] and d["status"] == "drafted"


def test_a_citation_outside_the_retrieved_set_is_flagged(client, app):
    pid, rid = confirmed_pack(client, app)

    def bad(d, user):
        d["answer"] += " We also hold ISO 14001 [E-999]."
        return d
    draft_now(client, app, pid, Tweak(bad))
    d = latest(client, rid)["draft"]
    assert d["outside_ids"] == [999] and "citation_outside_set" in d["flags"] and 999 not in d["cited_ids"]
    assert "[E-999]" in d["text"]  # kept visible; the claim check (S6) marks it unsupported


def long_answer(n):
    return " ".join(f"Sentence number {i} says something about cleaning standards." for i in range(n)) + " [E-1]"


def test_an_over_limit_answer_is_shortened_by_one_retry(client, app):
    pid, rid = confirmed_pack(client, app)
    calls = []

    def fn(d, user):
        calls.append("previous_answer" in user)
        d["answer"] = long_answer(80) if len(calls) == 1 else "A short answer about BICSc training [E-1]."
        return d
    draft_now(client, app, pid, Tweak(fn))
    d = latest(client, rid)["draft"]
    assert calls == [False, True] and d["word_count"] <= 300 and d["flags"] == ["shortened"]


def test_an_answer_still_over_the_limit_after_the_retry_is_cut_by_sentence(client, app):
    pid, rid = confirmed_pack(client, app)
    calls = []

    def fn(d, user):
        calls.append(1)
        d["answer"] = long_answer(80)  # 80 sentences x 8 words = 640 words, both times
        return d
    draft_now(client, app, pid, Tweak(fn))
    d = latest(client, rid)["draft"]
    assert len(calls) == 2 and d["word_count"] <= 300 and "trimmed" in d["flags"]
    assert d["text"].rstrip().endswith(".")  # whole sentences only


def test_fit_to_limit_edge_cases():
    assert dr.count_words("Hello world [E-12] again [E-3].") == 3
    assert dr.count_words(dr.fit_to_limit("One two three four. Five six seven eight. Nine ten.", 6)) <= 6
    one = dr.fit_to_limit("alpha beta gamma delta epsilon zeta eta theta", 3)
    assert one == "alpha beta gamma"
    gap = "Intro words here. [NEEDS FIRM INPUT: a case study. Please add one] Tail."
    cut = dr.fit_to_limit(gap, 4)
    assert cut == "Intro words here." and dr.fit_to_limit("x [NEEDS FIRM INPUT: abc def", 2) == "x"
    assert dr.split_sentences("Facts here. [E-4] More facts. [E-5]") == ["Facts here. [E-4]", "More facts. [E-5]"]


def test_user_edit_makes_a_new_version_and_keeps_the_old(client, app, new_client):
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    r = client.put(f"/api/requirements/{rid}/draft", json={"text": "My own words [E-1] and [E-77].", "base_version": 1})
    assert r.status_code == 201 and r.json()["version"] == 2 and r.json()["author"] == "user"
    body = latest(client, rid)
    assert [v["version"] for v in body["versions"]] == [2, 1] and body["draft"]["version"] == 2
    assert 77 in body["draft"]["outside_ids"]
    assert client.get(f"/api/requirements/{rid}/draft?version=1").json()["draft"]["author"] == "ai"
    assert client.get(f"/api/requirements/{rid}/draft?version=9").status_code == 404
    stale = client.put(f"/api/requirements/{rid}/draft", json={"text": "x", "base_version": 1})
    assert stale.status_code == 409 and "stale_version" in stale.text
    assert client.put(f"/api/requirements/{rid}/draft", json={"text": ""}).status_code == 422


def test_draft_is_idempotent_and_does_not_redo_drafted_questions(client, app, db):
    pid, rid = confirmed_pack(client, app)
    a = client.post(f"/api/packs/{pid}/draft")
    b = client.post(f"/api/packs/{pid}/draft")
    assert a.status_code == b.status_code == 202 and a.json()["id"] == b.json()["id"]
    run(app)
    assert client.post(f"/api/packs/{pid}/draft").status_code == 409  # nothing left to draft
    assert len(latest(client, rid)["versions"]) == 1


def test_draft_needs_a_confirmed_checklist(client):
    pid = make_pack(client)
    assert client.post(f"/api/packs/{pid}/draft").status_code == 409


def test_redraft_makes_version_2_and_is_limited_to_5_a_day(client, app, db):
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    for n in range(2, 6):
        assert client.post(f"/api/requirements/{rid}/redraft").status_code == 202
        run(app)
    assert latest(client, rid)["draft"]["version"] == 5
    r = client.post(f"/api/requirements/{rid}/redraft")
    assert r.status_code == 429


def test_redraft_of_a_non_question_is_409(client, app):
    pid, rid = confirmed_pack(client, app)
    r = client.post(f"/api/packs/{pid}/requirements", json={"text": "Provide insurance", "kind": "mandatory"})
    assert client.post(f"/api/requirements/{r.json()['id']}/redraft").status_code == 409


def test_cross_tenant_ids_are_404(client, app, new_client):
    pid, rid = confirmed_pack(client, app)
    draft_now(client, app, pid)
    other = new_client()
    sign_up(other, email="b@b.test", company="B Ltd")
    assert other.post(f"/api/packs/{pid}/draft").status_code == 404
    assert other.post(f"/api/requirements/{rid}/redraft").status_code == 404
    assert other.get(f"/api/requirements/{rid}/draft").status_code == 404
    assert other.put(f"/api/requirements/{rid}/draft", json={"text": "x"}).status_code == 404
    assert other.get(f"/api/requirements/{rid}/evidence").status_code == 404


def test_retrieval_is_tenant_scoped_for_drafting(client, app, new_client):
    """B's evidence is never in A's draft: A has none, so A's draft is the gap marker."""
    other = new_client()
    sign_up(other, email="b@b.test", company="B Ltd")
    assert up(other, "/api/evidence/documents", (EVIDENCE * 3).encode(), "quality.txt", category="policy").status_code == 201
    pid, rid = confirmed_pack(client, app, evidence=False)
    draft_now(client, app, pid)
    assert latest(client, rid)["draft"]["text"] == dr.GAP_TEXT


# ---------- R3: the app path must fit a trial tenant's 30k a day ----------
class AzureLike(ScriptedFakeAI):
    name = "azure"
    output_headroom = 1500


def _hits(n, chars):
    from app.tender.evidence import Hit
    import uuid
    return [Hit(uuid.uuid4(), i, uuid.uuid4(), "doc.pdf", 1, 1, "Heading", ("word " * chars)[:chars], 1.0, 1.0)
            for i in range(1, n + 1)]


def test_a_typical_draft_and_check_pair_reserves_at_most_30k():
    provider = AzureLike()
    typical = dr.draft_payload("Describe your quality system. " * 12, 300, 10, _hits(5, 900), dr.Limits())
    answer = "Our teams are trained to BICSc standards and hold ISO 9001 [E-1]. " * 25  # about 300 words
    cited = dr.passage_block(_hits(4, 900), dr.Limits())
    d, c = dr.draft_reservation(provider, typical), dr.check_reservation(provider, answer, cited)
    assert d + c <= 30_000, (d, c)


def test_a_typical_draft_shorten_retry_and_check_stay_within_30k():
    """R3: the shorten retry re-sends only the prior answer and caps its output, so all three fit one trial day."""
    provider = AzureLike()
    typical = dr.draft_payload("Describe your quality system. " * 12, 300, 10, _hits(5, 900), dr.Limits())
    over = "Our teams are trained to BICSc standards and hold ISO 9001 [E-1]. " * 40  # about 480 words, over the limit
    short = "Our teams are trained to BICSc standards and hold ISO 9001 [E-1]. " * 25
    cited = dr.passage_block(_hits(4, 900), dr.Limits())
    # A reservation is released when the call settles at actual use, so at each step the day's settled use plus the
    # next reservation must fit. A typical answer settles at its input plus about 600 output tokens.
    typical_out = 600
    d = dr.draft_reservation(provider, typical)
    d_used = d - dr.DRAFT_SPEC.max_output_tokens - int(provider.output_headroom) + typical_out
    r = dr.shorten_reservation(provider, over, 300)
    r_used = r - dr.SHORTEN_SPEC.max_output_tokens - int(provider.output_headroom) + typical_out
    c = dr.check_reservation(provider, short, cited)
    assert d <= 30_000 and d_used + r <= 30_000 and d_used + r_used + c <= 30_000, (d, d_used, r, r_used, c)
    assert r < 0.6 * d  # the retry is a small call, not a second full draft


def test_the_shorten_instruction_is_not_inside_a_data_block(client, app):
    """The model is told to ignore DATA blocks, so the retry's instruction must be in the system prompt."""
    pid, rid = confirmed_pack(client, app)
    seen = []

    class Spy(ScriptedFakeAI):
        def complete(self, system, user, max_output_tokens=1200, **kw):
            res = super().complete(system, user, max_output_tokens, **kw)
            seen.append((system, user))
            data = json.loads(res.text)
            data["answer"] = long_answer(80) if len(seen) == 1 else "A short answer [E-1]."
            return AIResult(json.dumps(data), res.input_tokens, res.output_tokens, res.model)
    draft_now(client, app, pid, Spy())
    assert len(seen) == 2
    system, user = seen[1]
    assert "shorten" in system.lower() and "word_limit" in system
    assert "shorten" not in user.lower() and "instruction" not in user
    assert "previous_answer:\n<<<DATA-" in user  # the prior draft is data


def test_the_largest_app_path_draft_still_reserves_under_the_daily_cap():
    worst = dr.draft_payload("q" * 9000, 500, 100, _hits(8, 5000), dr.Limits())
    assert len(worst["question"]) == dr.QUESTION_CHARS and worst["passages"].count("[E-") == dr.APP_PASSAGES
    assert dr.draft_reservation(AzureLike(), worst) < 21_500  # DESIGN 4.3: the reservation figure the caps were sized on
    # the harness (S9) may widen the limits
    wide = dr.draft_payload("q", None, None, _hits(8, 1400), dr.Limits(passages=8, passage_chars=1400))
    assert wide["passages"].count("[E-") == 8


def test_app_path_draft_goes_through_the_budget(client, app, db):
    """A settled draft writes an ai_usage row under feature `draft` (the app's caps apply)."""
    pid, rid = confirmed_pack(client, app)

    class Real(ScriptedFakeAI):
        cacheable = True
    draft_now(client, app, pid, Real())
    assert list(db.scalars(select(AIUsage).where(AIUsage.feature == "draft")))


def test_evidence_shows_exactly_what_drafting_used(client, app):
    pid = make_pack(client)
    assert up(client, tender_url(pid), pdf([["1. Describe your cleaning quality system and accreditations (maximum 300 words)."]])).status_code == 201
    for i in range(9):  # more matching documents than the app path passes to the model
        r = up(client, "/api/evidence/documents", (EVIDENCE.replace("forty", f"{40 + i}") * 3).encode(), f"quality{i}.txt",
               category="policy")
        assert r.status_code == 201, r.text
    client.post(f"/api/packs/{pid}/extract")
    run(app)
    assert client.post(f"/api/packs/{pid}/confirm").status_code == 200
    rid = client.get(f"/api/packs/{pid}/requirements").json()["requirements"][0]["id"]
    shown = [x["display_no"] for x in client.get(f"/api/requirements/{rid}/evidence").json()["results"]]
    draft_now(client, app, pid)
    d = latest(client, rid)["draft"]
    assert 0 < len(shown) <= dr.APP_PASSAGES and shown == d["retrieved_ids"]


def test_a_draft_task_does_not_write_to_a_pack_signed_meanwhile(client, app, db):
    pid, rid = confirmed_pack(client, app)
    assert client.post(f"/api/packs/{pid}/draft").status_code == 202
    from app.tender_models import TenderPack
    db.execute(TenderPack.__table__.update().where(TenderPack.id == pid).values(status="signed"))
    db.commit()
    run(app)
    db.expire_all()
    assert not list(db.scalars(select(Draft).where(Draft.requirement_id == rid)))
