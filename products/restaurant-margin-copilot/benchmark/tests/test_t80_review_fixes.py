"""T-80 review fixes: guards around the single TEST run. Fake provider only; no model calls."""
import json
from pathlib import Path

import pytest

import extract as e
import score as s
from test_extract import ok_body, run

BENCH = Path(__file__).resolve().parents[1]


def test_args(tmp_path, *extra, out="out"):
    return ["--set", "test", "--provider", "fake", "--out", str(tmp_path / out), "--ledger", str(tmp_path / "l.jsonl"), *extra]


test_args.__test__ = False


def test_max_usd_above_hard_cap_is_refused(tmp_path, capsys):
    rc = e.main(["--set", "dev", "--provider", "fake", "--out", str(tmp_path / "o"), "--max-usd", "5.01"])
    assert rc == 2
    assert "hard cap" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()


def test_max_usd_at_cap_is_accepted_and_workers_recorded(tmp_path):
    rc = e.main(["--set", "dev", "--provider", "fake", "--out", str(tmp_path / "o"), "--max-usd", "5", "--limit-pages", "1",
                 "--workers", "2"])
    assert rc == 0
    info = json.loads((tmp_path / "o" / "run.json").read_text())
    assert info["workers"] == 2 and info["max_usd"] == 5.0


def test_test_set_refuses_only_and_limit_pages(tmp_path, capsys):
    assert e.main(test_args(tmp_path, "--limit-pages", "1")) == 2
    assert e.main(test_args(tmp_path, "--only", "TEST-001_p1", out="o2")) == 2
    assert "not allowed on the test set" in capsys.readouterr().err
    assert not (tmp_path / "out").exists() and not (tmp_path / "o2").exists()


def test_test_set_refuses_existing_out_without_resume(tmp_path, capsys):
    (tmp_path / "out").mkdir()
    assert e.main(test_args(tmp_path)) == 2
    assert "already exists" in capsys.readouterr().err


def test_test_set_resume_never_overwrites_existing_page(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    first = sorted((BENCH / "data" / "test").glob("TEST-*.json"))[0]
    pid = f"{json.loads(first.read_text())['id']}_p1"
    sentinel = out / f"{pid}.json"
    sentinel.write_text('{"sentinel": true}')
    calls = []

    def fake_extract(path, meta, prov, bud):
        calls.append(meta["page_id"])
        return {"page_id": meta["page_id"], "status": "failed", "latency_s": 0, "input_tokens": 0, "output_tokens": 0,
                "cost_usd": 0, "retries": 0}

    monkeypatch.setattr(e, "extract_page", fake_extract)
    assert e.main(test_args(tmp_path, "--resume", "--workers", "3")) == 0
    assert pid not in calls and len(calls) == 65
    assert json.loads(sentinel.read_text()) == {"sentinel": True}
    assert json.loads((out / "run.json").read_text())["workers"] == 3


def test_response_from_other_model_is_not_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(e.time, "sleep", lambda s: None)
    body = ok_body()
    body["model"] = "gpt-5"
    rec, _, _ = run([(200, body), (200, body)], tmp_path)
    assert rec["status"] != "ok" and rec["attempts"][0]["outcome"] == "wrong_model"


def test_test_set_cost_comes_from_ledger_test_rows(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "TEST-001_p1.json").write_text(json.dumps({"page_id": "TEST-001_p1", "invoice_id": "TEST-001", "page_no": 1, "status": "failed",
                                                      "latency_s": 1.0, "input_tokens": 1, "output_tokens": 1, "cost_usd": 99.0,
                                                      "retries": 0, "data": None}))
    led = tmp_path / "l.jsonl"
    rows = [{"label": "DEV-001_p1", "usd": 1.0}, {"label": "TEST-001_p1 attempt 1", "usd": 0.5}, {"label": "TEST-002_p1", "usd": 0.66}]
    led.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    m = s.score_set(BENCH / "data" / "test", ext, led)["metrics"]
    assert m["pages"] == 66
    assert m["cost_total_usd"] == pytest.approx(1.16)
    assert m["cost_per_page_usd"] == pytest.approx(1.16 / 66, abs=1e-5)
    assert m["cost_from_page_records_usd"] == 99.0


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "0", "-1"])
def test_max_usd_non_finite_or_non_positive_is_refused(tmp_path, capsys, bad):
    rc = e.main(["--set", "dev", "--provider", "fake", "--out", str(tmp_path / "o"), f"--max-usd={bad}", "--limit-pages", "1"])
    assert rc == 2
    assert "finite positive" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0.0, -1.0, 5.01])
def test_budget_rejects_bad_cap(tmp_path, bad):
    import budget as b
    with pytest.raises(ValueError):
        b.Budget(tmp_path / "l.jsonl", max_usd=bad)


def test_resume_keeps_first_started_utc(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "run.json").write_text(json.dumps({"started_utc": "2026-01-01T00:00:00+00:00"}))
    monkeypatch.setattr(e, "extract_page", lambda path, meta, prov, bud: {
        "page_id": meta["page_id"], "status": "failed", "latency_s": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0, "retries": 0})
    assert e.main(test_args(tmp_path, "--resume")) == 0
    info = json.loads((out / "run.json").read_text())
    assert info["started_utc"] == "2026-01-01T00:00:00+00:00"
    assert len(info["resumed_utc"]) == 1


def test_test_set_cost_missing_ledger_is_an_error(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    with pytest.raises(FileNotFoundError):
        s.score_set(BENCH / "data" / "test", ext, tmp_path / "missing.jsonl")
