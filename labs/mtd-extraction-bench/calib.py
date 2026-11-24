"""Calibration layer: merchant-memory rules + confidence threshold + risky-category cap.
Rules are learned from a *prior quarter* of the same persona that a reviewer already corrected (truth labels).
No model calls. Tuned only on pilot findings (risky categories) and the prior quarter, never on the scored docs."""
import re

RISKY_CATS = {"repairs", "car_van_travel", "other_expenses", "professional_fees"}  # where the pilot's errors sat
RULE_AGREE_CONF, RULE_DISAGREE_CONF, RISKY_CAP = 0.97, 0.6, 0.79


def merchant_key(desc):
    toks = [t for t in re.sub(r"[^a-z0-9 &]", " ", str(desc).lower()).split() if not re.search(r"\d", t)]
    toks = [t for t in toks if t not in ("card", "payment", "to", "dd", "ltd")]
    return " ".join(toks[:5])


def build_rules(prior_truth_lines):
    seen = {}
    for l in prior_truth_lines:
        seen.setdefault(merchant_key(l["description"]), set()).add(l["category"])
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1 and k}   # ignore merchants the reviewer split


def apply(lines, rules, use_rules=True, risky_cap=True):
    """lines: [{description, category, confidence,...}] -> copies with calibrated category/confidence."""
    out = []
    for l in lines:
        l = dict(l); conf = float(l.get("confidence") or 0)
        k = merchant_key(l.get("description"))
        if use_rules and k in rules:
            if rules[k] == l.get("category"):
                conf = max(conf, RULE_AGREE_CONF)
            else:
                l["model_category"] = l.get("category"); l["category"] = rules[k]; conf = min(conf, RULE_DISAGREE_CONF)
            l["rule"] = True
        elif risky_cap and l.get("category") in RISKY_CATS:
            conf = min(conf, RISKY_CAP)
        l["confidence"] = conf
        out.append(l)
    return out
