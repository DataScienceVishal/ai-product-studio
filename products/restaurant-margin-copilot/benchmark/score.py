"""Score extraction results against ground truth, as defined in KILL-TEST.md section 2.

  python score.py --set dev --extractions results/dev1 [--out results/dev1/score.json] [--report results/dev1/REPORT.md]

A line is correct only if all of these hold against its paired ground-truth line: description similarity >= 0.95 (normalised
Levenshtein after lower-casing and collapsing punctuation), qty exact, pack cost per g/ml/each within 0.5%, unit price and line
total within 0.005, VAT rate exact. Pairing is a one-to-one optimal assignment on description similarity (pairs under 0.5
similarity are not paired). Unpaired predictions are hallucinated lines. Pages with no usable result (failed, or never run
because the budget stopped the run) have no predicted lines, so every ground-truth line on them counts as wrong.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

import extract
from packs import packs_equivalent

HERE = Path(__file__).resolve().parent
PAIR_FLOOR = 0.5  # below this similarity two lines are not the same line
DESC_MIN = 0.95
MONEY_TOL = 0.005


# ------------------------------------------------------------------ matching

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (text or "").lower())).strip()


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a and not b:
        return 1.0
    return 1.0 - levenshtein(a, b) / max(len(a), len(b))


def hungarian(cost: list[list[float]]) -> list[int]:
    """Minimum-cost assignment for a square matrix (O(n^3)); returns the column chosen for each row."""
    n = len(cost)
    INF = float("inf")
    u, v, p, way = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [INF] * (n + 1), [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    result = [0] * n
    for j in range(1, n + 1):
        result[p[j] - 1] = j - 1
    return result


def match_lines(truth: list[dict], pred: list[dict]) -> list[tuple[int, int, float]]:
    """(truth index, predicted index, similarity) pairs, one to one, maximising total description similarity."""
    if not truth or not pred:
        return []
    n = max(len(truth), len(pred))
    sims = [[similarity(t["description"], p["description"]) if i < len(truth) and j < len(pred) else 0.0
             for j, p in enumerate(pred + [None] * (n - len(pred)))] for i, t in enumerate(truth + [None] * (n - len(truth)))]
    cols = hungarian([[1.0 - s for s in row] for row in sims])
    return [(i, j, sims[i][j]) for i, j in enumerate(cols) if i < len(truth) and j < len(pred) and sims[i][j] >= PAIR_FLOOR]


def line_errors(t: dict, p: dict, sim: float) -> list[str]:
    """Which of the six conditions this paired line fails (empty list = correct)."""
    errs = []
    if sim < DESC_MIN:
        errs.append("description")
    if not math.isclose(float(p.get("qty", math.nan)), t["qty"], abs_tol=1e-9):
        errs.append("qty")
    if not packs_equivalent((t["unit_price"], t["pack_size"], t["unit"]), (p["unit_price"], p.get("pack_size"), p.get("unit"))):
        errs.append("pack")
    if abs(p["unit_price"] - t["unit_price"]) > MONEY_TOL:
        errs.append("unit_price")
    if abs(p["line_total"] - t["line_total"]) > MONEY_TOL:
        errs.append("line_total")
    if p["vat_rate"] != t["vat_rate"]:
        errs.append("vat_rate")
    return errs


# ------------------------------------------------------------------ invoice and set

def reconcile(truth: dict, merged: dict) -> dict:
    """KILL-TEST.md: (sum of extracted net line totals + VAT by rate) equals the extracted gross within 0.01 AND the
    extracted gross equals the ground-truth gross."""
    lines = merged["lines"]
    net = round(sum(ln["line_total"] for ln in lines), 2)
    vat = 0.0
    for rate in {ln["vat_rate"] for ln in lines}:
        part = sum(ln["line_total"] for ln in lines if ln["vat_rate"] == rate)
        vat += round(part * rate / 100 + 0.0, 2)
    calc_gross = round(net + vat, 2)
    gross = merged["totals"].get("gross")
    ok = gross is not None and abs(calc_gross - gross) <= 0.01 + 1e-9 and abs(gross - truth["totals"]["gross"]) <= MONEY_TOL
    return {"ok": bool(ok), "calc_gross": calc_gross, "extracted_gross": gross, "truth_gross": truth["totals"]["gross"]}


def score_invoice(truth: dict, records: list[dict]) -> dict:
    merged = extract.merge_pages(records) if records else extract.merge_pages([])
    pairs = match_lines(truth["lines"], merged["lines"])
    paired_t = {i for i, _, _ in pairs}
    paired_p = {j for _, j, _ in pairs}
    details, correct = [], 0
    for i, j, sim in pairs:
        errs = line_errors(truth["lines"][i], merged["lines"][j], sim)
        correct += not errs
        if errs:
            details.append({"truth": truth["lines"][i]["description"], "pred": merged["lines"][j]["description"], "errors": errs})
    missing = [truth["lines"][i]["description"] for i in range(len(truth["lines"])) if i not in paired_t]
    halluc = [merged["lines"][j]["description"] for j in range(len(merged["lines"])) if j not in paired_p]
    rec = reconcile(truth, merged)
    wrong = len(truth["lines"]) - correct + len(halluc)
    header = {"supplier": merged["supplier_name"] == truth["supplier"], "invoice_no": merged["invoice_number"] == truth["invoice_no"],
              "date": merged["invoice_date"] == truth["date"], "credit_flag": merged["is_credit_note"] == truth["credit_note"]}
    return {"id": truth["id"], "layout": truth["layout"], "heldout": truth["heldout"], "distorted": truth["distorted"],
            "credit_note": truth["credit_note"], "multipage": truth["pages"] > 1, "truth_lines": len(truth["lines"]),
            "correct": correct, "hallucinated": len(halluc), "wrong_lines": wrong, "missing": missing, "hallucinated_lines": halluc,
            "line_errors": details, "reconciled": rec["ok"], "reconciliation": rec,
            "silent_error": wrong > 0 and rec["ok"], "failed_pages": merged["failed_pages"], "header": header}


def acc(rows: list[dict]) -> dict:
    t = sum(r["truth_lines"] for r in rows)
    c = sum(r["correct"] for r in rows)
    h = sum(r["hallucinated"] for r in rows)
    return {"invoices": len(rows), "truth_lines": t, "correct": c, "hallucinated": h,
            "accuracy": (c / (t + h)) if (t + h) else None}


def p95(values: list[float]) -> float | None:
    """Nearest-rank 95th percentile."""
    if not values:
        return None
    s = sorted(values)
    return s[max(math.ceil(0.95 * len(s)) - 1, 0)]


def distortion_split(rows: list[dict], truths: dict) -> dict:
    """Information only: line accuracy for the worse and milder half of distorted invoices, per distortion parameter."""
    params = {"rotation_deg": lambda v: abs(v), "blur_sigma": float, "jpeg_quality": lambda v: -v, "shadow_strength": float,
              "crumple_amp_px": float, "perspective_jitter": float}
    dist = [r for r in rows if r["distorted"]]
    out = {}
    for name, sev in params.items():  # sev: higher = more severe
        vals = {}
        for r in dist:
            ds = truths[r["id"]].get("distortion") or []
            if ds:
                vals[r["id"]] = statistics.mean(sev(d[name]) for d in ds)
        if len(vals) < 4:
            continue
        med = statistics.median(vals.values())
        hi = [r for r in dist if vals.get(r["id"], -1e9) > med]
        lo = [r for r in dist if r["id"] in vals and vals[r["id"]] <= med]
        out[name] = {"more_severe": acc(hi), "milder": acc(lo)}
    return out


BARS = {  # KILL-TEST.md section 3 (fixed)
    "pass": {"overall": 0.95, "distorted": 0.90, "heldout": 0.90, "reconciliation": 0.90, "silent_max": 1, "cost_max": 0.02,
             "p95_max": 90.0, "failure_max": 0.02},
    "kill": {"overall": 0.88, "distorted": 0.80, "heldout": 0.80, "silent_min": 3, "cost_min": 0.05, "failure_min": 0.05},
}


def verdict(m: dict) -> dict:
    """PASS / KILL / INCONCLUSIVE from the metrics, per the fixed bars. Only meaningful on a complete TEST run."""
    def v(x):
        return x if x is not None else 0.0
    P, K = BARS["pass"], BARS["kill"]
    kill = {"overall < 88%": v(m["overall"]["accuracy"]) < K["overall"],
            "distorted < 80%": v(m["subsets"]["distorted"]["accuracy"]) < K["distorted"],
            "held-out < 80%": v(m["subsets"]["heldout"]["accuracy"]) < K["heldout"],
            "silent errors >= 3": m["silent_errors"] >= K["silent_min"],
            "cost > $0.05/page": m["cost_per_page_usd"] > K["cost_min"],
            "failure rate > 5%": m["failure_rate"] > K["failure_min"]}
    passed = {"overall >= 95%": v(m["overall"]["accuracy"]) >= P["overall"],
              "distorted >= 90%": v(m["subsets"]["distorted"]["accuracy"]) >= P["distorted"],
              "held-out >= 90%": v(m["subsets"]["heldout"]["accuracy"]) >= P["heldout"],
              "reconciliation >= 90%": m["reconciliation_rate"] >= P["reconciliation"],
              "silent errors <= 1": m["silent_errors"] <= P["silent_max"],
              "cost <= $0.02/page": m["cost_per_page_usd"] <= P["cost_max"],
              "p95 latency <= 90 s": (m["p95_latency_s"] or 0) <= P["p95_max"],
              "failure rate <= 2%": m["failure_rate"] <= P["failure_max"]}
    result = "KILL" if any(kill.values()) else ("PASS" if all(passed.values()) else "INCONCLUSIVE")
    return {"result": result, "kill_triggers": [k for k, x in kill.items() if x], "pass_checks": passed}


def score_set(set_dir: Path, ext_dir: Path, ledger: Path | None = None) -> dict:
    truths = {}
    for tj in sorted(set_dir.glob("*.json")):
        if tj.name != "MANIFEST.json":
            t = json.loads(tj.read_text())
            truths[t["id"]] = t
    recs: dict[str, list[dict]] = {k: [] for k in truths}
    for f in sorted(ext_dir.glob("*_p*.json")):
        r = json.loads(f.read_text())
        if r["invoice_id"] in recs:
            recs[r["invoice_id"]].append(r)
    rows = [score_invoice(truths[k], recs[k]) for k in sorted(truths)]
    all_recs = [r for rs in recs.values() for r in rs]
    total_pages = sum(t["pages"] for t in truths.values())
    failed = sum(1 for r in all_recs if r["status"] != "ok")
    unscored = max(total_pages - len(all_recs), 0)
    cost = sum(r["cost_usd"] for r in all_recs)
    record_cost = cost
    if ledger is not None and truths and all(k.startswith("TEST-") for k in truths):
        # metric of record (KILL-TEST s2): billed USD incl. retries, from the ledger rows labelled with TEST page ids
        cost = 0.0
        if Path(ledger).exists():
            for line in Path(ledger).read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    if str(row.get("label", "")).startswith("TEST-"):
                        cost += float(row["usd"])
    subsets = {"clean": [r for r in rows if not r["distorted"]], "distorted": [r for r in rows if r["distorted"]],
               "heldout": [r for r in rows if r["heldout"]], "dev_layouts": [r for r in rows if not r["heldout"]],
               "credit_notes": [r for r in rows if r["credit_note"]], "multipage": [r for r in rows if r["multipage"]]}
    layouts = sorted({r["layout"] for r in rows})
    metrics = {
        "invoices": len(rows), "pages": total_pages, "overall": acc(rows),
        "subsets": {k: acc(v) for k, v in subsets.items()},
        "per_layout": {k: acc([r for r in rows if r["layout"] == k]) for k in layouts},
        "reconciliation_rate": sum(r["reconciled"] for r in rows) / len(rows) if rows else 0.0,
        "silent_errors": sum(r["silent_error"] for r in rows),
        "silent_error_invoices": [r["id"] for r in rows if r["silent_error"]],
        "pages_failed_after_retry": failed, "pages_unscored_no_result": unscored,
        "failure_rate": (failed + unscored) / total_pages if total_pages else 0.0,
        "cost_total_usd": round(cost, 4),
        "cost_from_page_records_usd": round(record_cost, 4),
        # cost over pages that have a result; unscored pages (budget stop) have no cost, so a partial run shows a partial total
        "cost_per_page_usd": round(cost / total_pages, 5) if total_pages else 0.0,
        "p95_latency_s": p95([r["latency_s"] for r in all_recs]),
        "retried_pages": sum(1 for r in all_recs if r.get("retries")),
        "tokens": {"input": sum(r["input_tokens"] for r in all_recs), "output": sum(r["output_tokens"] for r in all_recs)},
        "header_accuracy": {k: sum(r["header"][k] for r in rows) / len(rows) for k in ("supplier", "invoice_no", "date", "credit_flag")}
        if rows else {},
        "by_distortion_param": distortion_split(rows, truths),
        "line_error_kinds": {},
    }
    kinds: dict[str, int] = {}
    for r in rows:
        for d in r["line_errors"]:
            for e in d["errors"]:
                kinds[e] = kinds.get(e, 0) + 1
    metrics["line_error_kinds"] = kinds
    metrics["verdict_if_test"] = verdict(metrics)
    return {"metrics": metrics, "invoices": rows}


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def report_md(res: dict, title: str) -> str:
    m = res["metrics"]
    L = [f"# {title}", "", f"{m['invoices']} invoices, {m['pages']} pages. Bars are from KILL-TEST.md; the verdict below is "
         "meaningful only on a complete TEST run.", "",
         "| Metric | Value |", "|---|---|",
         f"| Line accuracy, overall | {pct(m['overall']['accuracy'])} ({m['overall']['correct']} correct of {m['overall']['truth_lines']} "
         f"lines + {m['overall']['hallucinated']} hallucinated) |"]
    for k, label in (("clean", "clean"), ("distorted", "distorted"), ("heldout", "held-out layouts"), ("dev_layouts", "dev layouts"),
                     ("credit_notes", "credit notes"), ("multipage", "multi-page")):
        s = m["subsets"][k]
        L.append(f"| Line accuracy, {label} | {pct(s['accuracy'])} ({s['invoices']} invoices) |")
    L += [f"| Reconciliation rate | {pct(m['reconciliation_rate'])} |",
          f"| Silent-error invoices (wrong lines, totals pass) | {m['silent_errors']} {m['silent_error_invoices']} |",
          f"| Failure rate (failed after retry + never run) | {pct(m['failure_rate'])} ({m['pages_failed_after_retry']} failed, "
          f"{m['pages_unscored_no_result']} not run) |",
          f"| Cost per page | ${m['cost_per_page_usd']:.4f} (total ${m['cost_total_usd']:.4f}) |",
          f"| p95 latency per page | {m['p95_latency_s']} s |",
          f"| Pages that needed the 32k retry | {m['retried_pages']} |",
          f"| Tokens | {m['tokens']['input']} in, {m['tokens']['output']} out |", ""]
    L += ["## Per layout", "", "| Layout | Invoices | Accuracy |", "|---|---|---|"]
    L += [f"| {k} | {v['invoices']} | {pct(v['accuracy'])} |" for k, v in m["per_layout"].items()]
    L += ["", "## Wrong-line causes", "", ", ".join(f"{k}: {v}" for k, v in sorted(m["line_error_kinds"].items())) or "none", ""]
    if m["by_distortion_param"]:
        L += ["## By distortion type (information only)", "", "| Parameter | More severe half | Milder half |", "|---|---|---|"]
        L += [f"| {k} | {pct(v['more_severe']['accuracy'])} | {pct(v['milder']['accuracy'])} |" for k, v in m["by_distortion_param"].items()]
        L.append("")
    vd = m["verdict_if_test"]
    L += ["## Verdict against the fixed bars", "", f"**{vd['result']}**" + (f" (kill triggers: {', '.join(vd['kill_triggers'])})" if vd["kill_triggers"] else ""), ""]
    L += [f"- {'ok' if ok else 'FAIL'}: {name}" for name, ok in vd["pass_checks"].items()]
    bad = [r for r in res["invoices"] if r["wrong_lines"] or r["failed_pages"]]
    if bad:
        L += ["", "## Invoices with errors", ""]
        for r in bad:
            L.append(f"- {r['id']} ({r['layout']}): {r['wrong_lines']} wrong, reconciled={r['reconciled']}, silent={r['silent_error']}, "
                     f"failed pages {r['failed_pages']}; missing {r['missing'][:3]}; extra {r['hallucinated_lines'][:3]}; "
                     f"{[ (d['truth'], d['errors']) for d in r['line_errors'][:4]]}")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set", choices=["dev", "test"], required=True)
    ap.add_argument("--extractions", required=True)
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--ledger", help="spend ledger for the test-set cost (default <extractions>/ledger.jsonl if present, else results/ledger.jsonl)")
    a = ap.parse_args(argv)
    ledger = Path(a.ledger) if a.ledger else (Path(a.extractions) / "ledger.jsonl")
    if not ledger.exists() and not a.ledger:
        ledger = extract.DEFAULT_LEDGER
    res = score_set(HERE / "data" / a.set, Path(a.extractions), ledger)
    out = Path(a.out) if a.out else Path(a.extractions) / "score.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    rep = Path(a.report) if a.report else Path(a.extractions) / "REPORT.md"
    rep.write_text(report_md(res, f"T-80 benchmark report: {a.set} set"))
    m = res["metrics"]
    print(f"{a.set}: accuracy {pct(m['overall']['accuracy'])}, reconciliation {pct(m['reconciliation_rate'])}, silent {m['silent_errors']}, "
          f"failure {pct(m['failure_rate'])}, ${m['cost_per_page_usd']:.4f}/page, p95 {m['p95_latency_s']} s; wrote {out} and {rep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
