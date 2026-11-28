"""S9 (T-193): eval harness. Scorers on hand-built fixtures with known answers, mutation checks on them, ledger refusal and
worst-case charging, LedgerBudget never touching ai_usage, the sampler, the seed script and the dry-run driver.
No model is called anywhere: every provider here is ScriptedFakeAI."""
import ast
import json
import re
from dataclasses import replace as dc_replace
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


def test_config_pins_the_approved_values(tmp_path):
    q = tmp_path / "Q.md"
    q.write_text(QUESTIONS)
    base = json.loads(L.DEFAULT_CONFIG.read_text())
    mutations = [lambda c: c.update(model="gpt-5.4-pro", prices_usd_per_million={"gpt-5.4-pro": {"input": 1, "output": 2}}),
                 lambda c: c["groups"]["scored"].update(cap_usd=float("nan")),
                 lambda c: c["groups"]["tuning"].update(cap_usd=1.0),
                 lambda c: c["prices_usd_per_million"]["gpt-5-mini"].update(input=0),
                 lambda c: c["prices_usd_per_million"]["gpt-5-mini"].update(output=float("nan")),
                 lambda c: c.update(total_cap_usd=7.0)]
    for mutate in mutations:
        c = json.loads(json.dumps(base))
        mutate(c)
        p = tmp_path / "b.json"
        p.write_text(json.dumps(c))
        with pytest.raises(L.BudgetConfigError):
            L.load_budget_config(p, q)


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
    (row,) = [r for r in ledger.rows() if r.get("kind") != "hold"]
    assert row["charged_worst"] and row["failed"]
    assert abs(ledger.spent() - worst) < 1e-6
    h = b.hold(10_000)
    b.settle(h, 700, 300, "gpt-5-mini")                 # a normal call is charged what it used
    assert not [r for r in ledger.rows() if r.get("kind") != "hold"][1]["charged_worst"]


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


SCORED = [(n, p.worst_usd) for n, p in R.PHASES.items() if p.group == "scored"]


def test_scored_preflight_before_e1(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    L.preflight_scored(ledger, "E1", SCORED)                     # $2.60 free >= $2.54
    ledger.append({"phase": "E1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 40_000})   # $0.08
    L.preflight_scored(ledger, "E1", SCORED)                     # resuming E1: its own spend is credited ($2.46 needed, $2.52 left)
    L.preflight_scored(led(tmp_path / "dry", cfg, dry=True), "E1", SCORED)    # a dry run spends nothing


def test_live_ledger_e1_spends_then_e2_preflight_passes(cfg, tmp_path):
    """M1: after E1 has spent $0.25 the old preflight demanded $2.54 free and refused E2 to E4 and an E1 resume."""
    ledger = led(tmp_path, cfg)
    ledger.append({"phase": "E1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 125_000})   # $0.25
    for phase in ("E1", "E2", "E3", "E4"):
        L.preflight_scored(ledger, phase, SCORED)
    ledger.append({"phase": "E2", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 800_000})   # $1.60
    with pytest.raises(L.BudgetExceeded, match="E3"):            # $0.75 left, E3+E4 worst case is $0.92
        L.preflight_scored(ledger, "E3", SCORED)


def test_hold_is_durable_and_counts_at_worst_until_settled(cfg, tmp_path):
    """M6: a hold with no settle (a killed process) is spent at its worst case for a fresh Ledger on the same file."""
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "E2", "draft", 4000)
    h = b.hold(10_000)
    worst = b.worst_usd(10_000)
    fresh = led(tmp_path, cfg)                                   # a new process reading the same file
    assert abs(fresh.spent("scored") - worst) < 1e-9 and abs(fresh.spent() - worst) < 1e-9
    assert [r["kind"] for r in fresh.rows()] == ["hold"]
    b.settle(h, 700, 300, "gpt-5-mini")                          # settled: the real tokens replace the hold
    assert abs(fresh.spent() - (700 * 0.25 + 300 * 2.0) / 1e6) < 1e-9
    assert fresh.rows()[1]["hold_id"] == fresh.rows()[0]["hold_id"]


def test_open_hold_blocks_a_second_call_that_would_pass_the_cap(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "T1", "draft", 450_000)
    b.hold(900_000)                                              # worst $1.80 of the $2.00 tuning cap, never settled
    with pytest.raises(L.BudgetExceeded, match="tuning sub-cap"):
        L.LedgerBudget(led(tmp_path, cfg), "T1", "draft", 150_000).hold(300_000)   # a second process: +$0.60


def test_ledger_holds_are_taken_under_a_file_lock(cfg, tmp_path):
    import threading
    ledger = led(tmp_path, cfg)
    results = []

    def go():
        try:
            results.append(L.LedgerBudget(L.Ledger(ledger.path, cfg), "T1", "x", 300_000).hold(300_000))   # $0.60 each
        except L.BudgetExceeded:
            results.append(None)
    ts = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sum(r is not None for r in results) == 3             # $2.00 cap: three fit, no two racing past it
    assert ledger.spent("tuning") <= 2.0 + 1e-9


def test_live_ledger_does_not_hide_fake_rows(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    ledger.append({"phase": "E1", "task": "x", "model": "fake", "input_tokens": 1_000_000, "output_tokens": 0})
    assert abs(ledger.spent() - 0.25) < 1e-9
    assert led(tmp_path / "d", cfg, dry=True).spent() == 0.0


def test_worst_case_charge_rounds_up(cfg, tmp_path):
    ledger = led(tmp_path, cfg)
    b = L.LedgerBudget(ledger, "E2", "draft", 4000)
    h = b.hold(5_001)
    worst = b.worst_usd(5_001)
    b.settle(h, 0, 0, "unknown", failed=True)
    assert ledger.spent() >= worst - 1e-12


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
       q("3.1", "Provide your safeguarding arrangements"),                                                                                # matched by ref only
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


PARITY_TEXTS = ["We cleaned 40 schools. [E-3] We will deliver - on time [E-3]. We hold [NEEDS FIRM INPUT: ISO 14001 cert. Provide copy]",
                "One. Two! Three? [E-1] [E-2] Four.\nFive - six . seven", "- . \u2013 a [E-1].", ""]


def test_scorer_uses_the_apps_sentence_splitter_and_word_counter():
    from app.tender import draft as dr
    assert SC.split_sentences is dr.split_sentences and SC.count_words is dr.count_words
    for t in PARITY_TEXTS:
        assert SC.split_sentences(t) == dr.split_sentences(t) and SC.count_words(t) == dr.count_words(t)
    assert SC.count_words("one - two . three \u2013 [E-1].") == 3          # punctuation-only tokens are not words (M4)


def test_a4_correct_draft_with_late_citation_and_gap_marker_scores_one():
    """M3: the review's example. Every citation is valid; the old splitter scored it 0.25."""
    text = PARITY_TEXTS[0]
    r = SC.score_traceability([{"id": "d", "text": text, "retrieved_ids": [3], "live_ids": [3]}])
    assert r["claims"] == 2 and r["resolved"] == 2 and r["score"] == 1.0, r
    assert SC.claims_of("We hold [NEEDS FIRM INPUT: ISO 14001 cert. Provide copy]") == []
    assert SC.claims_of("We hold ISO 9001 [E-1] [NEEDS FIRM INPUT: scope]") == ["We hold ISO 9001 [E-1] [NEEDS FIRM INPUT: scope]"]
    assert SC.claims_of("We employ 250 staff.") == ["We employ 250 staff."]       # uncited and no marker: still a claim


def test_a7_word_count_matches_the_app_on_the_review_example():
    text = PARITY_TEXTS[0]
    assert SC.count_words(text) == 19
    assert SC.score_word_limits([{"id": "d", "text": text, "word_limit": 19}])["pass"]


def test_a3_ref_shared_with_a_question_does_not_make_a_mandatory_item_optional():
    key = [m("1.2", "Bidders must hold public liability insurance")]
    got = [q("1.2", "Describe your quality management system"), m("X", "Bidders must hold public liability insurance", pass_fail=True)]
    r = SC.score_extraction([{"pack": "P", "key": key, "got": got}])["A3"]
    assert r["found"] == 1 and not r["shown_optional"]


DRAFT_TEXT = {"d3": "We cleaned 400 schools in 2019. We hold ISO 9001 [E-1]. Our staff are trained.",
              "d4": "We employ 250 staff. We served Northgate Council for six years across the north of the county. "
              "Our turnover is high and our margins are healthy. We operate from three depots and a central office."}


def overlap_failures() -> list[str]:
    f = []
    seed = [{"id": "S5", "draft": "d3", "type": "number", "span": "We cleaned 400 schools in 2019"}]
    if SC.score_seeded_claims(seed, [{"draft": "d3", "span": "in", "verdict": "unsupported"}], DRAFT_TEXT)["caught"] != 0:
        f.append("tiny span caught")
    seeds4 = [{"id": "S6", "draft": "d4", "type": "number", "span": "We employ 250 staff"},
              {"id": "S7", "draft": "d4", "type": "client", "span": "We served Northgate Council"}]
    whole = [{"draft": "d4", "span": DRAFT_TEXT["d4"], "verdict": "unsupported"}]
    if SC.score_seeded_claims(seeds4, whole, DRAFT_TEXT)["caught"] != 0:
        f.append("whole-paragraph span caught")
    exact = [{"draft": "d4", "span": "We employ 250 staff", "verdict": "unsupported"}]
    if SC.score_seeded_claims(seeds4, exact, DRAFT_TEXT)["caught"] != 1:
        f.append("exact span missed")
    sentence = [{"draft": "d3", "span": "We cleaned 400 schools in 2019.", "verdict": "contradicted"}]
    if SC.score_seeded_claims(seed, sentence, DRAFT_TEXT)["caught"] != 1:
        f.append("whole sentence missed")
    flags = SC.score_seeded_claims(seeds4[:1], exact + [{"draft": "d4", "span": "Our turnover is high", "verdict": "unsupported"},
                                                         {"draft": "d4", "span": "Our staff", "verdict": "supported"}], DRAFT_TEXT)
    if flags["false_flags"] != {"flagged": 1, "non_seeded_claims": 2, "rate": 0.5}:
        f.append("false flag rate")
    return f


def test_overlap_rule_tiny_and_whole_paragraph_spans_miss():
    assert overlap_failures() == []


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
    seeded = [{"id": str(i), "draft": "d", "type": "n", "span": f"alpha{i:03d} beta{i:03d} gamma{i:03d}"} for i in range(40)]
    checked = [{"draft": "d", "span": f"alpha{i:03d} beta{i:03d} gamma{i:03d}", "verdict": "unsupported"} for i in range(38)]
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
        "refs ignored": ("match_items", lambda k, g, threshold=SC.SIM_THRESHOLD, **kw: [
            p for p in orig_match([{**x, "ref": ""} for x in k], [{**x, "ref": ""} for x in g], threshold)]),
        "threshold too loose": ("match_items", lambda k, g, threshold=SC.SIM_THRESHOLD, **kw: orig_match(k, g, 0.0, **kw)),
        "word count keeps markers": ("count_words", lambda t: len(t.split())),
        "word count drops gap markers": ("count_words", lambda t: orig_count(SC._GAP.sub("", t))),
        "similarity always 1": ("similarity", lambda a, b: 1.0),
        "claims_of keeps gap markers": ("split_claims", lambda t: (SC.split_sentences(t), [])),
        "overlap always true": ("_overlaps", lambda *a, **k: True),
        "overlap never": ("_overlaps", lambda *a, **k: False),
        "overlap raw substring": ("_overlaps", lambda a, b, sents=(): bool(SC._norm(a)) and bool(SC._norm(b)) and (
            SC._norm(a) in SC._norm(b) or SC._norm(b) in SC._norm(a))),
        "overlap ignores the share rule": ("_overlaps", lambda a, b, sents=(): len(set(SC._tokens(a)) & set(SC._tokens(b))) >= 1),
    }


@pytest.mark.parametrize("name", list(_mutants()))
def test_mutant_scorer_is_caught(monkeypatch, name):
    attr, fn = _mutants()[name]
    monkeypatch.setattr(SC, attr, fn)
    assert known_answer_failures() or overlap_failures(), f"mutant {name!r} was not caught by the fixtures"


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


def test_a5_sample_is_unchanged_by_gap_rows_which_form_a_separate_block(tmp_path):
    drafts = [{"id": "d1", "text": "We hold [NEEDS FIRM INPUT: x]. We hold ISO 9001 [E-1]."},
              {"id": "d2", "text": "Our insurance cover is [NEEDS FIRM INPUT: y]."}]
    gap = S.gap_exempt_rows(drafts)
    assert [g["id"] for g in gap] == ["gap-d1-000", "gap-d2-000"] and all(g["cited"] == [] for g in gap)
    assert S.gap_exempt_rows([{"id": "d", "text": "We are incident-free [NEEDS FIRM INPUT: x]."}]) == []      # now a claim
    assert S.sample_claims(_claims(500)) == S.sample_claims(_claims(500))
    assert len(S.sample_claims(_claims(37))) == 37
    p1, p2 = tmp_path / "a.csv", tmp_path / "b.csv"
    assert S.write_sheet(_claims(500), p1) == 100 and S.write_sheet(_claims(500), p2, gap_exempt=gap) == 100
    plain, with_gap = p1.read_text().splitlines(), p2.read_text().splitlines()
    assert with_gap[:101] == plain and len(with_gap) == 103                  # the 100 cited rows are identical
    assert [r.split(",")[0] for r in with_gap[101:]] == ["gap-d1-000", "gap-d2-000"]
    assert sum(r.startswith("gap-") for r in with_gap[:101]) == 0


@pytest.mark.parametrize("text", ["We won [NEEDS FIRM INPUT: x].", "We are the best [NEEDS FIRM INPUT: x].",
                                  "We are leading [NEEDS FIRM INPUT: x].", "We are trusted [NEEDS FIRM INPUT: x].",
                                  "We are experienced [NEEDS FIRM INPUT: x].", "We cant [NEEDS FIRM INPUT: x]."])
def test_a4_more_sole_word_claims_count(text):
    assert SC.claims_of(text) == [text]


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


def test_find_packs_refuses_empty_manifest_and_path_escape(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    (tmp_path.parent / "outside.pdf").write_bytes(b"x")
    for demo in ([], ["../outside.pdf"]):
        (tmp_path / "manifest.json").write_text(json.dumps({"demo": demo}))
        with pytest.raises(SD.SeedError):
            SD.find_packs(tmp_path)
    (tmp_path / "manifest.json").write_text(json.dumps({}))
    with pytest.raises(SD.SeedError, match="no .demo. packs"):
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
    assert again["packs"] == out["packs"]        # and does not duplicate the pack
    assert len(c.get("/api/packs").json()["packs"]) == 1


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
    for n in ("d1.txt", "d2.txt", "d3.txt", "h1.txt", "h2.txt", "h3.txt"):
        (packs / n).write_text("x")
    (packs / "manifest.json").write_text(json.dumps({"demo": ["d1.txt", "d2.txt", "d3.txt"], "heldout": ["h1.txt", "h2.txt", "h3.txt"],
                                                "drafting_heldout": ["h1.txt", "h2.txt", "h3.txt"]}))
    pages = [(1, "[page 1]\n1. Describe your approach to mobilisation (maximum 400 words)\n2. Tell us about training"),
             (2, "3. Explain your environmental policy")]
    keys = tmp_path / "keys"; keys.mkdir()
    labels = {"packs": {f"d{n}": [{"ref": f"{n}.{k}", "text": f"Demo question {n}.{k}?", "relevant": [1], "primary": [1]}
                                  for k in range(1, 8)] for n in (1, 2, 3)}}      # 7 labelled questions per demo pack
    (keys / "retrieval_labels.json").write_text(json.dumps(labels))
    return R.Context(ScriptedFakeAI(), led(tmp_path, cfg, dry=True), sessions, tid, load_pack=lambda name: pages,
                     retrieve=lambda question: [],          # nothing found: the draft takes the gap path, no model call
                     keys_dir=keys, results_dir=tmp_path / "results", packs_dir=packs)


def test_phase_table_matches_the_budget_groups(cfg):
    assert set(R.PHASES) == set(cfg.phase_group)
    assert all(cfg.phase_group[n] == p.group for n, p in R.PHASES.items())
    assert round(sum(p.worst_usd for p in R.PHASES.values() if p.group == "scored"), 2) == 2.54


def test_dry_run_extraction_records_to_the_ledger_and_resumes(ctx):
    r = R.run_phase("E1", ctx)
    assert (r["planned"], r["ran"], r["skipped"], r["dry_run"]) == (3, 3, 0, True)
    rows = [json.loads(l) for l in (ctx.results_dir / "E1.jsonl").read_text().splitlines()]
    assert len(rows) == 3 and len(rows[0]["result"]["items"]) == 3
    assert {x["model"] for x in ctx.ledger.rows()} == {"fake"} and ctx.ledger.spent() == 0.0
    r2 = R.run_phase("E1", ctx)
    assert (r2["ran"], r2["skipped"]) == (0, 3)


def test_phase_without_inputs_says_what_is_missing(ctx):
    with pytest.raises(R.PhaseNotReady, match="trap set"):
        R.run_phase("E3", ctx)
    with pytest.raises(R.PhaseNotReady, match="answer key"):
        R.run_phase("E2", ctx)
    with pytest.raises(R.PhaseNotReady, match="fixture drafts"):
        R.run_phase("E4", ctx)
    with pytest.raises(R.PhaseNotReady, match="unknown phase"):
        R.run_phase("E9", ctx)


def test_e4_uses_a_passed_claimcheck(ctx):
    ctx.keys_dir.mkdir(exist_ok=True)
    (ctx.keys_dir / "fixture_drafts.json").write_text(json.dumps([{"id": "f1", "text": "We hold ISO 9001 [E-1]."}]))
    ctx.claimcheck = lambda budget, text, hits: [{"span": "We hold ISO 9001", "verdict": "supported"}]
    assert R.run_phase("E4", ctx)["ran"] == 1


def test_check_without_a_claimcheck_says_phase_not_ready(ctx):
    ctx.claimcheck = None                                    # cleared after construction
    with pytest.raises(R.PhaseNotReady, match="claimcheck"):
        R._check(ctx, "E4", "f1", "We hold ISO 9001 [E-1].", [])


def test_replaced_context_rebuilds_the_default_claimcheck_for_the_new_provider(ctx):
    import dataclasses
    assert ctx.claimcheck.is_default_claimcheck
    other = ScriptedFakeAI()
    c2 = dataclasses.replace(ctx, provider=other)
    assert c2.claimcheck is not ctx.claimcheck and c2.claimcheck.is_default_claimcheck
    cells = [c.cell_contents for c in c2.claimcheck.__closure__]
    assert any(c is c2 for c in cells) and not any(c is ctx for c in cells)       # closes over the new context
    custom = lambda budget, text, hits: []
    assert dataclasses.replace(ctx, claimcheck=custom).claimcheck is custom      # a passed callable is kept


def test_draft_phase_runs_through_the_ledger_on_the_fake(ctx):
    ctx.keys_dir.mkdir(exist_ok=True)
    (ctx.keys_dir / "dev_trap_set.json").write_text(json.dumps([{"id": "t1", "question": "Do you hold ISO 14001?", "word_limit": 50}]))
    ctx.retrieve = lambda question: []                       # nothing found: the gap path, no model call
    ctx.claimcheck = lambda budget, text, hits: []
    r = R.run_phase("T3", ctx)
    assert r["planned"] == 3 and r["ran"] == 3
    row = json.loads((ctx.results_dir / "T3.jsonl").read_text().splitlines()[0])["result"]
    assert "NEEDS FIRM INPUT" in row["text"] and ctx.ledger.rows() == []


def live_ctx(ctx, cfg, tmp_path, name="live.jsonl"):
    ctx.ledger = L.Ledger(tmp_path / name, cfg, dry_run=False)
    ctx.dry = False
    return ctx


def test_a_refused_hold_stops_the_phase_cleanly(ctx, cfg, tmp_path):
    live = L.Ledger(tmp_path / "live.jsonl", cfg, dry_run=False)
    live.append({"phase": "T1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 999_000})
    ctx.ledger = live
    r = R.run_phase("T1", ctx)
    assert r["stopped"] and "tuning sub-cap" in r["stopped"] and r["ran"] == 0


def test_scored_preflight_refuses_when_the_reserve_is_short(ctx, cfg, tmp_path):
    live = L.Ledger(tmp_path / "l2.jsonl", cfg)
    live.append({"phase": "E1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 1_000_000})   # $2.00
    ctx.ledger = live
    (tmp_path / "results").mkdir(); (tmp_path / "results" / "E1.jsonl").write_text("")
    with pytest.raises(L.BudgetExceeded):
        R.run_phase("E1", ctx)


def test_live_phase_with_ledger_rows_but_no_results_file_is_refused(ctx, cfg, tmp_path):
    """M2: a fresh clone without the committed results must not re-run (and re-pay for) finished scored items."""
    live_ctx(ctx, cfg, tmp_path)
    ctx.ledger.append({"phase": "T1", "task": "x", "model": "gpt-5-mini", "input_tokens": 100, "output_tokens": 100})
    with pytest.raises(R.PhaseNotReady, match="results are committed"):
        R.run_phase("T1", ctx)
    (ctx.results_dir).mkdir(parents=True, exist_ok=True)
    (ctx.results_dir / "T1.jsonl").write_text("")            # restored (empty): the operator has checked


def test_results_are_committed_and_only_dry_results_ignored():
    ignore = (PRODUCT / "eval" / ".gitignore").read_text().split()
    assert "results/dry/" in ignore and not any(x in ("results/", "results/*.jsonl", "results/*") for x in ignore)
    assert R.DRY_RESULTS_DIR == R.RESULTS_DIR / "dry"


def test_every_context_has_a_claimcheck_so_no_draft_is_recorded_without_claims(ctx):
    """M7 (T-202): with none passed, the real claim check is wired in, so E2, E3, E4 and T3 always record claims."""
    assert callable(ctx.claimcheck)
    custom = lambda budget, text, hits: []
    assert dc_replace(ctx, claimcheck=custom).claimcheck is custom


def test_drafting_heldout_must_be_named_in_the_manifest(ctx):
    assert R.drafting_heldout(ctx) == ["h1.txt", "h2.txt", "h3.txt"]
    m = ctx.packs_dir / "manifest.json"
    base = json.loads(m.read_text())
    for bad in ({"drafting_heldout": ["h1.txt", "h2.txt"]}, {"drafting_heldout": ["h1.txt", "h1.txt", "h2.txt"]},
                {"drafting_heldout": ["h1.txt", "h2.txt", "d1.txt"]}, {"drafting_heldout": None}):
        m.write_text(json.dumps({**base, **bad}))
        with pytest.raises(R.PhaseNotReady):
            R.drafting_heldout(ctx)


def test_context_refuses_a_provider_with_reasoning_headroom(ctx):
    class Reasoning(ScriptedFakeAI):
        output_headroom = 1500
    with pytest.raises(R.PhaseNotReady, match="output_headroom"):
        R.Context(Reasoning(), ctx.ledger, ctx.sessions, ctx.tenant_id)


def test_a_failed_item_is_recorded_and_the_phase_goes_on(ctx, monkeypatch):
    from app.tender.llm import TaskFailed
    calls = []

    def fake_run(c, phase, item):
        calls.append(item.id)
        if len(calls) == 1:
            raise TaskFailed("ai_truncated", "x")
        return {"pack": item.data["pack"], "items": []}
    monkeypatch.setattr(R, "_run_item", fake_run)
    r = R.run_phase("E1", ctx)
    assert (r["ran"], r["failed"], r["stopped"]) == (3, 1, None)
    rows = [json.loads(l)["result"] for l in (ctx.results_dir / "E1.jsonl").read_text().splitlines()]
    assert rows[0] == {"error": "ai_truncated"}


def test_infrastructure_failure_stops_the_phase_without_recording_the_item(ctx, monkeypatch):
    from app.ai import AIUnavailable
    monkeypatch.setattr(R, "_run_item", lambda c, p, i: (_ for _ in ()).throw(AIUnavailable("down")))
    r = R.run_phase("E1", ctx)
    assert r["ran"] == 0 and "AI unavailable" in r["stopped"]
    assert (ctx.results_dir / "E1.jsonl").read_text() == ""


def test_claimcheck_cap_comes_from_the_app_not_a_literal(ctx, monkeypatch):
    from app.tender import draft as dr
    seen = []
    ctx.claimcheck = lambda budget, text, hits: seen.append(budget.output_cap) or []
    R._check(ctx, "E4", "f1", "text", [])
    assert seen == [dr.CHECK_CAP]
    assert "6000" not in (PRODUCT / "eval" / "run.py").read_text()


def test_cache_is_cleared_before_repeat_passes_of_a_cacheable_provider(ctx, monkeypatch):
    from app.tender_models import AICache
    cleared = []
    monkeypatch.setattr(R, "clear_ai_cache", lambda c: cleared.append(1))
    monkeypatch.setattr(R, "_run_item", lambda c, p, i: {})
    R.run_phase("T2", ctx)
    assert not cleared                                       # the fake is not cacheable: nothing to clear
    ctx.provider = type("Live", (ScriptedFakeAI,), {"cacheable": True})()
    (ctx.results_dir / "T2.jsonl").unlink()
    R.run_phase("T2", ctx)
    assert len(cleared) == 27                                # 3 packs x 3 passes x (1 extract + 2 drafts), cleared before every item
    with ctx.sessions() as db:
        R.clear_ai_cache(ctx)
        assert db.scalar(select(func.count()).select_from(AICache).where(AICache.tenant_id == ctx.tenant_id)) == 0


def test_run_refuses_a_non_local_database():
    assert R.local_database("postgresql+psycopg://u:p@localhost:5432/x") and R.local_database("postgresql+psycopg://u:p@127.0.0.1/x")
    assert not R.local_database("postgresql+psycopg://u:p@db.example.azure.com:5432/x")


@pytest.mark.parametrize("phase", ["E1", "E2", "E3", "E4", "R1", "R2", "config", "retrieval"])
def test_live_is_refused_outside_the_tuning_phases(phase, capsys, monkeypatch):
    for k in R.LIVE_ENV:
        monkeypatch.setenv(k, "x")                       # even fully configured, nothing but T1-T3 may go live
    monkeypatch.setattr(R, "build_live_provider", lambda *a, **k: pytest.fail("a provider was built"))
    assert R.main([phase, "--live"]) == 3
    err = capsys.readouterr().err
    assert "L1 configuration freeze" in err and "T1" in err


def test_live_phases_are_exactly_the_tuning_group(cfg):
    assert R.LIVE_PHASES == {n for n, p in R.PHASES.items() if p.group == "tuning"} == {"T1", "T2", "T3"}


def test_live_with_missing_env_makes_no_call_and_exits_nonzero(capsys, monkeypatch):
    for k in R.LIVE_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.invalid")      # one set, two missing
    monkeypatch.setattr(R, "build_live_provider", lambda *a, **k: pytest.fail("a provider was built"))
    assert R.main(["T1", "--live"]) == 6
    err = capsys.readouterr().err
    assert "AZURE_OPENAI_API_KEY" in err and "AZURE_OPENAI_DEPLOYMENT_MINI" in err and "AZURE_OPENAI_ENDPOINT" not in err


def test_missing_live_env_treats_blank_as_missing():
    assert R.missing_live_env({"AZURE_OPENAI_ENDPOINT": "e", "AZURE_OPENAI_API_KEY": "  ", "AZURE_OPENAI_DEPLOYMENT_MINI": "d"}) == \
        ["AZURE_OPENAI_API_KEY"]


def test_live_provider_is_the_apps_client_with_zero_headroom_and_hides_the_key():
    env = {"AZURE_OPENAI_ENDPOINT": "https://example.invalid", "AZURE_OPENAI_API_KEY": "sekrit-key-123",
           "AZURE_OPENAI_DEPLOYMENT_MINI": "mini-dep"}
    p = R.build_live_provider(env)
    from app.ai import AzureOpenAI
    assert isinstance(p, AzureOpenAI) and p.api == "responses" and p.output_headroom == 0 and p.deployment == "mini-dep"
    assert p.retries == R.LIVE_RETRIES and p.timeout == R.LIVE_TIMEOUT_SECONDS
    assert "sekrit-key-123" not in json.dumps(R.run_configuration())
    assert "sekrit" not in (PRODUCT / "eval" / "run.py").read_text()


@pytest.mark.parametrize("phase", ["E1", "E2", "E3", "E4", "R1", "R2"])
def test_run_phase_refuses_a_scored_or_recording_phase_with_a_real_provider(ctx, phase):
    class Real(ScriptedFakeAI):
        name = "azure"
    real = dc_replace(ctx, provider=Real())
    with pytest.raises(R.PhaseNotReady, match="L1 configuration freeze"):
        R.run_phase(phase, real)
    assert real.provider.calls == []


class LiveFake(ScriptedFakeAI):
    """Stands in for the Azure client: not named fake, so every call is priced and held for real."""
    name = "azure"
    recorded_answer = None

    def __init__(self, model="gpt-5-mini-2025-08-07"):
        super().__init__()
        self.model = model

    def complete(self, system, user, max_output_tokens=1200, *, json_schema=None, effort=None):
        r = super().complete(system, user, max_output_tokens, json_schema=json_schema, effort=effort)
        return type(r)(text=r.text, input_tokens=100, output_tokens=50, model=self.model)


def test_live_t1_path_writes_holds_and_settles_to_the_ledger(ctx, cfg, tmp_path):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = LiveFake()
    r = R.run_phase("T1", live)
    assert r["dry_run"] is False and r["ran"] == 6 and r["stopped"] is None
    rows = live.ledger.rows()
    holds = [x for x in rows if x["kind"] == "hold"]
    settles = [x for x in rows if x["kind"] == "settle"]
    assert holds and len(holds) == len(settles)
    assert {x["hold_id"] for x in holds} == {x["hold_id"] for x in settles}          # every hold is closed by its settle
    assert all(x["phase"] == "T1" and x["model"] == "gpt-5-mini" for x in holds)
    assert all(x["model"].startswith("gpt-5-mini") and x["input_tokens"] == 100 and x["usd"] > 0 for x in settles)
    assert live.ledger.spent(phase="T1") == pytest.approx(len(settles) * (100 * 0.25 + 50 * 2.0) / 1e6)
    assert (live.results_dir / "T1.jsonl").exists()


def test_live_wrong_reported_model_stops_the_run(ctx, cfg, tmp_path):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = LiveFake(model="gpt-5.4-pro")
    r = R.run_phase("T1", live)
    assert r["ran"] == 0 and r["model_mismatch"] and "MODEL MISMATCH" in r["stopped"]
    settles = [x for x in live.ledger.rows() if x["kind"] == "settle"]
    assert len(settles) == 1 and settles[0]["usd"] > 0                                  # priced, never hidden
    assert (live.results_dir / "T1.jsonl").read_text() == ""                            # the item was not recorded


@pytest.mark.parametrize("model", ["unknown", "", "gpt-5"])
def test_live_missing_or_other_model_name_stops_the_run(ctx, cfg, tmp_path, model):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = LiveFake(model=model)
    assert R.run_phase("T1", live)["model_mismatch"] is True


def test_live_cap_is_enforced_before_the_call(ctx, cfg, tmp_path):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = LiveFake()
    live.ledger.append({"phase": "T2", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 999_000})
    r = R.run_phase("T1", live)                                                          # tuning group already over its $2.00
    assert r["ran"] == 0 and "tuning sub-cap" in r["stopped"] and live.provider.calls == []


def test_live_total_cap_binds_on_its_own(ctx, cfg, tmp_path):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = LiveFake()
    live.ledger.append({"phase": "E1", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 2_999_500})   # $5.999 (scored over its sub-cap)
    r = R.run_phase("T1", live)                       # tuning is empty, so only the $6.00 total can refuse
    assert r["ran"] == 0 and "total cap" in r["stopped"] and live.provider.calls == []


def test_live_results_missing_with_ledger_rows_is_refused(ctx, cfg, tmp_path):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = LiveFake()
    live.ledger.append({"phase": "T1", "task": "x", "model": "gpt-5-mini", "input_tokens": 1, "output_tokens": 1})
    with pytest.raises(R.PhaseNotReady, match="results"):
        R.run_phase("T1", live)
    assert live.provider.calls == []


def test_live_ledger_and_results_defaults_point_at_the_committed_paths():
    assert R.LIVE_LEDGER == PRODUCT / "eval" / "ledger.jsonl" and R.RESULTS_DIR == PRODUCT / "eval" / "results"


def test_run_configuration_has_prompt_hashes():
    cfg = R.run_configuration()
    assert cfg["model"] == "gpt-5-mini" and cfg["reasoning_headroom"] == 0
    assert all(len(v["sha256"]) == 64 for v in cfg["prompts"].values())


# ---------- T-202 ----------

def test_run_configuration_prints_the_claimcheck_prompt_hash():
    import hashlib
    from app.tender import claimcheck as cc
    c = R.run_configuration()["claimcheck_prompt"]
    (key, v), = c.items()
    assert key.startswith("claimcheck:") and v["sha256"] == hashlib.sha256(cc.CLAIMCHECK_SPEC.system.encode()).hexdigest()
    assert v["output_cap"] == cc.CLAIMCHECK_SPEC.max_output_tokens


def test_e2_drafts_and_records_claims_end_to_end_with_the_real_claimcheck(ctx):
    """T-202: no claimcheck passed, so the default (app.tender.claimcheck.check_draft on ScriptedFakeAI) runs."""
    assert ctx.claimcheck is not None
    ctx.keys_dir.mkdir(exist_ok=True)
    items = [{"ref": "1", "kind": "question", "text": "Describe mobilisation", "word_limit": 100}]
    for n in ("h1", "h2", "h3"):
        (ctx.keys_dir / f"{n}.json").write_text(json.dumps({"items": items if n == "h1" else []}))
    seen = []
    ctx.retrieve = lambda question: []                       # gap path: no model call in draft or check
    orig = ctx.claimcheck
    ctx.claimcheck = lambda budget, text, hits, **kw: seen.append(budget.output_cap) or orig(budget, text, hits, **kw)
    r = R.run_phase("E2", ctx)
    assert r["ran"] == 1 and r["failed"] == 0 and ctx.ledger.spent() == 0.0
    row = json.loads((ctx.results_dir / "E2.jsonl").read_text().splitlines()[0])["result"]
    assert "NEEDS FIRM INPUT" in row["text"] and isinstance(row["claims"], list) and seen


def test_default_claimcheck_calls_the_model_through_the_ledger(ctx, monkeypatch):
    from app.tender.draft import CHECK_CAP
    from app.tender.llm import run_task as real_run
    calls = []
    import app.tender.claimcheck as cc
    monkeypatch.setattr(cc, "run_task", lambda *a, **k: calls.append(a[3].output_cap) or real_run(*a, **k))
    b = L.LedgerBudget(ctx.ledger, "E4", "claimcheck", CHECK_CAP, label="f1")
    claims = ctx.claimcheck(b, "We hold ISO 9001 [E-1].", [])
    assert calls == [CHECK_CAP] and isinstance(claims, list) and claims and claims[0]["verdict"] != "supported"
    assert {"span", "verdict", "cited_ids"} <= set(claims[0])      # dicts for the scorers; E-1 is not retrieved: unsupported


def test_a4_gap_sentence_with_other_factual_content_still_counts():
    mixed = "We have delivered 40 contracts for 12 councils since 2015 and hold [NEEDS FIRM INPUT: insurer] cover."
    claims, exempt = SC.split_claims(mixed)
    assert claims == [mixed] and exempt == []
    r = SC.score_traceability([{"id": "d", "text": mixed, "retrieved_ids": [], "live_ids": []}])
    assert (r["claims"], r["resolved"], r["gap_exempt"]) == (1, 0, 0) and r["failures"][0]["reason"] == "no citation"
    # a digit alone counts; so do three content words, a number word, an acronym or an app fact trigger
    assert SC.claims_of("We [NEEDS FIRM INPUT: x] 40.")
    assert SC.claims_of("Our experienced directors manage large cleaning contracts and [NEEDS FIRM INPUT: x].")
    assert SC.claims_of("We hold [NEEDS FIRM INPUT: x].") == [] and SC.claims_of("Our insurance cover is [NEEDS FIRM INPUT: x].") == []


@pytest.mark.parametrize("text", ["Our team cleaned schools [NEEDS FIRM INPUT: x].",
                                  "We are ISO certified [NEEDS FIRM INPUT: x].",
                                  "We hold Cyber Essentials [NEEDS FIRM INPUT: x].",
                                  "We have had zero RIDDOR incidents [NEEDS FIRM INPUT: x].",
                                  "We clean forty schools [NEEDS FIRM INPUT: x].",
                                  "We hold ISO 9001 [NEEDS FIRM INPUT: x].",
                                  "We hold ISO [NEEDS FIRM INPUT: x].",
                                  "Zero incidents [NEEDS FIRM INPUT: x].",
                                  "We have never had a breach [NEEDS FIRM INPUT: x].",
                                  "We have had no incidents [NEEDS FIRM INPUT: x].",
                                  "We do not subcontract [NEEDS FIRM INPUT: x].",
                                  "Nil claims [NEEDS FIRM INPUT: x].",
                                  "We are incident-free [NEEDS FIRM INPUT: x].",
                                  "We are compliant [NEEDS FIRM INPUT: x].",
                                  "We are accredited [NEEDS FIRM INPUT: x].",
                                  "Staff are vetted [NEEDS FIRM INPUT: x].",
                                  "We are certified [NEEDS FIRM INPUT: x].",
                                  "We are award-winning [NEEDS FIRM INPUT: x].",
                                  "We cannot recall incidents [NEEDS FIRM INPUT: x].",
                                  "We cannot [NEEDS FIRM INPUT: x].",
                                  "We haven't [NEEDS FIRM INPUT: x].",
                                  "We didn\u2019t [NEEDS FIRM INPUT: x].",
                                  "Section S1 [NEEDS FIRM INPUT: x].",
                                  "We meet H2 [NEEDS FIRM INPUT: x]."])
def test_a4_short_uncited_claims_with_gap_marker_still_count(text):
    """T-202 review must-fix: a gap marker must not hide a short factual claim."""
    claims, exempt = SC.split_claims(text)
    assert claims == [text] and exempt == []


@pytest.mark.parametrize("text", ["We hold [NEEDS FIRM INPUT: ISO 14001 cert. Provide copy]",
                                  "[NEEDS FIRM INPUT: no such case study]",
                                  "Our [NEEDS FIRM INPUT: a] and the [NEEDS FIRM INPUT: b] will be provided."])
def test_a4_marker_only_gap_sentences_are_exempt_and_reported(text):
    claims, exempt = SC.split_claims(text)
    assert claims == [] and len(exempt) == 1
    r = SC.score_traceability([{"id": "d", "text": text + ". We hold ISO 9001 [E-1].", "retrieved_ids": [1], "live_ids": [1]}])
    assert r["gap_exempt"] == 1 and r["claims"] == 1 and r["gap_exempt_share"] == 0.5 and len(r["gap_exempt_sentences"]) == 1


def test_a4_each_new_trigger_matters_mutation_style(monkeypatch):
    """Each trigger alone must keep its sentence a claim: blank the others and it still counts; blank it and it is exempt."""
    cases = {"claim words": ("CLAIM_WORDS", "We are compliant [NEEDS FIRM INPUT: x]."),
             "negation raw": ("_NEG_RAW", "We cannot [NEEDS FIRM INPUT: x]."),
             "hyphen": ("_HYPHEN", "We are incident-proof [NEEDS FIRM INPUT: x].")}
    # letter+digit codes (S1) are triple-covered (digit check, _CODE, app fact_triggers), so only the parametrized test pins them
    never = re.compile(r"(?!x)x")
    for name, (attr, text) in cases.items():
        assert SC.claims_of(text), name
        with monkeypatch.context() as m:
            m.setattr(SC, attr, frozenset() if attr == "CLAIM_WORDS" else never)
            exempt_without = SC.claims_of(text) == []
        assert exempt_without, f"{name}: no other rule covers it, so removing the trigger would let it through"


def test_a4_stubs_stay_exempt_after_the_new_triggers():
    for t in ["We hold [NEEDS FIRM INPUT: x].", "Our insurance cover is [NEEDS FIRM INPUT: x].", "We will provide [NEEDS FIRM INPUT: x]."]:
        assert SC.claims_of(t) == [], t


def test_a4_cited_gap_sentence_is_always_scored():
    assert len(SC.claims_of("We hold [NEEDS FIRM INPUT: x] [E-1].")) == 1


def test_a1_ref_match_needs_minimum_text_similarity():
    key = [{"ref": "3", "kind": "question", "text": "Describe your safeguarding policy"}]
    wrong = [{"ref": "3", "kind": "question", "text": "Provide three years of audited accounts"}]
    right = [{"ref": "3", "kind": "question", "text": "Describe your safeguarding policies"}]
    assert SC.match_items(key, wrong) == [] and SC.match_items(key, right) == [(0, 0)]
    assert SC.REF_SIM_MIN == 0.5


def test_reading_rows_takes_the_shared_file_lock(cfg, tmp_path, monkeypatch):
    lg = led(tmp_path, cfg, dry=True)
    lg.append({"phase": "E1", "task": "x", "model": "fake", "input_tokens": 1, "output_tokens": 1})
    ops = []
    real = L.fcntl.flock
    monkeypatch.setattr(L.fcntl, "flock", lambda f, op: ops.append(op) or real(f, op))
    assert len(lg.rows()) == 1
    assert ops[0] == L.fcntl.LOCK_SH and ops[-1] == L.fcntl.LOCK_UN


def test_only_task_failed_is_recorded_other_app_errors_are_fatal(ctx, monkeypatch):
    from app.errors import AppError
    from app.tender.llm import TaskFailed
    boom = {"n": 0}

    def fail(c, phase, item):
        boom["n"] += 1
        raise TaskFailed("ai_invalid_output", "bad") if boom["n"] == 1 else AppError(404, "tenant_missing", "no tenant")
    monkeypatch.setattr(R, "_run_item", fail)
    with pytest.raises(AppError, match="no tenant"):
        R.run_phase("E1", ctx)
    rows = [json.loads(l) for l in (ctx.results_dir / "E1.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["result"] == {"error": "ai_invalid_output"}


def test_cache_clearing_phases_say_the_demo_seed_must_be_rerun(ctx, capsys):
    ctx.provider = type("Cacheable", (ScriptedFakeAI,), {"cacheable": True})()
    r = R.run_phase("T1", ctx)
    assert "reseed_required" not in r                       # T1 does not clear the cache
    r = R.run_phase("T2", ctx)
    assert "eval.seed" in r["reseed_required"] and "eval.seed" in capsys.readouterr().err
    ctx.provider = ScriptedFakeAI()                          # not cacheable: nothing cleared, no note
    assert "reseed_required" not in R.run_phase("T2", ctx)


# ---------- T-213: invented limits in A2, report-only deadline ----------

def _pair(key_kw=None, got_kw=None, kind=q):
    """One matched question (or mandatory) pair with a stated word limit of 100 on both sides, plus the overrides."""
    k = kind("1.1", "Describe your approach to mobilisation of the service", **{"word_limit": 100, **(key_kw or {})})
    g = kind("1.1", "Describe your approach to mobilisation of the service", **{"word_limit": 100, **(got_kw or {})})
    return SC.score_extraction([{"pack": "P", "key": [k], "got": [g]}])


def test_invented_word_limit_counts_wrong_in_a2():
    r = _pair({"word_limit": None, "page_limit": 2}, {"word_limit": 400, "page_limit": 2})["A2"]
    assert (r["stated"], r["correct"]) == (2, 1) and r["score"] == 0.5 and not r["pass"]
    assert r["wrong"] == [{"pack": "P", "ref": "1.1", "field": "word_limit", "key": None, "got": 400, "invented": True}]


def test_invented_page_limit_counts_wrong_in_a2_for_mandatory_too():
    for kind in (q, m):
        r = _pair({"page_limit": None}, {"page_limit": 3}, kind=kind)["A2"]
        assert (r["stated"], r["correct"]) == (2, 1), kind
        assert r["wrong"][0]["field"] == "page_limit" and r["wrong"][0]["invented"] is True


def test_wrong_value_against_non_null_key_has_no_invented_flag():
    r = _pair(got_kw={"word_limit": 90})["A2"]
    assert (r["stated"], r["correct"]) == (1, 0) and "invented" not in r["wrong"][0]


def test_invented_marks_and_weight_are_listed_not_scored():
    e = _pair({}, {"marks": 10, "weight_pct": 6})
    assert (e["A2"]["stated"], e["A2"]["correct"], e["A2"]["score"]) == (1, 1, 1.0) and e["A2"]["wrong"] == []
    assert e["A2"]["invented_unscored"] == [{"pack": "P", "ref": "1.1", "field": "marks", "got": 10},
                                            {"pack": "P", "ref": "1.1", "field": "weight_pct", "got": 6}]


def test_null_key_and_null_extracted_changes_nothing():
    e = _pair({"word_limit": None}, {"word_limit": None})["A2"]
    assert (e["stated"], e["correct"], e["score"]) == (0, 0, None) and e["wrong"] == [] and e["invented_unscored"] == []


def test_deadline_parser_formats():
    P = SC.parse_deadline_text
    want = {(2027, 4, 30)}
    assert P("Tender submission deadline: Friday 30 April 2027, 12:00 noon") == {"dates": want, "times": {(12, 0)}}
    assert P("2027-04-30T12:00")["dates"] == want and P("2027-04-30T12:00")["times"] == {(12, 0)}
    assert P("30/04/2027 12:00") == {"dates": want, "times": {(12, 0)}}
    assert P("30th of April 2027 at 12 noon") == {"dates": want, "times": {(12, 0)}}
    assert P("April 30, 2027 at 2pm") == {"dates": want, "times": {(14, 0)}}
    assert P("12:00 midday on Friday 21 May 2027") == {"dates": {(2027, 5, 21)}, "times": {(12, 0)}}
    assert P("14:00 on Friday 23 April 2027") == {"dates": {(2027, 4, 23)}, "times": {(14, 0)}}   # the 14 is a time, not a day
    assert P("17.00")["times"] == {(17, 0)} and P("5.00pm")["times"] == {(17, 0)} and P("5.30 p.m.")["times"] == {(17, 30)}
    assert P("30.04.2027") == {"dates": want, "times": set()}
    assert P("30.04.2027 17.00") == {"dates": want, "times": {(17, 0)}}
    assert P("") == {"dates": set(), "times": set()} and P(None) == {"dates": set(), "times": set()}


DL_KEY = {"ref": "", "kind": "deadline", "text": "Tender submission deadline: Friday 30 April 2027, 12:00 noon"}


def _dl(got):
    return SC.score_extraction([{"pack": "P", "key": [DL_KEY], "got": got}])["deadline"]


@pytest.mark.parametrize("got", [
    {"kind": "deadline", "text": "Submit by", "deadline": "2027-04-30T12:00"},
    {"kind": "deadline", "text": "Tenders due 30/04/2027 12:00", "deadline": None},
    {"kind": "deadline", "text": "Closing: 30 April 2027 at 12 noon", "deadline": ""},
    {"kind": "other", "text": "Return date", "deadline": "30 April 2027 12:00"},     # counted via the deadline field
])
def test_deadline_found_in_other_formats(got):
    d = _dl([got])
    assert d["found"] == 1 and d["total"] == 1 and d["packs"][0]["found"] and d["packs"][0]["time_match"] is True
    assert d["packs"][0]["key_text"] == DL_KEY["text"] and len(d["packs"][0]["got"]) == 1


def test_deadline_wrong_day_month_or_year_is_not_found():
    for dt in ("2027-04-29T12:00", "30 May 2027 12:00", "30 April 2026 12:00"):
        d = _dl([{"kind": "deadline", "text": dt, "deadline": None}])
        assert d["found"] == 0 and d["packs"][0]["found"] is False and d["packs"][0]["time_match"] is None


def test_deadline_right_date_wrong_time_is_found_with_time_match_false():
    d = _dl([{"kind": "deadline", "text": "30 April 2027 at 17:00", "deadline": None}])
    assert d["found"] == 1 and d["packs"][0]["time_match"] is False


def test_no_deadline_item_means_not_found_and_never_affects_pass():
    d = _dl([q("1.1", "Describe your approach")])
    assert d["found"] == 0 and d["total"] == 1 and d["packs"][0]["found"] is False and d["packs"][0]["got"] == []
    assert "deadline" not in SC.BARS
    assert extraction()["deadline"] == {"packs": [], "found": 0, "total": 0}     # no key deadline: nothing reported


# ---------- T-221: end-to-end plans, no live cache, clean provider stops, main(--live) ----------

def test_t1_plan_is_extract_plus_five_labelled_questions_of_the_first_demo_pack(ctx):
    plan = R.build_plan("T1", ctx)
    assert [i.kind for i in plan] == ["extract"] + ["draft"] * 5 == [i.kind for i in plan]
    assert plan[0].data["pack"] == "d1.txt"
    assert [i.data["id"] for i in plan[1:]] == [f"d1:1.{k}" for k in range(1, 6)]        # the first 5 labelled, in order
    assert [i.data["question"] for i in plan[1:]] == [f"Demo question 1.{k}?" for k in range(1, 6)]
    assert R.DEMO_QUESTIONS_PER_PACK == 5 and R.DEMO_QUESTIONS_FILE == "retrieval_labels.json"


@pytest.mark.parametrize("phase,size,drafts", [("T2", 3 * 3 * 3, 18), ("R1", 3 * 6, 15), ("R2", 6, 5)])
def test_demo_plans_size_and_unique_ids(ctx, phase, size, drafts):
    plan = R.build_plan(phase, ctx)           # T2: 3 packs x 3 passes x (1 extract + 3 drafts); R1: 3 x (1 + 5); R2 = T1
    assert len(plan) == size and len({i.id for i in plan}) == size
    assert sum(i.kind == "draft" for i in plan) == drafts


def test_demo_plan_needs_the_labels_and_never_invents_questions(ctx):
    (ctx.keys_dir / "retrieval_labels.json").write_text(json.dumps({"packs": {"d2": []}}))
    with pytest.raises(R.PhaseNotReady, match="no labelled questions for demo pack d1.txt"):
        R.build_plan("T1", ctx)
    (ctx.keys_dir / "retrieval_labels.json").unlink()
    with pytest.raises(R.PhaseNotReady, match="labelled questions not found"):
        R.build_plan("T1", ctx)


def test_the_committed_demo_packs_have_five_labelled_questions_each():
    class C:
        keys_dir = R.KEYS_DIR
    for pack in json.loads((R.PRODUCT / "demo-data" / "packs" / "manifest.json").read_text())["demo"]:
        qs = R.demo_questions(C, pack)
        assert len(qs) == 5 and all(q["question"] and q["id"].startswith(pack[:3]) for q in qs)


class CountingLive(LiveFake):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.n = 0

    def complete(self, *a, **kw):
        self.n += 1
        return super().complete(*a, **kw)


def test_a_live_phase_never_serves_an_item_from_ai_cache(ctx, cfg, tmp_path):
    from app.tender_models import AICache
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = CountingLive()
    live.provider.cacheable = True                           # as the real client is
    R.run_phase("T1", live)
    first = live.provider.n
    assert first > 0 and live.provider.cacheable is True     # restored after the phase
    (live.results_dir / "T1.jsonl").unlink()
    live.ledger = L.Ledger(tmp_path / "second.jsonl", cfg, dry_run=False)
    with live.sessions() as db:                              # something the model could be answered with from the cache
        db.add(AICache(tenant_id=live.tenant_id, key="stale", output_json={}, input_tokens=1, output_tokens=1)); db.commit()
    R.run_phase("T1", live)
    assert live.provider.n == 2 * first                      # the second run called the model for every item again
    with live.sessions() as db:
        assert db.scalar(select(func.count()).select_from(AICache).where(AICache.tenant_id == live.tenant_id)) == 0


def test_live_phase_clears_a_preseeded_cache_before_every_item(ctx, cfg, tmp_path, monkeypatch):
    from app.tender_models import AICache
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = CountingLive()
    seen = []

    def spy(c, phase, item):
        with c.sessions() as db:
            seen.append(db.scalar(select(func.count()).select_from(AICache).where(AICache.tenant_id == c.tenant_id)))
        return {}
    with live.sessions() as db:
        db.add(AICache(tenant_id=live.tenant_id, key="x", output_json={}, input_tokens=1, output_tokens=1)); db.commit()
    monkeypatch.setattr(R, "_run_item", spy)
    r = R.run_phase("T1", live)
    assert seen == [0] * 6 and r["reseed_required"] == R.RESEED_NOTE


def test_a_provider_ai_rejected_stops_the_run_cleanly_and_settles_the_ledger(ctx, cfg, tmp_path):
    from app.errors import AppError

    class Rejecting(LiveFake):
        def complete(self, *a, **kw):
            raise AppError(502, "ai_rejected", "The AI service couldn't handle that request.")
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = Rejecting()
    r = R.run_phase("T1", live)
    assert r["ran"] == 0 and "ai_rejected" in r["stopped"] and not r.get("model_mismatch")
    rows = live.ledger.rows()
    assert [x["kind"] for x in rows] == ["hold", "settle"] and rows[1]["charged_worst"] and rows[1]["usd"] > 0
    assert (live.results_dir / "T1.jsonl").read_text() == ""


def test_other_app_errors_stay_fatal(ctx, monkeypatch):
    from app.errors import AppError
    monkeypatch.setattr(R, "_run_item", lambda c, p, i: (_ for _ in ()).throw(AppError(404, "tenant_missing", "no tenant")))
    with pytest.raises(AppError):
        R.run_phase("T1", ctx)


@pytest.mark.parametrize("phase", ["E1", "E2", "E3", "E4", "R1", "R2"])
def test_a_non_tuning_phase_is_refused_when_not_dry_even_with_the_fake(ctx, cfg, tmp_path, phase):
    live_ctx(ctx, cfg, tmp_path)                             # ledger live, ctx.dry False, provider still the fake
    with pytest.raises(R.PhaseNotReady, match="L1 configuration freeze"):
        R.run_phase(phase, ctx)


# main(["T1", "--live"]) with temp ledger and results

@pytest.fixture
def live_main(app, cfg, tmp_path, monkeypatch):
    sessions = app.state.db.sessions
    with sessions() as db:
        db.add(Tenant(name=SD.FIRM)); db.commit()
    from .conftest import TEST_DB
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    for k, v in (("AZURE_OPENAI_ENDPOINT", "https://x.invalid"), ("AZURE_OPENAI_API_KEY", "k"), ("AZURE_OPENAI_DEPLOYMENT_MINI", "d")):
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(R, "LIVE_LEDGER", tmp_path / "live-ledger.jsonl")
    monkeypatch.setattr(R, "RESULTS_DIR", tmp_path / "live-results")
    monkeypatch.setattr(R, "load_budget_config", lambda *a, **k: cfg)
    holder = {}
    monkeypatch.setattr(R, "build_live_provider", lambda env=None: holder["p"])
    return holder


def test_main_live_writes_a_non_dry_ledger_and_results_and_exits_0(live_main, tmp_path):
    live_main["p"] = LiveFake()
    assert R.main(["T1", "--live"]) == 0
    rows = [json.loads(l) for l in (tmp_path / "live-ledger.jsonl").read_text().splitlines()]
    assert rows and {"hold", "settle"} <= {r["kind"] for r in rows} and not any(r.get("dry_run") for r in rows)
    assert all(r["usd"] > 0 for r in rows if r["kind"] == "settle")
    out = [json.loads(l) for l in (tmp_path / "live-results" / "T1.jsonl").read_text().splitlines()]
    assert len(out) == 6 and out[0]["item"].startswith("extract:S04")


def test_main_live_wrong_model_exits_7(live_main, tmp_path, capsys):
    live_main["p"] = LiveFake(model="gpt-5.4-pro")
    assert R.main(["T1", "--live"]) == 7
    assert "MODEL MISMATCH" in capsys.readouterr().err


def test_main_live_cap_exits_8(live_main, tmp_path, capsys):
    live_main["p"] = LiveFake()
    from eval.ledger import Ledger
    Ledger(tmp_path / "live-ledger.jsonl", R.load_budget_config(), dry_run=False).append(
        {"phase": "T2", "task": "x", "model": "gpt-5-mini", "input_tokens": 0, "output_tokens": 999_000})
    (tmp_path / "live-results").mkdir(); (tmp_path / "live-results" / "T2.jsonl").write_text("")
    assert R.main(["T1", "--live"]) == 8
    assert "tuning sub-cap" in capsys.readouterr().err


def test_main_live_ai_unavailable_and_ai_rejected_exit_8_without_a_traceback(live_main, tmp_path, capsys):
    from app.ai import AIUnavailable
    from app.errors import AppError
    for exc in (AIUnavailable("down"), AppError(502, "ai_rejected", "The AI service couldn't handle that request.")):
        class Boom(LiveFake):
            def complete(self, *a, **kw):
                raise exc
        live_main["p"] = Boom()
        for f in ("live-ledger.jsonl",):
            (tmp_path / f).unlink(missing_ok=True)
        (tmp_path / "live-results" / "T1.jsonl").unlink(missing_ok=True)
        assert R.main(["T1", "--live"]) == 8
        err = capsys.readouterr().err
        assert "live phase stopped early" in err and "Traceback" not in err


def _source_rows(stem):
    src = next((R.PRODUCT / "demo-data" / "pack-sources").glob(f"{stem}-*.md")).read_text(encoding="utf-8")
    rows = {}
    for line in src.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 4:
            rows[cells[0]] = cells
    return rows


@pytest.mark.parametrize("stem", ["S04", "S08", "S12"])
def test_demo_word_limits_match_the_pack_source_tables(stem):
    data = json.loads((R.HERE / "demo_word_limits.json").read_text())["packs"][stem]
    rows = _source_rows(stem)
    labels = json.loads((R.KEYS_DIR / "retrieval_labels.json").read_text())["packs"]
    refs = [i["ref"] for p, items in labels.items() if p.startswith(stem) for i in items[:R.DEMO_QUESTIONS_PER_PACK]]
    assert sorted(data) == sorted(refs)                       # exactly the questions the T1/R plans draft
    for ref, v in data.items():
        printed = rows[ref][-1]
        assert v["printed"] == printed                        # the limit text is copied from the table, verbatim
        nums = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?=\s*words)|(?<=Words: )\d+", printed)]
        if v["word_limit"] is None:
            assert printed.startswith("Shared") or "page" in printed or printed.startswith("No limit")
        else:
            assert nums and v["word_limit"] == nums[0]


def test_demo_questions_carry_the_printed_word_limits():
    class C:
        keys_dir = R.KEYS_DIR
    assert [q["word_limit"] for q in R.demo_questions(C, "S08-security-trust-cctv-keyholding.docx")] == [750, 750, 500, 400, 1000]
    assert [q["word_limit"] for q in R.demo_questions(C, "S04-cleaning-halls-and-toilets.docx")] == [None, None, None, None, 400]
    assert [q["word_limit"] for q in R.demo_questions(C, "S12-grounds-hallowby-town.docx")] == [None, None, None, None, 400]


def test_tuning_phase_turns_the_cache_off_during_the_run_and_restores_it(ctx, cfg, tmp_path, monkeypatch):
    live = live_ctx(ctx, cfg, tmp_path)
    live.provider = CountingLive()
    live.provider.cacheable = True
    seen = []
    monkeypatch.setattr(R, "_run_item", lambda c, p, i: seen.append(c.provider.cacheable) or {})
    R.run_phase("T1", live)
    assert seen == [False] * 6 and live.provider.cacheable is True
