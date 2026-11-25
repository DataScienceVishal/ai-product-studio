import json
from pathlib import Path

import httpx
import pytest

import budget as b
import extract as e
import extract_config as cfg

DATA = Path(__file__).resolve().parents[1] / "data" / "dev"


def ok_body(lines=1, status="completed"):
    page = {"supplier_name": None, "invoice_number": None, "invoice_date": None, "is_credit_note": None,
            "lines": [{"description": f"X{i}", "pack_size": "", "unit": "each", "qty": 1, "unit_price": 1.0, "line_total": 1.0,
                       "vat_rate": 0} for i in range(lines)], "totals": {"net": None, "vat": None, "gross": None}}
    return {"status": status, "model": "gpt-5-mini", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(page)}]}],
            "usage": {"input_tokens": 1500, "output_tokens": 700}}


class Scripted:
    """A provider that plays back a list of responses (or exceptions) and counts calls."""
    deployment, effort = "scripted", "low"

    def __init__(self, script):
        self.script, self.calls, self.caps = list(script), 0, []

    def call(self, payload, meta, timeout):
        self.calls += 1
        self.caps.append(payload["max_output_tokens"])
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return e.FakeResponse(*item)


META = {"page_id": "DEV-008_p1", "invoice_id": "DEV-008", "page_no": 1, "truth_dir": str(DATA)}
PAGE = DATA / "DEV-008_p1.png"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(e.time, "sleep", lambda s: None)


def run(script, tmp_path, max_usd=5.0):
    prov = Scripted(script)
    bud = b.Budget(tmp_path / "l.jsonl", max_usd=max_usd)
    return e.extract_page(PAGE, META, prov, bud), prov, bud


def test_happy_path_records_tokens_cost_latency(tmp_path):
    rec, prov, bud = run([(200, ok_body())], tmp_path)
    assert rec["status"] == "ok" and rec["retries"] == 0 and prov.caps == [16000]
    assert rec["input_tokens"] == 1500 and rec["output_tokens"] == 700
    assert rec["cost_usd"] == pytest.approx(1500 * 0.25e-6 + 700 * 2e-6)
    assert bud.spent_usd == pytest.approx(rec["cost_usd"])


def test_length_stop_retries_once_at_32k(tmp_path):
    truncated = (200, {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
                       "usage": {"input_tokens": 1500, "output_tokens": 16000}})
    rec, prov, bud = run([truncated, (200, ok_body())], tmp_path)
    assert rec["status"] == "ok" and rec["retries"] == 1 and prov.caps == [16000, 32000]
    assert rec["cost_usd"] == pytest.approx(1500 * 0.25e-6 + 16000 * 2e-6 + 1500 * 0.25e-6 + 700 * 2e-6)  # both attempts billed


def test_invalid_json_then_failure_is_recorded_not_dropped(tmp_path):
    bad = (200, {"status": "completed", "model": "gpt-5-mini", "output": [{"type": "message", "content": [{"type": "output_text", "text": "{nope"}]}],
                 "usage": {"input_tokens": 1500, "output_tokens": 300}})
    rec, prov, _ = run([bad, bad], tmp_path)
    assert rec["status"] == "failed" and rec["reason"] == "invalid_json" and prov.calls == 2 and rec["data"] is None


def test_timeout_is_charged_worst_case_and_retried(tmp_path):
    rec, prov, bud = run([httpx.ReadTimeout("slow"), (200, ok_body())], tmp_path)
    assert rec["status"] == "ok" and rec["attempts"][0]["outcome"] == "timeout"
    assert rec["attempts"][0]["output_tokens"] == 16000 and bud.spent_usd > 16000 * 2e-6


def test_transient_429_does_not_use_the_32k_retry(tmp_path):
    rec, prov, _ = run([(429, {}), (503, {}), (200, ok_body())], tmp_path)
    assert rec["status"] == "ok" and rec["retries"] == 0 and prov.caps == [16000, 16000, 16000]


def test_auth_failure_stops_the_run(tmp_path):
    with pytest.raises(e.FatalError):
        run([(401, {})], tmp_path)


def test_budget_guard_aborts_before_the_call(tmp_path):
    prov = Scripted([(200, ok_body())])
    bud = b.Budget(tmp_path / "l.jsonl", max_usd=0.01)  # worst case 16k out is 0.032: refused
    with pytest.raises(b.BudgetExceeded):
        e.extract_page(PAGE, META, prov, bud)
    assert prov.calls == 0


def test_budget_guard_checks_the_32k_retry_separately(tmp_path):
    truncated = (200, {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
                       "usage": {"input_tokens": 1500, "output_tokens": 16000}})
    prov = Scripted([truncated, (200, ok_body())])
    bud = b.Budget(tmp_path / "l.jsonl", max_usd=0.07)  # first call fits (0.033), the 32k retry's worst case (0.064) does not
    with pytest.raises(b.BudgetExceeded):
        e.extract_page(PAGE, META, prov, bud)
    assert prov.calls == 1


def test_schema_is_strict_and_request_never_uses_pro(tmp_path, monkeypatch):
    payload = e.build_payload("dep", b"x", "image/png", 16000, "low")
    fmt = payload["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and payload["store"] is False
    assert cfg.CONFIG["deployment_env"] == "AZURE_OPENAI_DEPLOYMENT_MINI"
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.invalid/openai/v1/responses")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_MINI", "mini-dep")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "pro-dep")
    p = e.AzureProvider()
    assert p.deployment == "mini-dep" and p.url == "https://example.invalid/openai/v1/responses"


def test_image_is_downscaled_to_2048(tmp_path):
    from PIL import Image
    big = tmp_path / "big.png"
    Image.new("RGB", (3000, 1000), "white").save(big)
    data, mime = e.prepare_image(big, 2048)
    import io
    assert max(Image.open(io.BytesIO(data)).size) == 2048 and mime == "image/png"


def test_merge_pages_in_code():
    def page(n, lines, totals, status="ok"):
        return {"page_no": n, "status": status, "data": {"supplier_name": "S" if n == 1 else None, "invoice_number": "1", "invoice_date": None,
                                                         "is_credit_note": False, "lines": lines, "totals": totals} if status == "ok" else None}
    t0 = {"net": None, "vat": None, "gross": None}
    m = e.merge_pages([page(2, [{"description": "b"}], {"net": 1, "vat": 0, "gross": 1}), page(1, [{"description": "a"}], t0), page(3, [], t0, "failed")])
    assert [ln["description"] for ln in m["lines"]] == ["a", "b"] and m["totals"]["gross"] == 1
    assert m["failed_pages"] == [3] and m["supplier_name"] == "S"


def test_fake_run_end_to_end(tmp_path):
    out = tmp_path / "out"
    assert e.main(["--set", "dev", "--provider", "fake", "--out", str(out)]) == 0
    assert len(list(out.glob("DEV-*_p*.json"))) == 14
    import score
    res = score.score_set(DATA, out)
    assert 0.5 < res["metrics"]["overall"]["accuracy"] < 1.0  # injected errors are visible to the scorer


def test_test_set_refused_without_frozen_config(tmp_path, monkeypatch):
    monkeypatch.setattr(e, "HERE", tmp_path)  # no FROZEN.json, no KILL-TEST.md next to it
    assert e.main(["--set", "test", "--provider", "fake", "--out", str(tmp_path / "o")]) == 2


def test_frozen_hash_changes_with_prompt(monkeypatch):
    h = cfg.frozen_hash()
    monkeypatch.setattr(cfg, "PROMPT", cfg.PROMPT + " ")
    assert cfg.frozen_hash() != h
