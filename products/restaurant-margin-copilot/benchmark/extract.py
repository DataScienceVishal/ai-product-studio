"""One model call per page image: frozen prompt, strict JSON-schema output, spend guard, per-call logging.

  python extract.py --set dev --provider azure --out results/dev1 --limit-pages 3
  python extract.py --set dev --provider fake  --out results/fake

Azure path follows products/_starter/backend/app/ai.py: v1 Responses API at $AZURE_OPENAI_ENDPOINT, deployment from
$AZURE_OPENAI_DEPLOYMENT_MINI (the mini one only), key $AZURE_OPENAI_API_KEY sent as the `api-key` header (in cloud runs a
network secret swaps in the real key; this code never prints it). chat/completions is refused on that endpoint.

Rules from KILL-TEST.md: 16,000 output tokens; a page that stops on length, returns invalid JSON or times out (180 s) gets one
retry at 32,000; if that fails too the page is recorded as failed and the scorer counts all its lines wrong. Failed pages are
never dropped. The merge of a page set into an invoice is done in code (merge_pages); the model never adds anything up.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image

import budget as budget_mod
import extract_config as cfg

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DEFAULT_LEDGER = HERE / "results" / "ledger.jsonl"
_SUFFIXES = ("/openai/v1/chat/completions", "/openai/v1/responses", "/openai/v1", "/openai")


class FatalError(RuntimeError):
    """Configuration or credential problem: stop the whole run, do not count it as a page failure."""


# ------------------------------------------------------------------ images

def prepare_image(path: Path, max_edge: int) -> tuple[bytes, str]:
    """Bytes and mime type of the page, downscaled so the long edge is at most max_edge px."""
    img = Image.open(path)
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    if max(img.size) <= max_edge:
        return path.read_bytes(), mime
    scale = max_edge / max(img.size)
    img = img.convert("RGB").resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    if mime == "image/jpeg":
        img.save(buf, "JPEG", quality=92)
    else:
        img.save(buf, "PNG", optimize=True)
    return buf.getvalue(), mime


def estimate_input_tokens() -> int:
    return cfg.CONFIG["est_image_tokens"] + len(cfg.PROMPT) // 3 + len(json.dumps(cfg.SCHEMA)) // 3 + 200


def build_payload(deployment: str, image: bytes, mime: str, max_output_tokens: int, effort: str) -> dict:
    url = f"data:{mime};base64," + base64.b64encode(image).decode()
    payload = {
        "model": deployment, "instructions": cfg.PROMPT, "max_output_tokens": max_output_tokens, "store": False,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "Extract this page."},
                                                {"type": "input_image", "image_url": url, "detail": cfg.CONFIG["image_detail"]}]}],
        "text": {"format": {"type": "json_schema", "name": "invoice_page", "schema": cfg.SCHEMA, "strict": True}},
    }
    if effort:
        payload["reasoning"] = {"effort": effort}
    return payload


# ------------------------------------------------------------------ providers

class AzureProvider:
    def __init__(self, effort: str | None = None):
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
        self.deployment = os.environ.get(cfg.CONFIG["deployment_env"], "").strip()
        if not endpoint or not self.deployment:
            raise FatalError(f"AZURE_OPENAI_ENDPOINT and {cfg.CONFIG['deployment_env']} must be set")
        base = endpoint.rstrip("/")
        for s in _SUFFIXES:
            if base.lower().endswith(s):
                base = base[: -len(s)]
                break
        self.url = base + "/openai/v1/responses"
        # "proxy-injected" is the placeholder; the environment's network secret adds the real key to the request.
        self.headers = {"api-key": os.environ.get("AZURE_OPENAI_API_KEY") or "proxy-injected", "Content-Type": "application/json"}
        self.client = httpx.Client()
        self.effort = effort if effort is not None else cfg.CONFIG["reasoning_effort"]

    def call(self, payload: dict, meta: dict, timeout: float) -> httpx.Response:
        return self.client.post(self.url, json=payload, headers=self.headers, timeout=timeout)


class FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code, self._body, self.headers = status_code, body, {}

    def json(self):
        return self._body


class FakeProvider:
    """Returns ground truth for a page with deterministic injected errors, through the same response format and parse path."""
    deployment = "fake-mini"

    def __init__(self, truth_dir: Path | None = None, seed: int = 7, error_rate: float = 0.06, effort: str | None = None):
        self.truth_dir, self.seed, self.error_rate = truth_dir, seed, error_rate
        self.effort = effort or "low"

    def call(self, payload: dict, meta: dict, timeout: float) -> FakeResponse:
        truth = json.loads((Path(meta["truth_dir"]) / f"{meta['invoice_id']}.json").read_text())
        rng = random.Random(f"{self.seed}:{meta['page_id']}:{payload['max_output_tokens']}")
        if payload["max_output_tokens"] <= cfg.CONFIG["max_output_tokens"] and rng.random() < 0.04:  # first attempt runs out
            return FakeResponse(200, {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
                                      "usage": {"input_tokens": 1500, "output_tokens": payload["max_output_tokens"]}})
        page = meta["page_no"]
        lines = []
        for ln in truth["lines"]:
            if ln["page"] != page:
                continue
            ln = {k: ln[k] for k in ("description", "pack_size", "unit", "qty", "unit_price", "line_total", "vat_rate")}
            r = rng.random()
            if r < self.error_rate * 0.4:
                ln["unit_price"] = round(ln["unit_price"] * 1.1, 2)
            elif r < self.error_rate * 0.6:
                continue  # dropped line
            elif r < self.error_rate * 0.8:
                ln["vat_rate"] = 20 if ln["vat_rate"] == 0 else 0
            elif r < self.error_rate:
                ln["unit"], ln["pack_size"] = "each", ""
            lines.append(ln)
            if rng.random() < self.error_rate * 0.2:  # extra invented line
                lines.append({**ln, "description": ln["description"] + " X", "qty": 1.0})
        last = page == truth["pages"]
        t = truth["totals"]
        body = {"supplier_name": truth["supplier"] if page == 1 else None, "invoice_number": truth["invoice_no"] if page == 1 else None,
                "invoice_date": truth["date"] if page == 1 else None, "is_credit_note": truth["credit_note"] if page == 1 else None,
                "lines": lines, "totals": {"net": t["net"], "vat": t["vat"], "gross": t["gross"]} if last else
                {"net": None, "vat": None, "gross": None}}
        text = json.dumps(body)
        return FakeResponse(200, {"status": "completed", "model": "fake-mini", "_sim_latency": round(8 + rng.random() * 20, 1),
                                  "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
                                  "usage": {"input_tokens": 1500 + len(lines) * 5, "output_tokens": 600 + len(text) // 3}})


# ------------------------------------------------------------------ one page

def parse_response(data) -> tuple[int, int, str, str | None]:
    """(input tokens, output tokens, text, reason there is no usable text)."""
    if not isinstance(data, dict):
        raise ValueError("not an object")
    usage = data.get("usage") or {}
    used_in, used_out = int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)
    if data.get("status") == "incomplete":
        return used_in, used_out, "", (data.get("incomplete_details") or {}).get("reason") or "incomplete"
    parts = [p.get("text") or "" for item in data.get("output") or [] if isinstance(item, dict) and item.get("type") == "message"
             for p in item.get("content") or [] if isinstance(p, dict) and p.get("type") == "output_text"]
    text = "".join(parts).strip()
    return used_in, used_out, text, None if text else "no_output"


def validate_page(obj) -> str | None:
    """None when the object has the schema's shape, else why not. The strict schema should guarantee this; we still check."""
    if not isinstance(obj, dict) or not isinstance(obj.get("lines"), list) or not isinstance(obj.get("totals"), dict):
        return "bad_shape"
    for ln in obj["lines"]:
        if not isinstance(ln, dict):
            return "bad_line"
        for k in ("qty", "unit_price", "line_total", "vat_rate"):
            if not isinstance(ln.get(k), (int, float)) or isinstance(ln.get(k), bool):
                return f"bad_line_{k}"
        if not isinstance(ln.get("description"), str):
            return "bad_line_description"
    return None


def extract_page(image_path: Path, meta: dict, provider, bud: budget_mod.Budget) -> dict:
    """Run one page: attempt 1 at max_output_tokens, one retry at retry_max_output_tokens. Always returns a record."""
    c = cfg.CONFIG
    image, mime = prepare_image(image_path, c["max_long_edge_px"])
    est_in = estimate_input_tokens()
    rec = {"page_id": meta["page_id"], "invoice_id": meta["invoice_id"], "page_no": meta["page_no"], "status": "failed",
           "reason": None, "attempts": [], "latency_s": 0.0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
           "model": None, "data": None}
    caps = [c["max_output_tokens"], c["retry_max_output_tokens"]]
    for attempt_no, cap in enumerate(caps):
        bud.check(est_in, cap, label=f"{meta['page_id']} attempt {attempt_no + 1}")  # raises BudgetExceeded: stops the run
        payload = build_payload(provider.deployment, image, mime, cap, provider.effort)
        att = {"max_output_tokens": cap, "input_tokens": 0, "output_tokens": 0, "latency_s": 0.0, "outcome": None, "http": None}
        t0 = time.monotonic()
        response = None
        for transient in range(c["transient_retries"] + 1):
            try:
                response = provider.call(payload, meta, c["timeout_s"])
            except httpx.ConnectError:  # never reached the service: nothing billed
                response = None
                time.sleep(c["backoff_base_s"] * 2 ** transient * (0 if isinstance(provider, FakeProvider) else 1))
                continue
            except httpx.TransportError as e:  # sent, then lost or timed out: it may have run and been billed
                att["outcome"] = "timeout" if isinstance(e, httpx.TimeoutException) else "transport_error"
                response = None
                break
            if response.status_code == 429 or response.status_code >= 500:
                att["http"] = response.status_code
                response = None
                time.sleep(c["backoff_base_s"] * 2 ** transient * (0 if isinstance(provider, FakeProvider) else 1))
                continue
            break
        att["latency_s"] = round(time.monotonic() - t0, 2)
        if response is None and att["outcome"] is None:
            att["outcome"] = "unavailable"  # connect errors or throttling for every try; nothing billed
        elif response is None:  # timeout or lost after sending: charge the worst case
            e = bud.record(meta["page_id"], est_in, cap, estimated=True, note=att["outcome"])
            att["input_tokens"], att["output_tokens"] = est_in, cap
            rec["cost_usd"] += e["usd"]
        else:
            att["http"] = response.status_code
            if response.status_code in (401, 403):
                raise FatalError(f"credentials rejected (HTTP {response.status_code}); log a hurdle")
            if response.status_code >= 400:
                att["outcome"] = f"http_{response.status_code}"
                rec["attempts"].append(att)
                rec["latency_s"] += att["latency_s"]
                rec["reason"] = att["outcome"]
                break  # a request the service rejects will be rejected again
            try:
                data = response.json()
                used_in, used_out, text, why = parse_response(data)
            except (ValueError, TypeError):  # 200 we cannot read: it may have run, charge the worst case
                data = None
                e = bud.record(meta["page_id"], est_in, cap, estimated=True, note="unreadable 200")
                att["outcome"], att["input_tokens"], att["output_tokens"] = "unreadable", est_in, cap
                rec["cost_usd"] += e["usd"]
            if data is not None:
                if "_sim_latency" in data:
                    att["latency_s"] = data["_sim_latency"]
                e = bud.record(meta["page_id"], used_in, used_out)
                att["input_tokens"], att["output_tokens"] = used_in, used_out
                rec["cost_usd"] += e["usd"]
                rec["model"] = data.get("model")
                if why is not None:
                    att["outcome"] = "length" if why == "max_output_tokens" else why
                else:
                    try:
                        obj = json.loads(text)
                    except ValueError:
                        obj = None
                    bad = "invalid_json" if obj is None else validate_page(obj)
                    if bad:
                        att["outcome"] = bad
                    else:
                        att["outcome"] = "ok"
                        rec["status"], rec["data"] = "ok", obj
        rec["attempts"].append(att)
        rec["latency_s"] += att["latency_s"]
        rec["input_tokens"] += att["input_tokens"]
        rec["output_tokens"] += att["output_tokens"]
        if att["outcome"] == "ok":
            break
    rec["retries"] = max(len(rec["attempts"]) - 1, 0)
    rec["latency_s"] = round(rec["latency_s"], 2)
    rec["cost_usd"] = round(rec["cost_usd"], 6)
    if rec["status"] != "ok":
        rec["reason"] = rec["reason"] or (rec["attempts"][-1]["outcome"] if rec["attempts"] else "no_attempt")
    return rec


# ------------------------------------------------------------------ merge

def merge_pages(records: list[dict]) -> dict:
    """Merge the page records of one invoice in code: lines concatenated, header from the first page that has it, totals
    from the last page that has them. Failed pages contribute nothing and are listed in failed_pages."""
    ok = sorted((r for r in records if r["status"] == "ok"), key=lambda r: r["page_no"])
    merged = {"supplier_name": None, "invoice_number": None, "invoice_date": None, "is_credit_note": None, "lines": [],
              "totals": {"net": None, "vat": None, "gross": None},
              "failed_pages": sorted(r["page_no"] for r in records if r["status"] != "ok")}
    for r in ok:
        d = r["data"]
        for k in ("supplier_name", "invoice_number", "invoice_date", "is_credit_note"):
            if merged[k] is None and d.get(k) is not None:
                merged[k] = d[k]
        merged["lines"] += [{**ln, "page": r["page_no"]} for ln in d["lines"]]
        for k in ("net", "vat", "gross"):
            if d["totals"].get(k) is not None:
                merged["totals"][k] = d["totals"][k]
    return merged


# ------------------------------------------------------------------ run

def page_jobs(set_dir: Path):
    for tj in sorted(set_dir.glob("*.json")):
        if tj.name == "MANIFEST.json":
            continue
        t = json.loads(tj.read_text())
        for n, fname in enumerate(t["images"], 1):
            yield {"invoice_id": t["id"], "page_no": n, "page_id": f"{t['id']}_p{n}", "truth_dir": str(set_dir)}, set_dir / fname


def check_test_allowed() -> None:
    """The test set needs: KILL-TEST.md committed, a frozen prompt+config whose hash matches, and the test data."""
    kill = HERE.parent / "KILL-TEST.md"
    frozen = HERE / "FROZEN.json"
    if not kill.exists():
        raise FatalError("refused: KILL-TEST.md is not in the repo; it must be committed before any TEST run")
    if not frozen.exists():
        raise FatalError("refused: FROZEN.json missing; run freeze.py after prompt work on DEV, and commit it")
    if json.loads(frozen.read_text()).get("sha256") != cfg.frozen_hash():
        raise FatalError("refused: extract_config.py differs from FROZEN.json (prompt/schema/config changed after freezing)")
    if not (DATA / "test" / "MANIFEST.json").exists():
        raise FatalError("refused: data/test not generated (the held-out layouts are written after the freeze)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set", choices=["dev", "test"], required=True)
    ap.add_argument("--provider", choices=["azure", "fake"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", help=f"shared spend ledger (default {DEFAULT_LEDGER}; fake runs use <out>/ledger.jsonl)")
    ap.add_argument("--limit-pages", type=int, help="stop after this many pages (smoke runs)")
    ap.add_argument("--only", nargs="+", help="page ids to run, e.g. DEV-002_p1")
    ap.add_argument("--reasoning-effort", choices=["low", "medium"], help="dev only; test uses the frozen value")
    ap.add_argument("--resume", action="store_true", help="skip pages that already have a result file in --out")
    ap.add_argument("--workers", type=int, default=1, help="parallel pages; the budget check is per call, so overshoot is at most workers x one worst case")
    ap.add_argument("--max-usd", type=float, default=budget_mod.MAX_USD)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        if a.set == "test":
            check_test_allowed()
            if a.reasoning_effort:
                raise FatalError("refused: --reasoning-effort is not allowed on the test set; it is frozen")
        provider = AzureProvider(a.reasoning_effort) if a.provider == "azure" else FakeProvider(effort=a.reasoning_effort)
        ledger = Path(a.ledger) if a.ledger else (DEFAULT_LEDGER if a.provider == "azure" else out / "ledger.jsonl")
        bud = budget_mod.Budget(ledger, cfg.CONFIG["price_model"], a.max_usd)
    except FatalError as e:
        print(e, file=sys.stderr)
        return 2
    run_info = {"set": a.set, "provider": a.provider, "deployment": provider.deployment, "config_sha256": cfg.frozen_hash(),
                "reasoning_effort": provider.effort, "config": cfg.CONFIG, "max_usd": a.max_usd}
    (out / "run.json").write_text(json.dumps(run_info, indent=1) + "\n")
    jobs = []
    for meta, path in page_jobs(DATA / a.set):
        if a.only and meta["page_id"] not in a.only:
            continue
        if a.resume and (out / f"{meta['page_id']}.json").exists():
            continue
        jobs.append((meta, path))
    if a.limit_pages is not None:
        jobs = jobs[: a.limit_pages]

    def work(job):
        meta, path = job
        rec = extract_page(path, meta, provider, bud)
        (out / f"{meta['page_id']}.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(f"{meta['page_id']}: {rec['status']} in {rec['latency_s']}s, {rec['input_tokens']} in / {rec['output_tokens']} out, "
              f"${rec['cost_usd']:.4f}, retries {rec['retries']}; ledger total ${bud.spent_usd:.4f}", flush=True)

    done = 0
    try:
        with ThreadPoolExecutor(max_workers=max(a.workers, 1)) as pool:
            for _ in pool.map(work, jobs):
                done += 1
    except budget_mod.BudgetExceeded as e:
        print(f"STOP: {e}. Unscored pages will count as wrong.", file=sys.stderr)
        return 3
    except FatalError as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 2
    print(f"done: {done} pages; cumulative spend ${bud.spent_usd:.4f} of ${a.max_usd:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
