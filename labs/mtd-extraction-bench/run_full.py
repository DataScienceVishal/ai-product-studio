"""Full benchmark runner (T-12). Max 15 new model calls and $11.50 new spend, enforced by budget.Budget.
Deterministic extraction for PDF/CSV/xlsx; model only categorises (batch per document). Images: model transcribes + categorises.
Never touches the pilot. `--score-only` re-scores saved raw output with no API calls."""
import json, os, sys, time, base64, urllib.request, urllib.error, concurrent.futures as cf
from pathlib import Path
import gen, gen2, score, calib
from budget import Budget, BudgetRefused

HERE = Path(__file__).parent
DATA, RES = HERE / "data_full", HERE / "results"
RAW = RES / "full_raw"
MAX_OUT_TEXT, MAX_OUT_IMAGE = 6000, 14000
IMG_EFFORTS = ["minimal", "medium"]     # probed in order on the first image doc

CAT_HELP = ("turnover=business income; cost_of_goods=materials/stock; wages=staff pay; car_van_travel; premises=rent/utilities; "
            "repairs; phone_office=phone/stationery/software; advertising; interest_bank_charges; professional_fees=accountant etc; "
            "other_expenses=other allowable business costs; drawings_personal=owner's private spending; transfer=between own accounts or till float")


def cat_prompt(persona, lines):
    body = "\n".join(f"{i}|{l['date']}|{l['description']}|{l['amount']}" for i, l in enumerate(lines))
    return (f"Categorise bank/sheet lines for a UK sole trader ({gen2.PERSONAS[persona]['label']}) preparing HMRC Making Tax Digital "
            f"quarterly updates. Categories: {gen.CATS}. {CAT_HELP}. Lines that mix personal and business use, home-office costs and cash "
            f"withdrawals are ambiguous: pick the most likely category and give a LOWER confidence (0 to 1).\n"
            'Return ONLY compact JSON: {"c":[[index,"category",confidence],...]} with one entry per line, no commentary.\n\nLINES (index|date|description|amount):\n' + body)


def img_prompt(persona):
    import run_pilot
    return run_pilot.PROMPT.replace("a UK sole trader", f"a UK sole trader ({gen2.PERSONAS[persona]['label']})", 1)


def text_of(resp):
    return "".join(c.get("text", "") for o in resp.get("output", []) if o.get("type") == "message"
                   for c in o.get("content", []) if c.get("type") == "output_text")


def http_call(content, max_out, effort, timeout=420):
    body = {"model": os.environ["AZURE_OPENAI_DEPLOYMENT"], "max_output_tokens": max_out,
            "input": [{"role": "user", "content": content}]}
    if effort:
        body["reasoning"] = {"effort": effort}
    req = urllib.request.Request(os.environ["AZURE_OPENAI_ENDPOINT"], data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def guarded_call(bud, label, content, est_in, max_out, effort):
    """One counted attempt. 400 = rejected before generation (no tokens). Timeout/transport = unknown: bill worst case.
    Returns (resp|None, error|None)."""
    worst = bud.reserve(est_in, max_out)
    try:
        resp = http_call(content, max_out, effort)
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:300]
        # 4xx = rejected before generation (no tokens). 5xx = unknown (the upstream may have generated): bill worst case.
        bud.settle(worst, label, None, charge_worst=e.code >= 500, note=f"HTTP {e.code} effort={effort}")
        return None, f"HTTP {e.code}: {msg}"
    except Exception as e:
        bud.settle(worst, label, None, charge_worst=True, note=f"transport: {type(e).__name__}")
        return None, f"transport error: {type(e).__name__}"
    bud.settle(worst, label, resp.get("usage"), note=f"effort={effort} status={resp.get('status')}")
    return resp, None


def parse_json(text):
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`").removeprefix("json").strip()
    return json.loads(s)


def run_doc(bud, name, meta, effort_state):
    t0 = time.time(); kind = meta["kind"]; persona = meta["persona"]; rec = {"kind": kind}
    if kind in ("scan", "photo"):
        data_url = "data:image/jpeg;base64," + base64.b64encode((DATA / meta["file"]).read_bytes()).decode()
        content = [{"type": "input_text", "text": img_prompt(persona)}, {"type": "input_image", "image_url": data_url}]
        est_in, max_out = 3000, MAX_OUT_IMAGE
        efforts = [effort_state["accepted"]] if effort_state.get("probed") else IMG_EFFORTS + [None]
        resp = err = None
        for eff in efforts:
            resp, err = guarded_call(bud, name, content, est_in, max_out, eff)
            if resp is not None or not (err and err.startswith("HTTP 400") and ("reasoning" in err.lower() or "effort" in err.lower())):
                if resp is not None:
                    effort_state.update(accepted=eff, probed=True)
                break
            rec.setdefault("effort_rejected", []).append(eff)
        rec["effort"] = effort_state.get("accepted")
    else:
        lines = gen2.extract(name, DATA)
        content = [{"type": "input_text", "text": cat_prompt(persona, lines)}]
        est_in, max_out = len(content[0]["text"]) // 3 + 200, MAX_OUT_TEXT
        resp, err = guarded_call(bud, name, content, est_in, max_out, None)
        rec["effort"] = "default"; rec["extracted_lines"] = len(lines)
    rec["latency_s"] = round(time.time() - t0, 1)
    if resp is None:
        rec["error"] = err; return rec, None
    u = resp.get("usage", {})
    rec.update(status=resp.get("status"), input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
               reasoning_tokens=(u.get("output_tokens_details") or {}).get("reasoning_tokens"))
    raw = text_of(resp)
    (RAW / f"{name}.txt").write_text(raw)
    try:
        j = parse_json(raw)
    except Exception as e:
        rec["parse_error"] = str(e)[:150]; return rec, None
    if kind in ("scan", "photo"):
        out = j.get("lines", [])
    else:
        cats = {int(c[0]): c for c in j.get("c", [])}
        out = [{**l, "category": (cats.get(i) or [0, "other_expenses", 0])[1], "confidence": float((cats.get(i) or [0, 0, 0])[2])}
               for i, l in enumerate(lines)]
    (RAW / f"{name}.json").write_text(json.dumps({"lines": out}, indent=1))
    return rec, out


def rules_for(persona):
    tx, _ = gen2.make_txns(persona, gen2.PRIOR_SEED_OFFSET + hash_persona(persona))
    return calib.build_rules(tx)


def hash_persona(p):
    return {"tradesperson": 1, "consultant": 2, "market_stall": 3}[p]


def score_variants(name, meta, lines, threshold=0.8):
    truth = json.loads((DATA / f"{name}.truth.json").read_text())["lines"]
    rules = sheet_rules(meta["persona"]) if meta["kind"] == "xlsx" else rules_for(meta["persona"])
    out = {}
    for tag, kw in [("model_only", None), ("rules_only", dict(use_rules=True, risky_cap=False)),
                    ("rules_and_risky_cap", dict(use_rules=True, risky_cap=True))]:
        ls = lines if kw is None else calib.apply(lines, rules, **kw)
        s = score.score_doc(truth, ls, threshold=threshold)
        out[tag] = s
    return out


def sheet_rules(persona):
    """Prior-quarter sheet vocabulary: the owner's own wording per category, as a reviewer would have corrected it."""
    import random, tempfile
    prior, _ = gen2.make_txns(persona, gen2.PRIOR_SEED_OFFSET + hash_persona(persona))
    with tempfile.TemporaryDirectory() as td:
        gen.write_messy_csv(Path(td) / "p.csv", prior, 5)
    return calib.build_rules([{"description": x["sheet_description"], "category": x["category"]} for x in prior])


def assemble(bud, recs, cap_hit):
    scores, agg = {}, {}
    for name, kind, layout, persona, seed in gen2.PLAN:
        f = RAW / f"{name}.json"
        if not f.exists():
            scores[name] = {"not_run": True}; continue
        lines = json.loads(f.read_text())["lines"]
        meta = {"kind": kind, "persona": persona, "file": json.loads((DATA / f"{name}.truth.json").read_text())["file"]}
        scores[name] = {"kind": kind, "layout": layout, "persona": persona, **score_variants(name, meta, lines)}
    return scores


def main():
    RES.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)
    bud = Budget(RES / "full_budget.json")
    meta = gen2.build(DATA) if not (DATA / "fenwick_trade.truth.json").exists() else {n: {"file": json.loads((DATA / f"{n}.truth.json").read_text())["file"], "kind": k, "layout": l, "persona": p} for n, k, l, p, s in gen2.PLAN}
    recs = {}
    rp = RES / "full_runs.json"
    if rp.exists():
        recs = json.loads(rp.read_text())
    if "--score-only" not in sys.argv:
        todo = [n for n, *_ in gen2.PLAN if not (RAW / f"{n}.json").exists() and n not in recs]
        eff = {}
        order_img = [n for n in todo if meta[n]["kind"] in ("scan", "photo")]
        first, rest = (order_img[0], [n for n in todo if n != order_img[0]]) if order_img else (None, todo)
        cap_hit = False
        def one(n):
            try:
                rec, _ = run_doc(bud, n, meta[n], eff)
            except BudgetRefused as e:
                rec = {"skipped_by_budget_guard": str(e)}
            recs[n] = rec; rp.write_text(json.dumps(recs, indent=1))
            print(n, {k: v for k, v in rec.items()}, f"| total ${bud.usd:.2f} calls {bud.calls}", flush=True)
        if first:
            one(first)        # serial probe: finds the accepted reasoning effort
        with cf.ThreadPoolExecutor(4) as ex:
            list(ex.map(one, rest))
    scores = assemble(bud, recs, False)
    out = {"model": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "pro"), "budget": bud.state(), "runs": recs, "scores": scores,
           "assumptions": score.ASSUMP, "silent_error_cost_s": score.SILENT_ERROR_COST, "threshold": score.THRESHOLD}
    (RES / "full.json").write_text(json.dumps(out, indent=1))
    print("budget", {k: v for k, v in bud.state().items() if k != "log"})


if __name__ == "__main__":
    main()
