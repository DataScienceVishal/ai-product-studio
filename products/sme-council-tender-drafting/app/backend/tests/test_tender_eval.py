"""S9 (T-193): eval harness. Scorers on hand-built fixtures with known answers, mutation checks on them, ledger refusal and
worst-case charging, LedgerBudget never touching ai_usage, the sampler, the seed script and the dry-run driver.
No model is called anywhere: every provider here is ScriptedFakeAI."""
import ast
import json
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

PRODUCT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PRODUCT))

from eval import ledger as L, run as R, sample as S, score as SC, seed as SD  # noqa: E402

from app.models import AIUsage, Tenant  # noqa: E402
from app.tender.scripted_ai import ScriptedFakeAI  # noqa: E402
from . import tender_files as tf  # noqa: E402
from .conftest import sign_up  # noqa: E402

QUESTIONS = """## Q-19 (status: answered A 2026-11-27T19:37:41Z via "1A"; was sent)
- Decision: x
## Q-20 (status: sent 2026-11-27)
- Decision: y
"""


@pytest.fixture
def cfg(tmp_path):
    q = tmp_path / "QUESTIONS.md"
    q.write_text(QUESTIONS)
    return L.load_budget_config(L.DEFAULT_CONFIG, q)


def led(tmp_path, cfg, dry=False):
    return L.Ledger(tmp_path / "ledger.jsonl", cfg, dry_run=dry)


# ---------- budget.json and the approving question ----------

def test_committed_budget_matches_q19(cfg):
    assert (cfg.approved_by, cfg.model, cfg.total_cap, cfg.headroom) == ("Q-19", "gpt-5-mini", 6.0, 0)
    assert cfg.group_caps == {"tuning": 2.0, "scored": 2.6, "recording": 1.4}
    assert [cfg.group_of(p) for p in ("T1", "E3", "R2")] == ["tuning", "scored", "recording"]
    assert cfg.scored_preflight_worst == 2.54


def test_committed_budget_loads_against_the_real_questions_file():
    assert L.load_budget_config().approved_by == "Q-19"  # state/QUESTIONS.md has Q-19 answered A


@pytest.mark.parametrize("text", ["## Q-20 (status: answered A x)\n", "## Q-19 (status: sent 2026)\n",
                                  "## Q-19 (status: answered B 2026)\n", ""])
def test_config_refused_unless_question_answered_a(tmp_path, text):
    q = tmp_path / "Q.md"
    q.write_text(text)
    with pytest.raises(L.BudgetConfigError):
        L.load_budget_config(L.DEFAULT_CONFIG, q)


def test_config_refuses_bad_caps_and_headroom(tmp_path):
    q = tmp_path / "Q.md"
    q.write_text(QUESTIONS)
    base = json.loads(L.DEFAULT_CONFIG.read_text())
    for mutate in (lambda c: c.update(reasoning_headroom=1500), lambda c: c["groups"]["scored"].update(cap_usd=5.0),
                   lambda c: c.update(total_cap_usd=float("nan")), lambda c: c.pop("approved_by")):
        c = json.loads(json.dumps(base))
        mutate(c)
        p = tmp_path / "b.json"
        p.write_text(json.dumps(c))
        with pytest.raises(L.BudgetConfigError):
            L.load_budget_config(p, q)


# ---------- ledger: refusal and worst-case charging ----------

def test_worst_usd_never_below_the_true_worst_case(cfg, tmp_path):
    for tokens_in, cap in ((9_000, 6_000), (500, 4_000), (30_000, 1_500), (0, 6_000)):
        b = L.LedgerBudget(led(tmp_path, cfg), "E1", "extract", cap)
        true_worst = tokens_in * 0.25 / 1e6 + cap * 2.0 / 1e6
        true_worst_doubled = tokens_in * 0.25 / 1e6 + 2 * cap * 2.0 / 1e6
        assert b.worst_usd(tokens_in + cap) >= true_worst - 1e-12
        assert b.worst_usd(tokens_in + 2 * cap) >= true_worst_doubled - 1e-12


def test_call_refused_when_it_could_pass_the_group_cap(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "T1", "draft", 4000)
    ledger.append({"phase": "T1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 995_000})  # $1.99
    with pytest.raises(L.BudgetExceeded, match="tuning sub-cap"):
        b.hold(8_000)              # worst $0.016 on $0.01 left
    b2 = L.LedgerBudget(ledger, "T1", "draft", 100)
    assert b2.hold(200) == 1       # a small one still fits


def test_total_cap_is_enforced_across_groups(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    for phase, out in (("T1", 950_000), ("E1", 1_250_000), ("R1", 650_000)):   # 1.9 + 2.5 + 1.3 = 5.7
        ledger.append({"phase": phase, "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": out})
    assert abs(ledger.spent() - 5.7) < 1e-9
    with pytest.raises(L.BudgetExceeded):
        L.LedgerBudget(ledger, "R1", "x", 100_000).hold(200_000)   # worst $0.40 > R1's $0.10 left and the total's $0.30


def test_failed_call_with_no_tokens_is_charged_the_worst_case(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "E2", "draft", 4000)
    h = b.hold(10_000)
    worst = b.worst_usd(10_000)
    b.settle(h, 0, 0, "unknown", failed=True)          # a 5xx or reset after send
    (row,) = ledger.rows()
    assert row["charged_worst"] and row["failed"]
    assert abs(ledger.spent() - worst) < 1e-6
    h = b.hold(10_000)
    b.settle(h, 700, 300, "gpt-5-mini")                 # a normal call is charged what it used
    assert not ledger.rows()[1]["charged_worst"]


def test_spend_is_recomputed_from_tokens_not_the_stored_usd(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "E1", "extract", 6000)
    b.settle(b.hold(8000), 1_000_000, 0, "gpt-5-mini")
    text = ledger.path.read_text().replace('"usd": 0.25', '"usd": 0.0')   # tamper with the informational field
    ledger.path.write_text(text)
    assert abs(ledger.spent("scored") - 0.25) < 1e-9


def test_other_model_stops_the_run_but_is_still_recorded(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "E1", "extract", 6000)
    with pytest.raises(L.ModelMismatch):
        b.settle(b.hold(8000), 1000, 1000, "gpt-5.4-pro")
    assert ledger.spent() > 0
    b.settle(b.hold(8000), 10, 10, "gpt-5-mini-2025-08-07")    # a dated gpt-5-mini name is fine


def test_scored_preflight(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    L.preflight_scored(ledger)                                   # $2.60 free >= $2.54
    ledger.append({"phase": "E1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 40_000})   # $0.08
    with pytest.raises(L.BudgetExceeded):
        L.preflight_scored(ledger)                               # $2.52 left < $2.54
    L.preflight_scored(led(tmp_path / "dry", cfg, dry=True))     # a dry run spends nothing


def test_unknown_phase_is_a_config_error(cfg, tmp_path):
    with pytest.raises(L.BudgetConfigError):
        L.LedgerBudget(led(tmp_path, cfg), "E9", "x", 100)


def test_ledger_module_does_not_import_the_app():
    tree = ast.parse((PRODUCT / "eval" / "ledger.py").read_text())
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + \
           [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not [m for m in mods if m == "app" or m.startswith("app.")]


def test_ledger_budget_never_writes_ai_usage_or_calls_reserve(app, cfg, tmp_path, monkeypatch):
    import app.tender.llm as llm
    from app.tender import draft as dr
    c = app  # the FastAPI app: only its database is used
    sessions = c.state.db.sessions
    with sessions() as db:
        t = Tenant(name="Eval tenant")
        db.add(t); db.commit()
        tenant_id = t.id
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("the app budget path was used"))
    monkeypatch.setattr(llm, "reserve", boom)
    monkeypatch.setattr(llm, "settle", boom)
    ledger = led(tmp_path, cfg, dry=True)
    b = L.LedgerBudget(ledger, "T1", "draft", dr.DRAFT_SPEC.max_output_tokens)
    payload = {"question": "q", "word_limit": "no limit stated", "marks": "not stated", "passages": "[E-1] We hold ISO 9001."}
    res = llm.run_task(dr.DRAFT_SPEC, payload, tenant_id, b, provider=ScriptedFakeAI(), sessions=sessions)
    assert "[E-1]" in res.output.answer
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(AIUsage)) == 0
    assert len(ledger.rows()) == 1 and ledger.rows()[0]["model"] == "fake"


# ---------- scorers: known answers ----------

def q(ref, text, **kw):
    return {"ref": ref, "kind": "question", "text": text, "word_limit": None, "page_limit": None, "marks": None,
            "weight_pct": None, "pass_fail": None, **kw}


def m(ref, text, **kw):
    return q(ref, text, kind="mandatory", **kw)


KEY = [q("1.1", "Describe your approach to mobilisation of the cleaning service", word_limit=500, marks=10),
       q("1.2", "Give two examples of similar contracts you have delivered", word_limit=300),
       q("2.1", "How do you manage staff training and development", marks=5),
       q("2.2", "Explain your environmental policy and how it is audited", word_limit=250),
       q("3.1", "Provide your safeguarding arrangements for vulnerable service users"),
       m("M1", "Bidders must hold public liability insurance of at least five million pounds"),
       m("M2", "Bidders must confirm they pay the real living wage")]
GOT = [q("1.1", "Describe your approach to mobilisation of the cleaning service", word_limit=500, marks=10),   # exact
       q("Q2", "Give two examples of similar contracts that you have delivered", word_limit=350),           # text match, wrong limit
       q("2.1", "How do you manage staff training and development", marks=5),                                # exact
       q("3.1", "Safeguarding"),                                                                             # matched by ref only
       q("9.9", "Please state your registered company number"),                                              # extra (precision)
       m("M1", "Bidders must hold public liability insurance of at least five million pounds", pass_fail=True),
       q("M2", "Bidders must confirm they pay the real living wage")]                                        # mandatory shown optional


def extraction():
    return SC.score_extraction([{"pack": "P", "key": KEY, "got": GOT}])


def traceability():
    drafts = [{"id": "d1", "text": "We hold ISO 9001 [E-1]. We cleaned 40 sites [E-2]. [NEEDS FIRM INPUT: ISO 14001]",
               "retrieved_ids": [1, 2, 3], "live_ids": [1, 2, 3]},
              {"id": "d2", "text": "We employ 102 staff. Our turnover is high [E-9]. Quality is audited [E-3].",
               "retrieved_ids": [3], "live_ids": [3]}]
    return SC.score_traceability(drafts)    # 5 claims; 3 resolve (d2: one uncited, one outside the set)


SEEDED = [{"id": "S1", "draft": "d1", "type": "number", "span": "We employ 250 staff"},
          {"id": "S2", "draft": "d1", "type": "client", "span": "We served Northgate Council"},
          {"id": "S3", "draft": "d2", "type": "accreditation", "span": "We hold ISO 14001"},
          {"id": "S4", "draft": "d2", "type": "date", "span": "Founded in 1990"}]
CHECKED = [{"draft": "d1", "span": "We employ 250 staff.", "verdict": "contradicted"},     # caught
           {"draft": "d1", "span": "We served Northgate Council", "verdict": "supported"},      # miss: judged supported
           {"draft": "d2", "span": "We hold ISO 14001", "verdict": "unchecked"},                # miss: unchecked is not a catch
           {"draft": "d1", "span": "Founded in 1990", "verdict": "unsupported"}]                # right verdict, wrong draft: miss


def known_answer_failures() -> list[str]:
    """The scorer fixtures as one function returning what is wrong, so a mutant scorer can be shown to fail it."""
    f = []
    e = extraction()
    if (e["A1"]["matched"], e["A1"]["key"], e["A1"]["extracted"]) != (4, 5, 6):  # M2 was extracted as a question: an extra, so 5
        f.append("A1 counts")
    if abs(e["A1"]["recall"] - 0.8) > 1e-9 or abs(e["A1"]["precision"] - 4 / 6) > 1e-9 or e["A1"]["pass"]:
        f.append("A1 ratios")
    if [x["ref"] for x in e["A1"]["missed"]] != ["2.2"]:
        f.append("A1 missed")
    # stated fields among matched: 1.1 word 500 + marks 10 ok; 1.2 word 300 vs 350 wrong; 2.1 marks 5 ok -> 3 of 4
    if (e["A2"]["stated"], e["A2"]["correct"]) != (4, 3) or e["A2"]["wrong"][0]["field"] != "word_limit":
        f.append("A2")
    if (e["A3"]["key"], e["A3"]["found"]) != (2, 1) or e["A3"]["shown_optional"] != [{"pack": "P", "ref": "M2"}] or e["A3"]["pass"]:
        f.append("A3")
    t = traceability()
    if (t["claims"], t["resolved"]) != (5, 3) or t["failures"][0]["draft"] != "d2" or t["pass"]:
        f.append("A4")
    if SC.count_words("Ten words [E-1] and [E-22] here [NEEDS FIRM INPUT: x y]") != 9:
        f.append("word rule")
    w = SC.score_word_limits([{"id": "a", "text": "one two three", "word_limit": 3},
                              {"id": "b", "text": "one two three four [E-1]", "word_limit": 3},
                              {"id": "c", "text": "no limit " * 50, "word_limit": None}])
    if (w["scored"], len(w["over"]), w["pass"]) != (2, 1, False):
        f.append("A7")
    g = SC.score_gaps([{"id": "t1", "text": "[NEEDS FIRM INPUT: no such case study]"}, {"id": "t2", "text": "We did it in 2019."}])
    if (g["with_gap"], g["missing"], g["pass"]) != (1, ["t2"], False):
        f.append("A8")
    s = SC.score_seeded_claims(SEEDED, CHECKED)
    if (s["caught"], s["total"], s["pass"]) != (1, 4, False) or {x["id"] for x in s["misses"]} != {"S2", "S3", "S4"} \
            or s["per_type"]["number"] != {"caught": 1, "total": 1}:
        f.append("A6a")
    return f


def test_scorers_known_answers():
    assert known_answer_failures() == []


def test_a1_passes_at_the_bar_and_pools_across_packs():
    key = [q(str(i), f"question number {i} about topic {'abcdefghij'[i]}") for i in range(10)]
    got = key[:9]            # 9 of 10 found, nothing extra
    r = SC.score_extraction([{"pack": "A", "key": key, "got": got}])["A1"]
    assert (r["recall"], r["precision"], r["pass"]) == (0.9, 1.0, True)
    r2 = SC.score_extraction([{"pack": "A", "key": key, "got": got}, {"pack": "B", "key": key[:2], "got": []}])["A1"]
    assert r2["matched"] == 9 and r2["key"] == 12 and not r2["pass"]


def test_matching_is_one_to_one():
    key = [q("1", "same text here"), q("2", "same text here")]
    pairs = SC.match_items(key, [q("x", "same text here")])
    assert len(pairs) == 1


def test_a4_and_a6a_bars_at_threshold():
    ok = [{"id": f"d{i}", "text": "A fact [E-1].", "retrieved_ids": [1], "live_ids": [1]} for i in range(19)]
    bad = [{"id": "dx", "text": "No cite.", "retrieved_ids": [1], "live_ids": [1]}]
    assert SC.score_traceability(ok + bad)["pass"]               # 19 of 20 = 95%
    assert not SC.score_traceability(ok[:18] + bad * 2)["pass"]  # 18 of 20
    seeded = [{"id": str(i), "draft": "d", "type": "n", "span": f"seeded claim {i:03d} text"} for i in range(40)]
    checked = [{"draft": "d", "span": f"seeded claim {i:03d} text", "verdict": "unsupported"} for i in range(38)]
    assert SC.score_seeded_claims(seeded, checked)["pass"]       # 38 of 40
    assert not SC.score_seeded_claims(seeded, checked[:37])["pass"]


def test_empty_inputs_never_pass():
    assert not SC.score_traceability([])["pass"] and not SC.score_gaps([])["pass"]
    assert not SC.score_word_limits([])["pass"] and not SC.score_seeded_claims([], [])["pass"]
    assert not SC.score_extraction([{"pack": "A", "key": [], "got": []}])["A1"]["pass"]


# ---------- mutation checks: a deliberately wrong scorer must be caught by the fixtures ----------

def _mutants():
    orig_match, orig_count, orig_sim = SC.match_items, SC.count_words, SC.similarity
    return {
        "refs ignored": ("match_items", lambda k, g, threshold=SC.SIM_THRESHOLD: [
            p for p in orig_match([{**x, "ref": ""} for x in k], [{**x, "ref": ""} for x in g], threshold)]),
        "threshold too loose": ("match_items", lambda k, g, threshold=SC.SIM_THRESHOLD: orig_match(k, g, 0.0)),
        "word count keeps markers": ("count_words", lambda t: len(t.split())),
        "word count drops gap markers": ("count_words", lambda t: orig_count(SC._GAP.sub("", t))),
        "similarity always 1": ("similarity", lambda a, b: 1.0),
        "claims_of keeps gap markers": ("claims_of", lambda t: SC.split_sentences(t)),
        "overlap always true": ("_overlaps", lambda a, b: True),
        "overlap never": ("_overlaps", lambda a, b: False),
    }


@pytest.mark.parametrize("name", list(_mutants()))
def test_mutant_scorer_is_caught(monkeypatch, name):
    attr, fn = _mutants()[name]
    monkeypatch.setattr(SC, attr, fn)
    assert known_answer_failures(), f"mutant {name!r} was not caught by the fixtures"


def test_mutated_bars_are_caught(monkeypatch):
    monkeypatch.setitem(SC.BARS, "A6a", 0.2)       # 1 of 4 would now pass: the fixture must notice
    assert "A6a" in known_answer_failures()
    monkeypatch.setitem(SC.BARS, "A7", 0.4)
    assert "A7" in known_answer_failures()


# ---------- sampler ----------

def _claims(n):
    return [{"id": f"c{i:04d}", "draft": "d", "claim": f"claim {i}", "cited": [i], "passage_text": "p"} for i in range(n)]


def test_sample_fixed_seed_size_and_order_independence():
    cs = _claims(500)
    a = S.sample_claims(cs)
    assert len(a) == 100 and a == S.sample_claims(cs)
    assert a == S.sample_claims(list(reversed(cs)))                     # export order does not matter
    assert [c["id"] for c in a] != [c["id"] for c in S.sample_claims(cs, seed=1)]
    assert [c["id"] for c in a][:3] == [c["id"] for c in sorted(a, key=lambda c: c["id"])][:3]
    assert len({c["id"] for c in a}) == 100


def test_sample_takes_all_when_fewer_and_writes_a_sheet(tmp_path):
    assert len(S.sample_claims(_claims(37))) == 37
    path = tmp_path / "sheet.csv"
    assert S.write_sheet(_claims(150), path) == 100
    lines = path.read_text().splitlines()
    assert lines[0].startswith("claim_id,") and len(lines) == 101 and S.A5_SEED == 20261127


# ---------- seed ----------

def test_seed_fails_clearly_with_no_packs(tmp_path):
    with pytest.raises(SD.SeedError, match="no tender pack files"):
        SD.find_packs(tmp_path)
    with pytest.raises(SD.SeedError, match="no tender pack files"):
        SD.find_packs(tmp_path / "missing")
    (tmp_path / "notes.csv").write_text("x")
    with pytest.raises(SD.SeedError):
        SD.find_packs(tmp_path)


def test_find_packs_uses_manifest_else_first_three(tmp_path):
    for n in "edcba":
        (tmp_path / f"{n}.pdf").write_bytes(b"x")
    assert [p.name for p in SD.find_packs(tmp_path)] == ["a.pdf", "b.pdf", "c.pdf"]
    (tmp_path / "manifest.json").write_text(json.dumps({"demo": ["e.pdf", "d.pdf"]}))
    assert [p.name for p in SD.find_packs(tmp_path)] == ["e.pdf", "d.pdf"]
    (tmp_path / "manifest.json").write_text(json.dumps({"demo": ["nope.pdf"]}))
    with pytest.raises(SD.SeedError, match="nope.pdf"):
        SD.find_packs(tmp_path)


def test_category_for_real_evidence_names():
    assert SD.category_for("20-case-study-eastvale-offices-cleaning.md") == "case_study"
    assert SD.category_for("03-accreditation-summary.md") == "accreditation"
    assert SD.category_for("05-environmental-policy.md") == "policy"


def test_seed_loads_evidence_packs_and_cache(app, new_client, tmp_path):
    c = new_client()
    sign_up(c, company=SD.FIRM)
    sessions = app.state.db.sessions
    with sessions() as db:
        tenant_id = db.scalar(select(Tenant.id).where(Tenant.name == SD.FIRM))
    ev = tmp_path / "ev"; ev.mkdir()
    (ev / "03-accreditation-summary.md").write_text("# Accreditation\nWe hold ISO 9001 certificate CERT-DEMO-0001.\n")
    (ev / "05-environmental-policy.md").write_text("# Environment\nWe recycle waste and cut energy use.\n")
    packs = tmp_path / "packs"; packs.mkdir()
    (packs / "P1.pdf").write_bytes(tf.pdf([["1. Describe your approach (maximum 300 words)"]]))
    rec = tmp_path / "rec" / "draft"; rec.mkdir(parents=True)
    key = "a" * 64
    (rec / f"{key}.json").write_text(json.dumps({"output": {"answer": "x", "gaps": [], "used_ids": []}}))
    out = SD.seed(c, sessions, tenant_id, evidence_dir=ev, packs_dir=packs, recorded_dir=tmp_path / "rec")
    assert out["evidence_documents"] == 2 and out["evidence_passages"] >= 2 and len(out["packs"]) == 1
    assert out["cache_rows"] == 1
    again = SD.seed(c, sessions, tenant_id, evidence_dir=ev, packs_dir=packs, recorded_dir=tmp_path / "rec")
    assert again["cache_rows"] == 1     # re-seeding is safe (conflict ignored)


def test_seed_changes_nothing_when_no_packs(app, new_client, tmp_path):
    c = new_client()
    sign_up(c, company=SD.FIRM)
    with pytest.raises(SD.SeedError):
        SD.seed(c, app.state.db.sessions, uuid.uuid4(), evidence_dir=tmp_path, packs_dir=tmp_path / "none")
    with app.state.db.sessions() as db:
        from app.tender_models import SourceDocument, TenderPack
        assert db.scalar(select(func.count()).select_from(SourceDocument)) == 0
        assert db.scalar(select(func.count()).select_from(TenderPack)) == 0


# ---------- the dry-run driver ----------

@pytest.fixture
def ctx(app, cfg, tmp_path):
    sessions = app.state.db.sessions
    with sessions() as db:
        t = Tenant(name="Harness tenant")
        db.add(t); db.commit()
        tid = t.id
    packs = tmp_path / "packs"; packs.mkdir()
    for n in ("d1.txt", "d2.txt", "d3.txt", "h1.txt", "h2.txt"):
        (packs / n).write_text("x")
    (packs / "manifest.json").write_text(json.dumps({"demo": ["d1.txt", "d2.txt", "d3.txt"], "heldout": ["h1.txt", "h2.txt"]}))
    pages = [(1, "[page 1]\n1. Describe your approach to mobilisation (maximum 400 words)\n2. Tell us about training"),
             (2, "3. Explain your environmental policy")]
    return R.Context(ScriptedFakeAI(), led(tmp_path, cfg, dry=True), sessions, tid, load_pack=lambda name: pages,
                     keys_dir=tmp_path / "keys", results_dir=tmp_path / "results", packs_dir=packs)


def test_phase_table_matches_the_budget_groups(cfg):
    assert set(R.PHASES) == set(cfg.phase_group)
    assert all(cfg.phase_group[n] == p.group for n, p in R.PHASES.items())
    assert round(sum(p.worst_usd for p in R.PHASES.values() if p.group == "scored"), 2) == 2.54


def test_dry_run_extraction_records_to_the_ledger_and_resumes(ctx):
    r = R.run_phase("E1", ctx)
    assert (r["planned"], r["ran"], r["skipped"], r["dry_run"]) == (2, 2, 0, True)
    rows = [json.loads(l) for l in (ctx.results_dir / "E1.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and len(rows[0]["result"]["items"]) == 3
    assert {x["model"] for x in ctx.ledger.rows()} == {"fake"} and ctx.ledger.spent() == 0.0
    r2 = R.run_phase("E1", ctx)
    assert (r2["ran"], r2["skipped"]) == (0, 2)


def test_phase_without_inputs_says_what_is_missing(ctx):
    with pytest.raises(R.PhaseNotReady, match="trap set"):
        R.run_phase("E3", ctx)
    with pytest.raises(R.PhaseNotReady, match="answer key"):
        R.run_phase("E2", ctx)
    with pytest.raises(R.PhaseNotReady, match="fixture drafts"):
        R.run_phase("E4", ctx)
    with pytest.raises(R.PhaseNotReady, match="unknown phase"):
        R.run_phase("E9", ctx)


def test_check_phase_needs_a_claimcheck(ctx):
    ctx.keys_dir.mkdir()
    (ctx.keys_dir / "fixture_drafts.json").write_text(json.dumps([{"id": "f1", "text": "We hold ISO 9001 [E-1]."}]))
    with pytest.raises(R.PhaseNotReady, match="claim check"):
        R.run_phase("E4", ctx)
    ctx.claimcheck = lambda budget, text, hits: [{"span": "We hold ISO 9001", "verdict": "supported"}]
    assert R.run_phase("E4", ctx)["ran"] == 1


def test_draft_phase_runs_through_the_ledger_on_the_fake(ctx):
    ctx.keys_dir.mkdir()
    (ctx.keys_dir / "dev_trap_set.json").write_text(json.dumps([{"id": "t1", "question": "Do you hold ISO 14001?", "word_limit": 50}]))
    ctx.retrieve = lambda question: []                       # nothing found: the gap path, no model call
    r = R.run_phase("T3", ctx)
    assert r["planned"] == 3 and r["ran"] == 3
    row = json.loads((ctx.results_dir / "T3.jsonl").read_text().splitlines()[0])["result"]
    assert "NEEDS FIRM INPUT" in row["text"] and ctx.ledger.rows() == []


def test_a_refused_hold_stops_the_phase_cleanly(ctx, cfg, tmp_path):
    live = L.Ledger(tmp_path / "live.jsonl", cfg, dry_run=False)
    live.append({"phase": "T1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 999_000})
    ctx.ledger = live
    r = R.run_phase("T1", ctx)
    assert r["stopped"] and "tuning sub-cap" in r["stopped"] and r["ran"] == 0
    with pytest.raises(L.BudgetExceeded):                    # the scored preflight refuses before E1 starts
        R.run_phase("E1", R.Context(ctx.provider, L.Ledger(tmp_path / "l2.jsonl", cfg), ctx.sessions, ctx.tenant_id,
                                    load_pack=ctx.load_pack, packs_dir=ctx.packs_dir, results_dir=ctx.results_dir)
                    if (live.path.with_name("l2.jsonl").write_text(json.dumps(
                        {"phase": "E1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 50_000}) + "\n") or True)
                    else None)


def test_live_is_refused_and_nothing_defaults_to_live(capsys):
    assert R.main(["E1", "--live"]) == 3
    assert "not enabled" in capsys.readouterr().err
    src = (PRODUCT / "eval" / "run.py").read_text()
    assert "AzureOpenAI" not in src and "build_provider" not in src      # no live provider is even constructed


def test_run_configuration_has_prompt_hashes():
    cfg = R.run_configuration()
    assert cfg["model"] == "gpt-5-mini" and cfg["reasoning_headroom"] == 0
    assert all(len(v["sha256"]) == 64 for v in cfg["prompts"].values())
