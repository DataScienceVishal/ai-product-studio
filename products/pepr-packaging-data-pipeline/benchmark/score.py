"""Scorer for the pEPR extraction benchmark. Implements benchmark/README.md "Scoring rules" exactly.

Usage:  python3 score.py --set test|tuning --pred DIR [--ledger FILE] [--out FILE]
DIR holds one <sheet_id>.json prediction per sheet, in the truth shape (see README "Truth format"); a prediction
component has the same fields as a truth component, `ram_category` being a plain string. Extra keys are ignored.

Slots per truth component: material, colour, weight_g, plausible features, and ram_category (only if truth material
is present). A slot scores 1 when:
  present  -> prediction present and equal (strings: taxonomy.canonical equality; weight: taxonomy.weight_within)
  missing  -> prediction missing (a value there is a fabrication; an absent key is wrong but not a fabrication)
  conflict -> prediction flags conflict with both truth values (each within tolerance); anything else scores 0
Pass mark 4b (kill test wording) is the share of conflict cases flagged as a conflict, not silently chosen; the
both-values rate is shown as information and already counts in field accuracy through this rule.
Traceability: every non-missing predicted value (conflict: each value) must carry refs, and every ref must pass
taxonomy.quote_ok against the stated page's text. ram_category is derived, so it has no quote.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import taxonomy as tx  # noqa: E402

DATA = HERE / "data"
USD_PER_SHEET_MAX = 0.316  # GBP 0.25 at 0.79 GBP/USD, README "Run budget"
PASS_MARKS = {"overall_field_accuracy": 0.90, "messy10_field_accuracy": 0.80, "untraced": 0,
              "missing_handling": 0.95, "conflict_flag": 0.80}


def _pred_status(f):
    return f.get("status") if isinstance(f, dict) else None


def _vals_match(key, truth_vals, pred_vals):
    """Both truth values reported (order-free), each within tolerance (weights) or canonical-equal (strings)."""
    if not isinstance(pred_vals, list) or len(pred_vals) != len(truth_vals):
        return False
    left = list(pred_vals)
    for t in truth_vals:
        hit = next((p for p in left if _eq(key, t, p)), None)
        if hit is None:
            return False
        left.remove(hit)
    return True


def _eq(key, truth_value, pred_value):
    try:
        if key == "weight_g":
            return tx.weight_within(float(pred_value), float(truth_value))
        return tx.canonical(key.split(".")[-1], pred_value) == tx.canonical(key.split(".")[-1], truth_value)
    except (TypeError, ValueError):
        return False


def match_components(truth_comps, pred_comps):
    """Rule (d): greedy, one-to-one, in sheet order. Name first (norm_name); material is a tie-break only when truth
    material is present. Returns ({truth_idx: pred_idx}, [unmatched pred idx])."""
    pred_comps = [p if isinstance(p, dict) else {} for p in pred_comps]
    used, pairs = set(), {}
    for i, t in enumerate(truth_comps):
        cands = [j for j, p in enumerate(pred_comps)
                 if j not in used and tx.norm_name(p.get("name", "")) == tx.norm_name(t["name"])]
        if len(cands) > 1 and t["material"]["status"] != "missing":
            tm = t["material"]["value"]
            same = [j for j in cands if _pred_status(pred_comps[j].get("material")) == "present"
                    and tx.canonical("material", pred_comps[j]["material"].get("value", "")) == tm]
            cands = same or cands
        if cands:
            pairs[i] = cands[0]
            used.add(cands[0])
    return pairs, [j for j in range(len(pred_comps)) if j not in used]


def _get(comp, slot):
    if slot == "ram_category":
        return comp.get("ram_category")
    if slot.startswith("features."):
        feats = comp.get("features")
        return feats.get(slot[9:]) if isinstance(feats, dict) else None
    return comp.get(slot)


def _slot_key(slot):
    return slot[9:] if slot.startswith("features.") else slot


def _traced(slot, field, page_texts):
    """True if a non-missing predicted field is fully traced. ram_category needs none."""
    key = _slot_key(slot)
    st = _pred_status(field)
    refs = field.get("refs")
    if not isinstance(refs, list) or not refs:
        return False
    values = field.get("conflict_values") if st == "conflict" else [field.get("value")]
    if not isinstance(values, list) or not values:
        return False
    for r in refs:
        if not (isinstance(r, dict) and isinstance(r.get("page"), int) and 1 <= r["page"] <= len(page_texts)
                and isinstance(r.get("quote"), str)):
            return False
    for v in values:  # each value needs a ref whose quote names it, and every ref must check out for some value
        if not any(tx.quote_ok(key, _canon(key, v), r["quote"], page_texts[r["page"] - 1]) for r in refs):
            return False
    for r in refs:
        if not any(tx.quote_ok(key, _canon(key, v), r["quote"], page_texts[r["page"] - 1]) for v in values):
            return False
    return True


def _canon(key, v):
    if key == "weight_g":
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")
    c = tx.canonical(key, v) if isinstance(v, str) else None
    return c if c is not None else "\x00unlisted"


def score_sheet(truth, pred, page_texts):
    """Counts for one sheet. page_texts: list of str per page (text layer or recorded page text)."""
    c = dict(slots=0, correct=0, missing_slots=0, missing_ok=0, fabricated=0, conflict_slots=0, conflict_ok=0,
             conflict_flagged=0, unflagged_conflicts=0, false_conflicts=0, untraced=0, traced_values=0,
             extra_component_slots=0)
    tcomps = truth["components"]
    pcomps = pred.get("components") if isinstance(pred.get("components"), list) else []
    pairs, extra = match_components(tcomps, pcomps)
    for i, t in enumerate(tcomps):
        p = pcomps[pairs[i]] if i in pairs and isinstance(pcomps[pairs[i]], dict) else None
        for _, slot, tstatus in [s for s in tx.scored_slots({"components": [t]})]:
            c["slots"] += 1
            tfield = _get(t, slot)
            pfield = _get(p, slot) if p else None
            if slot == "ram_category":
                ok = p is not None and isinstance(pfield, str) and pfield == t["ram_category"]
                c["correct"] += ok
                continue
            key = _slot_key(slot)
            pst = _pred_status(pfield)
            ok = False
            if tstatus == "present":
                if pst == "present":
                    ok = _eq(slot, tfield["value"], pfield.get("value"))
                elif pst == "conflict" and slot == "weight_g":
                    c["false_conflicts"] += 1
            elif tstatus == "missing":
                c["missing_slots"] += 1
                ok = pst == "missing"
                c["missing_ok"] += ok
                if pst in ("present", "conflict"):
                    c["fabricated"] += 1
            else:  # conflict
                c["conflict_slots"] += 1
                if pst == "conflict":
                    c["conflict_flagged"] += 1
                    ok = _vals_match(slot, tfield["conflict_values"], pfield.get("conflict_values"))
                else:
                    c["unflagged_conflicts"] += 1
                c["conflict_ok"] += ok
            c["correct"] += ok
    # every non-missing predicted value, matched or not, must be traced
    for comp in pcomps:
        if not isinstance(comp, dict):
            continue
        feats = comp.get("features") if isinstance(comp.get("features"), dict) else {}
        for slot in ["material", "colour", "weight_g"] + [f"features.{k}" for k in feats]:
            f = _get(comp, slot)
            if _pred_status(f) in ("present", "conflict"):
                c["traced_values"] += 1
                if _slot_key(slot) not in tx.VOCAB and slot not in ("material", "colour", "weight_g") \
                        or not _traced(slot, f, page_texts):
                    c["untraced"] += 1
    for j in extra:  # unmatched extracted component: one wrong field per slot it would have
        comp = pcomps[j] if isinstance(pcomps[j], dict) else {}
        n = 4 + len(tx.PLAUSIBLE.get(tx.norm_name(comp.get("name", "")), []))  # material, colour, weight, ram + features
        c["slots"] += n
        c["extra_component_slots"] += n
    return c


def page_texts_for(sheet_id, pdf, manifest_entry):
    from pypdf import PdfReader
    if manifest_entry.get("scanned"):
        return list(manifest_entry["page_text"])
    return [p.extract_text() or "" for p in PdfReader(str(pdf)).pages]


def _add(a, b):
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def _pct(n, d):
    return None if not d else n / d


def summarise(c):
    return {"slots": c["slots"], "field_accuracy": _pct(c["correct"], c["slots"]), "untraced": c["untraced"],
            "traced_values": c["traced_values"], "fabricated": c["fabricated"],
            "missing_handling": _pct(c["missing_ok"], c["missing_slots"]),
            "conflict_flag": _pct(c["conflict_flagged"], c["conflict_slots"]),  # pass mark 4b: flagged, not silently chosen
            "conflict_both_values": _pct(c["conflict_ok"], c["conflict_slots"]),  # information only (feeds field accuracy via rule a)
            "unflagged_conflicts": c["unflagged_conflicts"], "false_conflicts": c["false_conflicts"],
            "counts": c}


def read_ledger_cost(ledger, sheet_ids):
    """USD per sheet from the JSONL ledger (sum of that sheet's entries)."""
    per = {}
    if ledger and Path(ledger).exists():
        for line in Path(ledger).read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                if e.get("sheet_id") in sheet_ids:
                    per[e["sheet_id"]] = per.get(e["sheet_id"], 0.0) + float(e.get("usd", 0.0))
    return per


def score_set(truths, preds, page_texts, messy_ids, cost_per_sheet=None, require_cost=True):
    """truths/preds/page_texts: dicts keyed by sheet_id. Returns the full report with pass/fail per mark."""
    per, total, messy = {}, {}, {}
    for sid, t in truths.items():
        pred = preds.get(sid) or {}
        c = score_sheet(t, pred, page_texts[sid])
        per[sid] = summarise(c)
        total = _add(total, c)
        if sid in messy_ids:
            messy = _add(messy, c)
    overall, m10 = summarise(total), summarise(messy) if messy else None
    checks = {
        "1_overall_field_accuracy>=0.90": (overall["field_accuracy"] or 0) >= 0.90,
        "2_messy10_field_accuracy>=0.80": m10 is not None and (m10["field_accuracy"] or 0) >= 0.80,
        "3_untraced==0": overall["untraced"] == 0,
        "4a_missing_handling>=0.95": (overall["missing_handling"] if overall["missing_handling"] is not None else 1) >= 0.95,
        "4b_conflict_flagged>=0.80": (overall["conflict_flag"] if overall["conflict_flag"] is not None else 1) >= 0.80,
    }
    cost = None
    if cost_per_sheet is not None:
        tot = sum(cost_per_sheet.values())
        cost = {"total_usd": tot, "mean_usd_per_sheet": tot / max(len(truths), 1),
                "max_usd_sheet": max(cost_per_sheet.values(), default=0.0),
                "sheets_with_cost": len(cost_per_sheet)}
        checks["5_cost<=USD0.316_mean_per_sheet"] = cost["mean_usd_per_sheet"] <= USD_PER_SHEET_MAX \
            and len(cost_per_sheet) == len(truths)
    elif require_cost:
        checks["5_cost<=USD0.316_mean_per_sheet"] = False  # no ledger: cost cannot be shown, so not passed
    return {"overall": overall, "messy10": m10, "per_sheet": per, "cost": cost, "checks": checks,
            "pass": all(checks.values())}


def load_set(which, pred_dir, data=DATA):
    manifest = json.loads((data / "manifest.json").read_text())
    entries = {e["sheet_id"]: e for e in manifest["test" if which == "test" else "tuning"]}
    tdir, pdfdir = ("truth", "sheets") if which == "test" else ("tuning_truth", "tuning")
    truths, preds, texts = {}, {}, {}
    for sid, e in sorted(entries.items()):
        truths[sid] = json.loads((data / tdir / f"{sid}.json").read_text())
        pf = Path(pred_dir) / f"{sid}.json"
        preds[sid] = json.loads(pf.read_text()) if pf.exists() else {}
        texts[sid] = page_texts_for(sid, data / pdfdir / f"{sid}.pdf", e)
    return truths, preds, texts, set(manifest["messiest_10"]) if which == "test" else set()


def format_report(r):
    pc = lambda x: "n/a" if x is None else f"{100 * x:.1f}%"
    o, m = r["overall"], r["messy10"]
    lines = [f"field accuracy overall {pc(o['field_accuracy'])} ({o['counts']['correct']}/{o['slots']})",
             f"messy-10 accuracy      {pc(m['field_accuracy']) if m else 'n/a'}",
             f"untraced values        {o['untraced']} of {o['traced_values']}",
             f"missing handled        {pc(o['missing_handling'])}   fabricated {o['fabricated']}",
             f"conflicts flagged {pc(o['conflict_flag'])} (pass mark 4b)   with both values {pc(o['conflict_both_values'])} (info)"
             f"   unflagged {o['unflagged_conflicts']}   false conflicts {o['false_conflicts']}"]
    if r["cost"]:
        lines.append(f"cost USD {r['cost']['total_usd']:.3f} total, {r['cost']['mean_usd_per_sheet']:.3f} mean/sheet, "
                     f"max sheet {r['cost']['max_usd_sheet']:.3f}")
    for sid, s in r["per_sheet"].items():
        lines.append(f"  {sid}: acc {pc(s['field_accuracy'])} untraced {s['untraced']} fabricated {s['fabricated']}")
    for k, v in r["checks"].items():
        lines.append(f"{'PASS' if v else 'FAIL'}  {k}")
    lines.append("OVERALL " + ("PASS" if r["pass"] else "FAIL"))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["test", "tuning"], required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--ledger")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    truths, preds, texts, messy = load_set(a.set, a.pred)
    cost = read_ledger_cost(a.ledger, set(truths)) if a.ledger else None
    r = score_set(truths, preds, texts, messy, cost, require_cost=(a.set == "test"))
    if a.set == "tuning":
        r["checks"].pop("2_messy10_field_accuracy>=0.80", None)
        r["pass"] = all(r["checks"].values())
    print(format_report(r))
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
