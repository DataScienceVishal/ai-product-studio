import builtins
import json
import socket
import sys
import urllib.error
from pathlib import Path

import pytest

PRODUCT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PRODUCT))
sys.path.insert(0, str(PRODUCT / "benchmark"))
from extractor import budget as B  # noqa: E402
from extractor import extract, pdfio, prompt, providers, run, vocab  # noqa: E402
import score  # noqa: E402

DATA = PRODUCT / "benchmark" / "data"
SHEETS, TUNING = DATA / "sheets", DATA / "tuning"


def oracle_for(truth):
    """Test-only: answers a sheet from its truth (the extractor itself never sees truth)."""
    def strip(f):
        return {k: v for k, v in f.items() if k != "accepted_values"}
    comps = [{"name": c["name"], "material": strip(c["material"]), "colour": strip(c["colour"]),
              "weight_g": strip(c["weight_g"]), "features": {k: strip(v) for k, v in c["features"].items()}}
             for c in truth["components"]]
    return lambda system, parts: "```json\n" + json.dumps({"components": comps}) + "\n```"


PRO = "gpt-5.4-pro"
P_IN, P_OUT = B.PRICES[PRO]
MINI = "gpt-5-mini"


def new_budget(tmp_path, **kw):
    kw.setdefault("model", PRO)
    return B.Budget(tmp_path / "ledger.jsonl", **kw)


# ---- item 3: isolation ----------------------------------------------------------------------------

def test_no_module_but_cli_names_truth_or_manifest():
    for f in (PRODUCT / "extractor").glob("*.py"):
        if f.name in ("run.py",):
            continue
        src = f.read_text().lower()
        for bad in ("manifest", "tuning_truth", "data/truth", '"truth"', "page_text"):
            assert bad not in src.replace("truth-shaped", "").replace("truth shape", ""), (f.name, bad)


def test_extraction_reads_only_a_temp_copy(monkeypatch, tmp_path):
    opened = []
    real_open = builtins.open
    monkeypatch.setattr(builtins, "open", lambda p, *a, **k: (opened.append(str(p)), real_open(p, *a, **k))[1])
    seen_dirs = []
    real_read = pdfio.read_pages
    monkeypatch.setattr(pdfio, "read_pages", lambda p: (seen_dirs.append(sorted(x.name for x in Path(p).parent.iterdir())),
                                                        real_read(p))[1])
    pred = extract.extract_pdf(SHEETS / "S001.pdf", providers.FakeProvider(), new_budget(tmp_path, model=MINI))
    assert pred["sheet_id"] == "S001"
    assert seen_dirs == [["sheet.pdf"]]  # empty temp dir holding only the copy
    pdf_reads = [p for p in opened if p.endswith(".pdf")]
    assert pdf_reads[0] == str(SHEETS / "S001.pdf")  # the one read of the source: the copy itself
    assert len(pdf_reads) > 1 and all("pepr-extract-" in p for p in pdf_reads[1:])  # everything after reads the copy
    for p in opened:
        assert "manifest" not in p and "truth" not in p


def test_extract_pdf_signature_takes_only_a_path_no_truth_args():
    import inspect
    assert list(inspect.signature(extract.extract_pdf).parameters)[:2] == ["pdf_path", "provider"]


# ---- item 4: layout text and images ---------------------------------------------------------------

def test_text_pages_use_layout_mode(monkeypatch):
    from pypdf import PageObject
    modes = []
    real = PageObject.extract_text
    monkeypatch.setattr(PageObject, "extract_text", lambda self, *a, **k: (modes.append(k.get("extraction_mode")),
                                                                         real(self, *a, **k))[1])
    pages = pdfio.read_pages(SHEETS / "S011.pdf")
    assert modes and set(modes) == {"layout"}
    assert all(p["mode"] == "layout_text" for p in pages)


def test_scanned_sheets_send_images_and_record_it(tmp_path):
    fake = providers.FakeProvider()
    pred = extract.extract_pdf(SHEETS / "S021.pdf", fake, new_budget(tmp_path, model=MINI))
    assert all(p["input"] == "image" for p in pred["pages"])
    assert any(part["type"] == "image" and part["media_type"] == "image/jpeg" and part["data_b64"]
               for part in fake.calls[0])
    assert not any("Oakridge" in part.get("text", "") for part in fake.calls[0])  # no recorded page text leaks in
    text_pred = extract.extract_pdf(SHEETS / "S011.pdf", providers.FakeProvider(), new_budget(tmp_path, model=MINI))
    assert all(p["input"] == "layout_text" for p in text_pred["pages"])


def test_two_column_layout_keeps_columns_apart():
    two_col = next(s["sheet_id"] for s in json.loads((DATA / "manifest.json").read_text())["test"]
                   if s["template"] == "two_column")
    t = pdfio.read_pages(SHEETS / f"{two_col}.pdf")[0]["text"]
    assert "  " in t  # layout mode keeps the wide gap between the columns


# ---- prompt ---------------------------------------------------------------------------------------

def test_prompt_lists_vocab_keys_and_the_none_examples():
    s = prompt.system_prompt()
    for k in vocab.FEATURE_VOCAB:
        assert k in s
    for k in ("black (carbon black)", "corrugated board", "HDPE cap with PE liner", "outer carton"):
        assert k in s
    assert "Sleeve: none" in s and "to be confirmed" in s and "ONE cell" in s and "never" in s.lower()
    assert "ram_category" in s  # told it is derived


def test_ram_mapping_matches_generator_materials():
    import generate
    gen = {v: ram for comps in generate.COMPONENTS.values() for v, ram, _ in comps}
    assert vocab.RAM_CATEGORY == gen


# ---- budget guard (item 5) ------------------------------------------------------------------------

def test_budget_refuses_worst_case_over_usd_cap(tmp_path):
    b = new_budget(tmp_path)
    b.record("x", 0, int(11.5e6 / P_OUT), note="seed")  # USD 11.5 spent
    with pytest.raises(B.BudgetExceeded):
        b.check(10_000, 12_000)  # worst 0.15 + 1.44 > 0.5 left
    b.check(1000, 1000)  # 0.015 + 0.12 fits


def test_budget_refuses_token_cap(tmp_path):
    b = new_budget(tmp_path, max_tokens=100_000)
    with pytest.raises(B.BudgetExceeded, match="token"):
        b.check(90_000, 12_000)
    b.check(80_000, 12_000)


def test_budget_exact_boundary(tmp_path):
    b = new_budget(tmp_path, max_usd=1.0)
    b.check(0, int(1e6 / P_OUT))  # 8333 tokens = USD 0.99996: allowed
    with pytest.raises(B.BudgetExceeded):
        b.check(0, int(1e6 / P_OUT) + 2)


def test_ledger_persists_and_is_shared(tmp_path):
    b = new_budget(tmp_path)
    b.record("S1", 1000, 500)
    b2 = new_budget(tmp_path)
    assert b2.tokens == 1500 and b2.spent_usd == pytest.approx(1000 * P_IN / 1e6 + 500 * P_OUT / 1e6)
    e = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[0])
    assert e["sheet_id"] == "S1" and e["usd"] == pytest.approx(0.12) and e["price_in"] == 30.0 and e["price_out"] == 180.0


def test_guard_runs_before_the_call_and_blocks_it(tmp_path):
    b = new_budget(tmp_path, max_usd=0.01)
    fake = providers.FakeProvider()
    with pytest.raises(B.BudgetExceeded):
        extract.extract_pdf(SHEETS / "S001.pdf", fake, b)
    assert fake.calls == [] and not (tmp_path / "ledger.jsonl").exists()


def test_failed_call_that_may_have_run_is_charged_worst_case(tmp_path):
    class Boom:
        output_headroom = 0
        def complete(self, s, p, m, **kw):
            raise providers.ProviderError("timeout", 5000, m, may_have_run=True)
    b = new_budget(tmp_path)
    with pytest.raises(providers.ProviderError):
        extract.extract_pdf(SHEETS / "S001.pdf", Boom(), b, max_output_tokens=1000)
    assert b.tokens == 6000 and json.loads((tmp_path / "ledger.jsonl").read_text())["estimated"] is True


# ---- Azure provider (no network: transport is injected) -------------------------------------------

ENV = {"T56_SPEND_APPROVED": "1", "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
       "AZURE_OPENAI_API_KEY": "sekret-key-123", "T56_DEPLOYMENT": PRO}


@pytest.fixture
def nb(tmp_path):
    """Budget factory; every call in one test shares tmp_path/l.jsonl (cleaned up by pytest)."""
    return lambda: B.Budget(tmp_path / "l.jsonl", model=PRO)


def ok_body(text="{}", i=100, o=50):
    return json.dumps({"status": "completed", "model": "gpt-5.4-pro",
                       "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
                       "usage": {"input_tokens": i, "output_tokens": o}}).encode()


def test_azure_refuses_without_spend_approval():
    with pytest.raises(providers.SpendNotApproved):
        providers.AzureResponsesProvider(env={"AZURE_OPENAI_ENDPOINT": "https://x"})
    with pytest.raises(providers.SpendNotApproved):
        providers.AzureResponsesProvider(env={"T56_SPEND_APPROVED": "0", "AZURE_OPENAI_ENDPOINT": "https://x"})


def test_azure_refusal_also_at_call_time(nb):
    env = dict(ENV)
    p = providers.AzureResponsesProvider(env=env, transport=lambda r, t: pytest.fail("must not send"))
    env["T56_SPEND_APPROVED"] = "0"
    with pytest.raises(providers.SpendNotApproved):
        p.complete("s", [{"type": "text", "text": "x"}], 100, budget=nb())


def test_cli_refuses_azure_without_approval(monkeypatch, tmp_path):
    monkeypatch.delenv("T56_SPEND_APPROVED", raising=False)
    assert run.main(["--set", "tuning", "--provider", "azure", "--out", str(tmp_path / "o")]) == 2
    assert not list((tmp_path / "o").glob("*.json"))


def test_azure_request_shape(nb):
    sent = []
    def tr(req, timeout):
        sent.append((req, timeout))
        return 200, {}, ok_body()
    p = providers.AzureResponsesProvider(env=ENV, transport=tr, reasoning_effort="medium", timeout=77)
    parts = [{"type": "text", "text": "hi"}, {"type": "image", "media_type": "image/jpeg", "data_b64": "QUJD"}]
    r = p.complete("sys", parts, 4321, budget=nb())
    req, timeout = sent[0]
    body = json.loads(req.data)
    assert req.full_url == "https://example.openai.azure.com/openai/v1/responses" and timeout == 77
    assert body["model"] == "gpt-5.4-pro" and body["max_output_tokens"] == 4321
    assert body["reasoning"] == {"effort": "medium"} and body["store"] is False and body["instructions"] == "sys"
    c = body["input"][0]["content"]
    assert c[0] == {"type": "input_text", "text": "hi"}
    assert c[1]["type"] == "input_image" and c[1]["image_url"] == "data:image/jpeg;base64,QUJD"
    assert req.get_header("Api-key") == "sekret-key-123"
    assert (r.input_tokens, r.output_tokens, r.model) == (100, 50, "gpt-5.4-pro")


def test_azure_default_reasoning_effort_is_explicit_and_validated():
    p = providers.AzureResponsesProvider(env=ENV)
    assert p.reasoning_effort == "medium" and p.deployment == "gpt-5.4-pro"
    with pytest.raises(ValueError):
        providers.AzureResponsesProvider(env=ENV, reasoning_effort="max")


def test_azure_retries_429_with_backoff_then_succeeds(nb):
    seq = iter([(429, {"retry-after": "3"}, b""), (503, {}, b""), (200, {}, ok_body())])
    slept = []
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: next(seq), sleep=slept.append, backoff=2)
    assert p.complete("s", [{"type": "text", "text": "x"}], 10, budget=nb()).text == "{}"
    assert slept == [3.0, 4.0]


def test_azure_connect_error_retried_then_clear_error(nb):
    def tr(req, t):
        raise urllib.error.URLError(ConnectionRefusedError("no"))
    slept = []
    p = providers.AzureResponsesProvider(env=ENV, transport=tr, sleep=slept.append, retries=2)
    with pytest.raises(providers.ProviderError, match="gave up after 3 attempts") as e:
        p.complete("s", [{"type": "text", "text": "x"}], 10, budget=nb())
    assert len(slept) == 2 and not e.value.may_have_run and "sekret" not in str(e.value)


def test_azure_timeout_is_not_retried_and_may_have_run(nb):
    calls = []
    def tr(req, t):
        calls.append(1)
        raise socket.timeout()
    p = providers.AzureResponsesProvider(env=ENV, transport=tr, sleep=lambda s: None)
    with pytest.raises(providers.ProviderError) as e:
        p.complete("s", [{"type": "text", "text": "x"}], 500, budget=nb())
    assert calls == [1] and e.value.may_have_run and e.value.output_tokens == 500


def test_azure_auth_error_and_incomplete_answer(nb):
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: (401, {}, b"bad"))
    with pytest.raises(providers.ProviderError, match="credentials rejected"):
        p.complete("s", [{"type": "text", "text": "x"}], 10, budget=nb())
    inc = json.dumps({"status": "incomplete", "output": [], "usage": {"input_tokens": 9, "output_tokens": 7}}).encode()
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: (200, {}, inc))
    with pytest.raises(providers.ProviderError) as e:
        p.complete("s", [{"type": "text", "text": "x"}], 10, budget=nb())
    assert (e.value.input_tokens, e.value.output_tokens) == (9, 7)  # billed anyway, recorded by the caller


# ---- output cleaning ------------------------------------------------------------------------------

def test_parse_json_fences_and_prose():
    assert extract.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract.parse_json('Here you go: {"a": 1} done') == {"a": 1}


def test_clean_output_drops_junk_and_derives_ram():
    raw = {"components": [
        {"name": "cap", "material": {"status": "present", "value": "HDPE", "refs": [{"page": 1, "quote": "HDPE"}, "junk"]},
         "colour": "blue", "weight_g": {"status": "present", "value": "n/a"},
         "features": {"liner": {"status": "missing"}, "ink_coating": 7}},
        "not a component", {"name": "can", "material": {"status": "missing"}}]}
    comps, warns = extract.clean_output(raw)
    assert len(comps) == 2 and warns
    cap = comps[0]
    assert cap["ram_category"] == "plastic" and "colour" not in cap and "weight_g" not in cap
    assert cap["material"]["refs"] == [{"page": 1, "quote": "HDPE"}] and list(cap["features"]) == ["liner"]
    assert comps[1]["ram_category"] == "missing"


def test_invalid_json_gives_empty_prediction_with_warning(tmp_path):
    fake = providers.FakeProvider(responder=lambda s, p: "sorry")
    pred = extract.extract_pdf(SHEETS / "S001.pdf", fake, new_budget(tmp_path, model=MINI))
    assert pred["components"] == [] and pred["warnings"]


# ---- end to end: oracle through the whole pipeline, then the scorer -------------------------------

def test_oracle_through_pipeline_scores_100_percent_and_passes_on_test_set(tmp_path):
    truths, _, texts, messy = score.load_set("test", "/none")
    b = new_budget(tmp_path, model=MINI)
    preds = {}
    for sid, t in truths.items():
        preds[sid] = extract.extract_pdf(SHEETS / f"{sid}.pdf", providers.FakeProvider(oracle_for(t)), b)
    man = {e["sheet_id"]: e for e in json.loads((DATA / "manifest.json").read_text())["test"]}
    n_img = sum(int(e["pages"]) for e in man.values() if e["scanned"])
    assert n_img >= 5 and sum(1 for p in preds.values() for pg in p["pages"] if pg["input"] == "image") == n_img
    r = score.score_set(truths, preds, texts, messy, score.read_ledger_cost(b.ledger, set(truths)))
    assert r["overall"]["field_accuracy"] == 1.0 and r["overall"]["untraced"] == 0, r["checks"]
    assert r["pass"]


def test_cli_fake_end_to_end(tmp_path, capsys):
    rc = run.main(["--set", "tuning", "--provider", "fake", "--out", str(tmp_path / "o")])
    out = capsys.readouterr().out
    assert rc == 0 or "OVERALL" in out  # the default fake scores badly; the plumbing is what is tested
    assert len(list((tmp_path / "o").glob("S9*.json"))) == 5 and (tmp_path / "o" / "ledger.jsonl").exists()
    assert (tmp_path / "o" / "score.json").exists() and "OVERALL" in out


# ---- review fixes ---------------------------------------------------------------------------------

def test_default_max_output_tokens_is_6000():
    assert extract.MAX_OUTPUT_TOKENS == 6000


def test_preflight_arithmetic(tmp_path):
    B.preflight(new_budget(tmp_path / "fresh"), 30, 6000)
    need = 30 * 0.316 + B.usd(B.WORST_INPUT_TOKENS, 6000, PRO)
    b = new_budget(tmp_path / "short")
    b.record("x", 0, int((12 - need + 0.05) * 1e6 / P_OUT))
    with pytest.raises(B.BudgetExceeded, match="short by"):
        B.preflight(b, 30, 6000)
    b2 = new_budget(tmp_path / "enough")
    b2.record("x", 0, int((12 - need - 0.05) * 1e6 / P_OUT))
    B.preflight(b2, 30, 6000)


def test_preflight_token_analogue(tmp_path):
    with pytest.raises(B.BudgetExceeded, match="tokens"):
        B.preflight(new_budget(tmp_path, max_tokens=500_000), 30, 6000)


def test_cli_refuses_to_start_test_set_when_budget_short(tmp_path, capsys):
    ledger = tmp_path / "ledger.jsonl"
    B.Budget(ledger, model=PRO).record("tuning", 0, int(11.9e6 / P_OUT))  # USD 11.9 spent: 0.1 left < ~0.55 needed (fake = mini price)
    rc = run.main(["--set", "test", "--provider", "fake", "--out", str(tmp_path / "o"), "--ledger", str(ledger)])
    assert rc == 4 and "short by" in capsys.readouterr().err
    assert not list((tmp_path / "o").glob("S*.json"))


def test_cli_starts_test_set_with_full_budget(tmp_path):
    assert run.main(["--set", "test", "--provider", "fake", "--out", str(tmp_path / "o"), "--no-score"]) == 0
    assert len(list((tmp_path / "o").glob("S0*.json"))) == 30


def test_http_400_is_fatal_and_stops_the_run(monkeypatch, tmp_path):
    class P(providers.FakeProvider):
        def complete(self, s, p, m, **kw):
            raise providers.ProviderError("request rejected (HTTP 400)", fatal=True)
    monkeypatch.setattr(run, "make_provider", lambda name: P())
    assert run.main(["--set", "tuning", "--provider", "fake", "--out", str(tmp_path / "o"), "--no-score"]) == 5


# ---- S2: every billable 5xx is charged at worst case, budget re-checked before each retry -------------------
X = [{"type": "text", "text": "x"}]  # estimate_input_tokens = 1 + len(system "s") = 2


def _ledger(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines()]


def test_s2_three_5xx_then_200_records_three_worst_cases_plus_real(tmp_path):
    seq = iter([(500, {}, b""), (502, {}, b""), (503, {}, b""), (200, {}, ok_body())])
    b = B.Budget(tmp_path / "l.jsonl", model=PRO)
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: next(seq), sleep=lambda s: None)
    res = p.complete("s", X, 1000, budget=b, label="S1")
    b.record("S1", res.input_tokens, res.output_tokens, served_model=res.model)  # what extract_pdf does
    rows = _ledger(tmp_path / "l.jsonl")
    assert len(rows) == 4
    assert [r["estimated"] for r in rows] == [True, True, True, False]
    assert all((r["input_tokens"], r["output_tokens"]) == (2, 1000) for r in rows[:3])
    assert rows[3]["input_tokens"] == 100 and b.tokens == 3 * 1002 + 150


def test_s2_429_and_connect_errors_are_free(tmp_path):
    seq = iter([(429, {}, b""), "conn", (200, {}, ok_body())])

    def tr(req, t):
        v = next(seq)
        if v == "conn":
            raise urllib.error.URLError(ConnectionRefusedError("no"))
        return v
    b = B.Budget(tmp_path / "l.jsonl", model=PRO)
    p = providers.AzureResponsesProvider(env=ENV, transport=tr, sleep=lambda s: None)
    p.complete("s", X, 1000, budget=b, label="S1")
    assert not (tmp_path / "l.jsonl").exists() and b.tokens == 0


def test_s2_retry_refused_when_next_attempt_could_cross_cap(tmp_path):
    calls = []
    def tr(req, t):
        calls.append(1)
        return 500, {}, b""
    # cap fits the first attempt's worst case (1002 tokens) twice over, but not three times
    b = B.Budget(tmp_path / "l.jsonl", model=PRO, max_tokens=2500)
    b.check(2, 1000)
    p = providers.AzureResponsesProvider(env=ENV, transport=tr, sleep=lambda s: None)
    with pytest.raises(B.BudgetExceeded, match="retry 3"):
        p.complete("s", X, 1000, budget=b, label="S1")
    assert len(calls) == 2 and len(_ledger(tmp_path / "l.jsonl")) == 2 and b.tokens == 2004


def test_s2_final_5xx_is_charged_and_gives_up(tmp_path):
    b = B.Budget(tmp_path / "l.jsonl", model=PRO)
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: (500, {}, b""), sleep=lambda s: None, retries=2)
    with pytest.raises(providers.ProviderError, match="gave up after 3 attempts") as e:
        p.complete("s", X, 1000, budget=b, label="S1")
    assert len(_ledger(tmp_path / "l.jsonl")) == 3 and not e.value.may_have_run  # no double charge in extract_pdf


def test_s2_usd_cap_refuses_retry(tmp_path):
    b = B.Budget(tmp_path / "l.jsonl", model=PRO, max_usd=0.4)  # worst case 1000 out + 2 in = USD 0.18006 per attempt
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: (500, {}, b""), sleep=lambda s: None)
    with pytest.raises(B.BudgetExceeded, match="USD"):
        p.complete("s", X, 1000, budget=b, label="S1")
    assert len(_ledger(tmp_path / "l.jsonl")) == 2


def test_s2_extract_pdf_charges_5xx_through_azure_provider(tmp_path):
    seq = iter([(500, {}, b""), (500, {}, b""), (200, {}, ok_body('{"components": []}'))])
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: next(seq), sleep=lambda s: None)
    b = new_budget(tmp_path)
    extract.extract_pdf(SHEETS / "S001.pdf", p, b, max_output_tokens=1000)
    rows = [json.loads(l) for l in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [r["estimated"] for r in rows] == [True, True, False]
    assert [r["sheet_id"] for r in rows] == ["S001"] * 3  # 5xx rows must count in the per-sheet cost check
    assert rows[0]["output_tokens"] == rows[1]["output_tokens"] == 1000 and rows[0]["input_tokens"] > 1000
    assert (rows[2]["input_tokens"], rows[2]["output_tokens"]) == (100, 50)


def test_s2_retry_check_includes_output_headroom(tmp_path):
    p = providers.AzureResponsesProvider(env=ENV, transport=lambda r, t: (500, {}, b""), sleep=lambda s: None)
    p.output_headroom = 5000
    b = B.Budget(tmp_path / "l.jsonl", model=PRO, max_tokens=2500)
    with pytest.raises(B.BudgetExceeded, match="retry 2"):
        p.complete("s", X, 1000, budget=b, label="S1")


# ---- realism supplement (S7, Amendment 4) ---------------------------------------------------------

SUPP = PRODUCT / "benchmark" / "supplement"


def test_encrypted_supplement_sheet_is_read_by_pdfio():
    pages = pdfio.read_pages(SUPP / "data" / "sheets" / "S812.pdf")
    assert pages[0]["mode"] == "layout_text" and "Bottle weight" in pages[0]["text"]
    assert b"/AESV2" in (SUPP / "data" / "sheets" / "S812.pdf").read_bytes()


def test_oracle_through_pipeline_scores_100_percent_on_supplement(tmp_path):
    truths, _, texts, messy = score.load_set("supplement", "/none")
    b = new_budget(tmp_path, model=MINI)
    preds = {sid: extract.extract_pdf(SUPP / "data" / "sheets" / f"{sid}.pdf", providers.FakeProvider(oracle_for(t)), b)
             for sid, t in truths.items()}
    assert len(preds) == 12 and all(p["components"] for p in preds.values())
    r = score.score_set(truths, preds, texts, messy, None, require_cost=False)
    assert r["overall"]["field_accuracy"] == 1.0 and r["overall"]["untraced"] == 0, r["checks"]
    assert r["overall"]["fabricated"] == 0
    r["checks"].pop("2_messy10_field_accuracy>=0.80")  # no messy-10 in the supplement (score.main drops it too)
    assert all(r["checks"].values())


def test_cli_supplement_set_fake(tmp_path, capsys):
    (tmp_path / "o").mkdir()
    (tmp_path / "o" / "ledger.jsonl").write_text(json.dumps({"sheet_id": "S001", "input_tokens": 1, "output_tokens": 1, "usd": 0.0, "model": MINI}) + "\n")
    run.main(["--set", "supplement", "--provider", "fake", "--out", str(tmp_path / "o")])
    assert len(list((tmp_path / "o").glob("S8*.json"))) == 12 and "OVERALL" in capsys.readouterr().out


def test_prompt_has_amendment_4_lines():
    s = prompt.system_prompt()
    for need in ("largest share", "Weight (g) | 25.5", "gsm", "title names one item code"):
        assert need in s


def test_supplement_refuses_before_test_set_in_ledger(tmp_path, capsys):
    assert run.main(["--set", "supplement", "--provider", "fake", "--out", str(tmp_path / "o")]) == 6
    assert "after the test set" in capsys.readouterr().err
    assert not list((tmp_path / "o").glob("S8*.json"))
    (tmp_path / "o2").mkdir()  # a tuning-only ledger is not enough either
    (tmp_path / "o2" / "ledger.jsonl").write_text(json.dumps({"sheet_id": "S901", "input_tokens": 1, "output_tokens": 1, "usd": 0.0, "model": MINI}) + "\n")
    assert run.main(["--set", "supplement", "--provider", "fake", "--out", str(tmp_path / "o2")]) == 6


def test_supplement_refuses_on_malformed_ledger(tmp_path, capsys):
    out = tmp_path / "o"
    out.mkdir()
    good = json.dumps({"sheet_id": "S001", "input_tokens": 1, "output_tokens": 1, "usd": 0.0, "model": MINI})
    for bad in ("{not json\n", good + "\n[1, 2]\n", good + "\n{truncated"):
        (out / "ledger.jsonl").write_text(bad)
        assert run.main(["--set", "supplement", "--provider", "fake", "--out", str(out)]) == 6
        assert "unreadable" in capsys.readouterr().err
    assert not list(out.glob("S8*.json"))


def test_prompt_does_not_exclude_listed_outer_case_components():
    s = prompt.system_prompt()
    assert "unless the sheet gives them a material" not in s
    assert 'Component: outer case", even if its Material row says n/a) stays a component' in s
    # S019-style wording really is on a test sheet and has Material n/a
    text = " ".join(p["text"] for p in pdfio.read_pages(SHEETS / "S019.pdf")).lower()
    assert "outer case" in text and "n/a" in text
    comp = json.loads((DATA / "truth" / "S019.json").read_text())["components"]
    assert any(c["name"] == "outer carton" and c["material"]["status"] == "missing" for c in comp)


# ---- run e08c tuning follow-up ----------------------------------------------------------------------
S902_TEXT = ("Component summary\n tin can - oxygen barrier: monolayer, no barrier\n"
             "tin can - ink / coating: print: UV-curable ink\n sachet - barrier: no barrier layer present\n")


def _comp(**feats):
    return {"name": "can", "features": feats, "ram_category": "missing"}


def _f(value, quote, page=1):
    return {"status": "present", "value": value, "refs": [{"page": page, "quote": quote}]}


def test_s902_fragment_quotes_are_dropped_and_full_wording_kept():
    pages = [{"page": 1, "mode": "layout_text", "text": S902_TEXT, "chars": len(S902_TEXT)}]
    comps = [_comp(barrier_layer=_f("no barrier layer", "no barrier"),
                   ink_coating=_f("UV-cured ink", "UV-curable ink"))]
    warns = []
    extract.drop_unverified(comps, pages, warns)
    assert comps[0]["features"]["barrier_layer"] == {"status": "missing"}
    assert comps[0]["features"]["ink_coating"] == {"status": "missing"} and len(warns) == 2
    good = [_comp(barrier_layer=_f("no barrier layer", "monolayer, no barrier"),
                  ink_coating=_f("UV-cured ink", "print: UV-curable ink"))]
    extract.drop_unverified(good, pages, [])
    assert good[0]["features"]["barrier_layer"]["status"] == "present"
    assert good[0]["features"]["ink_coating"]["status"] == "present"


def test_drop_unverified_page_text_misses_wrong_page_and_image_pages():
    pages = [{"page": 1, "mode": "layout_text", "text": "cap HDPE 3.5 g", "chars": 14},
             {"page": 2, "mode": "image", "text": None, "chars": 0}]
    c = {"name": "cap", "material": _f("HDPE", "HDPE"), "colour": _f("blue", "blue"),
         "weight_g": _f(3.5, "3.5 g", page=3), "features": {"liner": _f("no liner", "x", page=2)}, "ram_category": "plastic"}
    extract.drop_unverified([c], pages, [])
    assert c["material"]["status"] == "present"
    assert c["colour"] == {"status": "missing"}      # quote not on page 1
    assert c["weight_g"] == {"status": "missing"}    # page out of range
    assert c["features"]["liner"]["status"] == "present"  # image page: no text layer, left alone


def test_drop_unverified_missing_material_resets_ram():
    pages = [{"page": 1, "mode": "layout_text", "text": "cap", "chars": 3}]
    c = {"name": "cap", "material": _f("HDPE", "HDPE"), "features": {}, "ram_category": "plastic"}
    extract.drop_unverified([c], pages, [])
    assert c["material"] == {"status": "missing"} and c["ram_category"] == "missing"


def test_prompt_quotes_whole_feature_value_and_own_row_only():
    sp = prompt.system_prompt()
    assert '"monolayer, no barrier" (not "no barrier")' in sp and '"print: UV-curable ink"' in sp
    assert "OWN ROW ONLY" in sp and "does not give a separate \"label\" component the material PP" in sp
    assert "shortest span" not in sp


def test_tuning1_s902_misses_would_now_be_dropped_not_scored_untraced():
    pred = json.loads((PRODUCT / "results" / "tuning1" / "S902.json").read_text()) \
        if (PRODUCT / "results" / "tuning1" / "S902.json").exists() else None
    if pred is None:
        pytest.skip("results/ not present")
    man = {e["sheet_id"]: e for e in json.loads((DATA / "manifest.json").read_text())["tuning"]}["S902"]
    texts = score.page_texts_for("S902", TUNING / "S902.pdf", man)
    pages = [{"page": 1, "mode": "layout_text", "text": texts[0], "chars": len(texts[0])}]
    truth = json.loads((DATA / "tuning_truth" / "S902.json").read_text())
    before = score.score_sheet(truth, pred, texts)
    assert before["untraced"] == 2
    extract.drop_unverified(pred["components"], pages, [])
    assert score.score_sheet(truth, pred, texts)["untraced"] == 0


# ---- T-58: price is 30/180 and old ledger rows are repriced from tokens --------------------------------

def _old_ledger(path):
    """Two rows priced at the old 15/120 (stored usd understates), one S-row, as in results/ledger.jsonl."""
    rows = [{"sheet_id": "S001", "input_tokens": 10_000, "output_tokens": 2_000, "usd": 0.39, "model": PRO},
            {"sheet_id": "S001", "input_tokens": 1_000, "output_tokens": 1_000, "usd": 0.135, "model": PRO},
            {"sheet_id": "S002", "input_tokens": 0, "output_tokens": 5_000, "usd": 0.6, "model": PRO}]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_price_table():
    assert B.PRICES == {"gpt-5.4-pro": (30.0, 180.0), "gpt-5-mini": (0.25, 2.00)}
    assert B.usd(1_000_000, 1_000_000, PRO) == pytest.approx(210.0)
    assert B.usd(1_000_000, 1_000_000, MINI) == pytest.approx(2.25)


def test_budget_spent_is_repriced_from_tokens_not_stored_usd(tmp_path):
    _old_ledger(tmp_path / "l.jsonl")
    b = B.Budget(tmp_path / "l.jsonl", model=PRO)
    want = (11_000 * 30 + 8_000 * 180) / 1e6
    assert b.spent_usd == pytest.approx(want) and want == pytest.approx(1.77)
    assert b.spent_usd != pytest.approx(0.39 + 0.135 + 0.6)


def test_score_cost_check_uses_tokens_at_current_price(tmp_path):
    _old_ledger(tmp_path / "l.jsonl")
    per = score.read_ledger_cost(tmp_path / "l.jsonl", {"S001", "S002"})
    assert per["S001"] == pytest.approx((11_000 * 30 + 3_000 * 180) / 1e6)
    assert per["S002"] == pytest.approx(0.9)
    # a sheet whose stored usd passes 0.316 but whose repriced cost fails
    (tmp_path / "m.jsonl").write_text(json.dumps({"sheet_id": "S1", "input_tokens": 0, "output_tokens": 1_500, "usd": 0.18, "model": PRO}) + "\n")
    per = score.read_ledger_cost(tmp_path / "m.jsonl", {"S1"})
    assert per["S1"] == pytest.approx(0.27) and per["S1"] <= 0.316
    (tmp_path / "n.jsonl").write_text(json.dumps({"sheet_id": "S1", "input_tokens": 0, "output_tokens": 1_900, "usd": 0.228, "model": PRO}) + "\n")
    per = score.read_ledger_cost(tmp_path / "n.jsonl", {"S1"})
    assert per["S1"] == pytest.approx(0.342) and per["S1"] > score.USD_PER_SHEET_MAX


# ---- Amendment 6: price follows the model ---------------------------------------------------------------

def _row(model, i=1_000_000, o=1_000_000, sid="S001"):
    return {"sheet_id": sid, "input_tokens": i, "output_tokens": o, "usd": 0.0, "model": model}


def test_mixed_model_ledger_is_priced_per_row(tmp_path):
    l = tmp_path / "l.jsonl"
    l.write_text("".join(json.dumps(r) + "\n" for r in
                         [_row(PRO, sid="S901"), _row(MINI, sid="S001"), _row(MINI, 2_000_000, 0, sid="S002")]))
    b = B.Budget(l, model=MINI)
    assert b.spent_usd == pytest.approx(210.0 + 2.25 + 0.5)
    per = score.read_ledger_cost(l, {"S001", "S002", "S901"})
    assert per == pytest.approx({"S901": 210.0, "S001": 2.25, "S002": 0.5})


@pytest.mark.parametrize("bad", ["", None, "gpt-5.4", "gpt-5-mini-2025-08-07"])
def test_ledger_row_with_unknown_or_empty_model_fails_loudly(tmp_path, bad):
    l = tmp_path / "l.jsonl"
    row = _row(bad)
    if bad is None:
        del row["model"]
    l.write_text(json.dumps(row) + "\n")
    with pytest.raises(B.UnknownModel):
        B.Budget(l, model=MINI)
    with pytest.raises(B.UnknownModel):
        score.read_ledger_cost(l, {"S001"})


def test_unknown_model_cannot_check_or_record(tmp_path):
    with pytest.raises(B.UnknownModel):
        B.Budget(tmp_path / "l.jsonl", model="gpt-9")
    b = B.Budget(tmp_path / "l.jsonl")  # no model: reading is fine, charging is not
    with pytest.raises(B.UnknownModel):
        b.check(1, 1)
    with pytest.raises(B.UnknownModel):
        b.record("S1", 1, 1)


def test_budget_check_and_failed_call_charge_use_the_called_models_price(tmp_path):
    b = B.Budget(tmp_path / "l.jsonl", model=MINI, max_usd=1.0)
    b.check(0, 400_000)  # 0.8 at mini; at pro price this would be refused
    with pytest.raises(B.BudgetExceeded):
        b.check(0, 600_000)  # 1.2
    e = b.record("S1", 10, 1_000_000, estimated=True, note="worst case")  # model defaults to the budget's
    assert e["model"] == MINI and e["usd"] == pytest.approx(2.0 + 0.0000025) and (e["price_in"], e["price_out"]) == (0.25, 2.0)


def test_failed_call_row_is_worst_case_at_mini_price(tmp_path):
    class Boom(providers.FakeProvider):
        def complete(self, *a, **k):
            raise providers.ProviderError("timeout", 100, 6000, may_have_run=True)
    b = B.Budget(tmp_path / "l.jsonl", model=MINI, deployment="gpt-5-mini")
    with pytest.raises(providers.ProviderError):
        extract.extract_pdf(SHEETS / "S001.pdf", Boom(), b, max_output_tokens=6000)
    e = json.loads((tmp_path / "l.jsonl").read_text())
    assert e["model"] == MINI and e["deployment"] == "gpt-5-mini" and e["usd"] == pytest.approx(100 * 0.25e-6 + 6000 * 2e-6)


def test_preflight_with_mini_price_passes_with_8_91_left(tmp_path):
    b = B.Budget(tmp_path / "l.jsonl", model=MINI)
    b.record("tuning", 0, 0, model=PRO)  # seed row shape
    b.spent_usd = 3.091  # tuning1 restated at the pro price
    B.preflight(b, 30, 6000)
    b.spent_usd = 12.0 - 0.5
    with pytest.raises(B.BudgetExceeded, match="short by"):
        B.preflight(b, 30, 6000)


def test_preflight_still_refuses_pro_with_8_91_left(tmp_path):
    b = B.Budget(tmp_path / "l.jsonl", model=PRO)
    b.spent_usd = 3.091
    with pytest.raises(B.BudgetExceeded):
        B.preflight(b, 30, 6000)


def _sheet_cost(l, model, n_in, n_out, nsheets=30):
    rows = [_row(model, n_in, n_out, sid=f"S{i:03d}") for i in range(1, nsheets + 1)]
    l.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return score.read_ledger_cost(l, {r["sheet_id"] for r in rows})


def test_cost_mark_per_row_price(tmp_path):
    per = _sheet_cost(tmp_path / "a.jsonl", MINI, 20_000, 15_000)  # 0.005 + 0.03
    assert max(per.values()) == pytest.approx(0.035) and sum(per.values()) / 30 <= score.USD_PER_SHEET_MAX
    per = _sheet_cost(tmp_path / "b.jsonl", PRO, 20_000, 15_000)  # same tokens at the pro price
    assert sum(per.values()) / 30 > score.USD_PER_SHEET_MAX


def test_deployment_fallback_order():
    base = {"T56_SPEND_APPROVED": "1", "AZURE_OPENAI_ENDPOINT": "https://x"}
    both = dict(base, T56_DEPLOYMENT=PRO, AZURE_OPENAI_DEPLOYMENT_MINI=MINI)
    p = providers.AzureResponsesProvider(env=both)
    assert (p.deployment, p.price_model) == (PRO, PRO)
    p = providers.AzureResponsesProvider(env=dict(base, AZURE_OPENAI_DEPLOYMENT_MINI=MINI))
    assert (p.deployment, p.price_model) == (MINI, MINI)
    assert providers.AzureResponsesProvider(env=both, deployment=MINI).deployment == MINI  # explicit argument first
    with pytest.raises(ValueError, match="no deployment"):  # no hard-coded pro default
        providers.AzureResponsesProvider(env=base)
    with pytest.raises(ValueError, match="no price"):
        providers.AzureResponsesProvider(env=dict(base, T56_DEPLOYMENT="gpt-9-turbo"))


def test_unknown_deployment_refuses_the_run(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("T56_SPEND_APPROVED", "1")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x")
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_MINI", raising=False)
    monkeypatch.setenv("T56_DEPLOYMENT", "mystery")
    assert run.main(["--set", "tuning", "--provider", "azure", "--out", str(tmp_path / "o")]) == 2
    assert "refused" in capsys.readouterr().err
    monkeypatch.delenv("T56_DEPLOYMENT")
    assert run.main(["--set", "tuning", "--provider", "azure", "--out", str(tmp_path / "o")]) == 2


def test_run_log_and_ledger_record_the_deployment(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("T56_MAX_OUTPUT_TOKENS", raising=False)
    assert run.main(["--set", "tuning", "--provider", "fake", "--out", str(tmp_path / "o"), "--no-score"]) == 0
    assert "deployment gpt-5-mini" in capsys.readouterr().out
    info = json.loads((tmp_path / "o" / "run.json").read_text())
    assert info["deployment"] == "gpt-5-mini" and info["usd_per_m_out"] == 2.0 and info["max_output_tokens"] == 6000
    rows = _ledger(tmp_path / "o" / "ledger.jsonl")
    assert rows and all(r["model"] == MINI and r["deployment"] == "gpt-5-mini" for r in rows)


def test_azure_ledger_row_uses_price_name_not_served_model_name(nb, tmp_path):
    body = json.dumps({"status": "completed", "model": "gpt-5-mini-2025-08-07",
                       "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"components": []}'}]}],
                       "usage": {"input_tokens": 100, "output_tokens": 50}}).encode()
    p = providers.AzureResponsesProvider(env=dict(ENV, T56_DEPLOYMENT=MINI), transport=lambda r, t: (200, {}, body))
    b = B.Budget(tmp_path / "l.jsonl", model=p.price_model, deployment=p.deployment)
    extract.extract_pdf(SHEETS / "S001.pdf", p, b)
    row = _ledger(tmp_path / "l.jsonl")[0]
    assert row["model"] == MINI and row["served_model"] == "gpt-5-mini-2025-08-07"
    assert B.Budget(tmp_path / "l.jsonl", model=MINI).spent_usd == pytest.approx(100 * 0.25e-6 + 50 * 2e-6)


def test_max_output_tokens_env_and_flag():
    assert run.resolve_max_output_tokens(None, env={}) == 6000
    assert run.resolve_max_output_tokens(None, env={"T56_MAX_OUTPUT_TOKENS": "16000"}) == 16000
    assert run.resolve_max_output_tokens(9000, env={"T56_MAX_OUTPUT_TOKENS": "16000"}) == 9000
    for bad in ("abc", "10", "0"):
        with pytest.raises(ValueError):
            run.resolve_max_output_tokens(None, env={"T56_MAX_OUTPUT_TOKENS": bad})


def test_incomplete_response_is_reported_billed_and_written_as_missing(tmp_path, capsys):
    inc = json.dumps({"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
                      "usage": {"input_tokens": 900, "output_tokens": 6000}}).encode()
    p = providers.AzureResponsesProvider(env=dict(ENV, T56_DEPLOYMENT=MINI), transport=lambda r, t: (200, {}, inc))
    with pytest.raises(providers.ProviderError, match="incomplete: output budget exhausted") as e:
        p.complete("s", X, 6000, budget=B.Budget(tmp_path / "x.jsonl", model=MINI))
    assert e.value.output_tokens == 6000 and not e.value.fatal
    # through the CLI: billed in the ledger, sheet written with no components and a warning, run continues
    class P(providers.FakeProvider):
        def complete(self, s, parts, m, **kw):
            raise providers.ProviderError("incomplete: output budget exhausted", 900, 6000)
    import pytest as _p
    mp = _p.MonkeyPatch()
    mp.setattr(run, "make_provider", lambda name: P())
    try:
        rc = run.main(["--set", "tuning", "--provider", "fake", "--out", str(tmp_path / "o"), "--no-score"])
    finally:
        mp.undo()
    assert rc == 0
    pred = json.loads((tmp_path / "o" / "S901.json").read_text())
    assert pred["components"] == [] and "incomplete" in pred["warnings"][0]
    rows = _ledger(tmp_path / "o" / "ledger.jsonl")
    assert len(rows) == 5 and rows[0]["output_tokens"] == 6000 and rows[0]["model"] == MINI
    assert "without an answer" in capsys.readouterr().err


# ---- served model must match the price model (review T-56-mini) ----------------------------------------

@pytest.mark.parametrize("served,ok", [
    ("gpt-5-mini", True), ("gpt-5-mini-2025-08-07", True),
    ("gpt-5-mini-pro", False), ("gpt-5-mini-2025-08", False), ("gpt-5-mini-2025-08-07-x", False),
    ("gpt-5.4-pro-2026-03-05", False), ("gpt-5", False), ("", False), (None, False)])
def test_served_model_matches(served, ok):
    assert B.served_model_matches(MINI, served) is ok


def _served_provider(served, tmp_path):
    inner = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"components": []}'}]}],
             "usage": {"input_tokens": 1000, "output_tokens": 500}}
    if served is not None:
        inner["model"] = served
    p = providers.AzureResponsesProvider(env=dict(ENV, T56_DEPLOYMENT=MINI),
                                         transport=lambda r, t: (200, {}, json.dumps(inner).encode()))
    return p, B.Budget(tmp_path / "l.jsonl", model=p.price_model, deployment=p.deployment)


@pytest.mark.parametrize("served", ["gpt-5-mini", "gpt-5-mini-2025-08-07"])
def test_served_model_match_is_priced_at_mini(tmp_path, served):
    p, b = _served_provider(served, tmp_path)
    extract.extract_pdf(SHEETS / "S001.pdf", p, b)
    row = _ledger(tmp_path / "l.jsonl")[0]
    assert row["model"] == MINI and row["usd"] == pytest.approx(1000 * 0.25e-6 + 500 * 2e-6)


@pytest.mark.parametrize("served", ["gpt-5.4-pro-2026-03-05", "gpt-5-mini-pro", None])
def test_served_model_mismatch_charges_most_expensive_and_is_fatal(tmp_path, served):
    p, b = _served_provider(served, tmp_path)
    with pytest.raises(providers.ProviderError, match="served model mismatch") as e:
        extract.extract_pdf(SHEETS / "S001.pdf", p, b)
    assert e.value.fatal
    row = _ledger(tmp_path / "l.jsonl")[0]
    assert row["model"] == PRO and row["usd"] == pytest.approx(1000 * 30e-6 + 500 * 180e-6)
    assert row["served_model"] == (served or "") and "does not match" in row["note"]


def test_served_model_mismatch_stops_the_run_with_exit_5_after_one_sheet(monkeypatch, tmp_path, capsys):
    p, _ = _served_provider("gpt-5.4-pro-2026-03-05", tmp_path)
    monkeypatch.setattr(run, "make_provider", lambda name: p)
    rc = run.main(["--set", "tuning", "--provider", "azure", "--out", str(tmp_path / "o"), "--no-score",
                   "--ledger", str(tmp_path / "l2.jsonl")])
    assert rc == 5 and "served model mismatch" in capsys.readouterr().err
    assert len(_ledger(tmp_path / "l2.jsonl")) == 1


def test_low_and_minimal_efforts_accepted_medium_default():
    for e in ("minimal", "low"):
        assert providers.AzureResponsesProvider(env=dict(ENV, T56_DEPLOYMENT=MINI), reasoning_effort=e).reasoning_effort == e
    assert providers.AzureResponsesProvider(env=ENV).reasoning_effort == "medium"
