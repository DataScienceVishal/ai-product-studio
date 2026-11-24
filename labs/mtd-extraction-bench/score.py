"""Scorer: field accuracy, category accuracy, review routing, review-time model."""
import difflib, json, re
from pathlib import Path

THRESHOLD = 0.8
# Review-time assumptions (seconds). Stated in RESULTS.md; change here to test sensitivity.
ASSUMP = {
    "manual_per_line": 25.0,    # read source, type date/amount/description, pick category
    "glance_per_line": 4.0,     # confirm an auto-accepted line at a glance
    "flagged_per_line": 35.0,   # open source, check and fix a flagged line
    "missed_per_line": 25.0,    # line the model failed to extract: entered by hand
    "fixed_per_doc": 60.0,      # open file, check totals/opening balance
}


SILENT_ERROR_COST = 120.0  # s charged per undetected wrong auto-accepted line (find later + fix / amend)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()


def desc_sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def to_amount(x):
    try:
        return round(float(str(x).replace(",", "").replace("£", "")), 2)
    except (TypeError, ValueError):
        return None


def match_lines(truth, pred):
    """Greedy match each truth line to an unused prediction: same date+amount, then amount, then order."""
    used, pairs = set(), []
    for t in truth:
        best = None
        for i, p in enumerate(pred):
            if i in used or to_amount(p.get("amount")) != t["amount"]:
                continue
            score = (p.get("date") == t["date"]) * 2 + desc_sim(p.get("description"), t["description"])
            if best is None or score > best[0]:
                best = (score, i)
        if best:
            used.add(best[1]); pairs.append((t, pred[best[1]]))
        else:
            pairs.append((t, None))
    return pairs


def conf_of(p):
    try:
        return float(p.get("confidence"))
    except (TypeError, ValueError):
        return 0.0


def score_doc(truth, pred, threshold=THRESHOLD, assump=ASSUMP):
    pairs = match_lines(truth, pred)
    n = len(truth)
    d_ok = a_ok = s_ok = b_ok = b_n = c_ok = matched = 0
    routed = auto = auto_cat_ok = auto_all_ok = 0
    for t, p in pairs:
        if p is None:
            continue
        matched += 1
        da = p.get("date") == t["date"]
        am = to_amount(p.get("amount")) == t["amount"]
        ds = desc_sim(p.get("description"), t["description"]) >= 0.6
        d_ok += da; a_ok += am; s_ok += ds
        if t.get("balance") is not None:
            b_n += 1; b_ok += to_amount(p.get("balance")) == t["balance"]
        cat = p.get("category") == t["category"]
        c_ok += cat
        if conf_of(p) < threshold:
            routed += 1
        else:
            auto += 1; auto_cat_ok += cat; auto_all_ok += (cat and da and am and ds)
    missed = n - matched
    flagged = routed
    manual = assump["manual_per_line"] * n
    ai = (assump["fixed_per_doc"] + assump["glance_per_line"] * auto +
          assump["flagged_per_line"] * flagged + assump["missed_per_line"] * missed)
    r = lambda a, b: round(a / b, 4) if b else None
    silent = auto - auto_all_ok          # wrong lines that were auto-accepted: nobody looks at them
    ai_silent = ai + assump.get("silent_error_cost", SILENT_ERROR_COST) * silent
    return {
        "silent_errors": silent, "assisted_seconds_silent": round(ai_silent, 1),
        "review_time_ratio_silent": r(ai_silent, manual),
        "lines_truth": n, "lines_matched": matched, "lines_missed": missed,
        "extra_pred_lines": max(0, len(pred) - matched),
        "date_acc": r(d_ok, n), "amount_acc": r(a_ok, n), "desc_acc": r(s_ok, n),
        "balance_acc": r(b_ok, b_n),
        "category_acc": r(c_ok, n),
        "routed_to_review": r(routed + missed, n),
        "auto_lines": auto, "auto_category_acc": r(auto_cat_ok, auto),
        "auto_all_fields_acc": r(auto_all_ok, auto),
        "undetected_errors_in_auto": auto - auto_all_ok,
        "manual_seconds": manual, "assisted_seconds": round(ai, 1),
        "review_time_ratio": r(ai, manual),
        "review_time_halved": bool(manual and ai <= 0.5 * manual),
    }


def score_all(datadir, results):
    out = {}
    for name, res in results.items():
        truth = json.loads((Path(datadir) / f"{name}.truth.json").read_text())["lines"]
        out[name] = score_doc(truth, res.get("lines", []))
    return out
