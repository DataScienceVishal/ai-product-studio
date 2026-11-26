"""Score predictions against the frozen gold file.

    python3 -m mapper.score --gold gold.csv --pred predictions.csv --run run.json --expect-sha <sha256> --out RESULTS.md

Headline: nine-category accuracy (B1). Eight-category accuracy (deduction_excluded folded into expense_excluded on both
sides) is reported alongside, never instead.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper.mapper import UNMAPPED
from mapper.prompt import CATEGORIES

B1_PASS = 0.95
B2_PASS_BELOW, B2_KILL_ABOVE = 0.02, 0.05


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        digest.update(handle.read())
    return digest.hexdigest()


def fold(category: str) -> str:
    return "expense_excluded" if category == "deduction_excluded" else category


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def compute(gold: list[dict], pred: dict[str, str]) -> dict:
    """All metrics. A row with no prediction counts as UNMAPPED (wrong)."""
    pairs = [(g["id"], g["category"], pred.get(g["id"], UNMAPPED), (g.get("note") or "").startswith("AMBIGUOUS:"))
             for g in gold]
    n = len(pairs)

    def acc(items, f=lambda c: c):
        return (sum(1 for _, t, p, _ in items if p != UNMAPPED and f(t) == f(p)) / len(items)) if items else None

    amb = [x for x in pairs if x[3]]
    rest = [x for x in pairs if not x[3]]
    labels = list(CATEGORIES) + [UNMAPPED]
    confusion = {t: {p: 0 for p in labels} for t in CATEGORIES}
    for _, t, p, _ in pairs:
        confusion.setdefault(t, {x: 0 for x in labels})[p if p in labels else UNMAPPED] += 1
    per = {}
    for c in CATEGORIES:
        tp = sum(1 for _, t, p, _ in pairs if t == c and p == c)
        pn = sum(1 for _, _, p, _ in pairs if p == c)
        tn = sum(1 for _, t, _, _ in pairs if t == c)
        per[c] = {"precision": tp / pn if pn else None, "recall": tp / tn if tn else None, "support": tn, "predicted": pn}
    return {
        "n": n, "acc9": acc(pairs), "acc8": acc(pairs, fold),
        "ambiguous": {"n": len(amb), "acc9": acc(amb)}, "rest": {"n": len(rest), "acc9": acc(rest)},
        "per_category": per, "confusion": confusion,
        "unmapped": sum(1 for x in pairs if x[2] == UNMAPPED),
    }


def b2_verdict(cost_per_200: float) -> str:
    if cost_per_200 < B2_PASS_BELOW:
        return "PASS"
    if cost_per_200 > B2_KILL_ABOVE:
        return "KILL"
    return "REVIEW"


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render(m: dict, run: dict, gold_sha: str) -> str:
    n = m["n"]
    cost_200 = (run.get("cost_usd", 0.0) / run["names"] * 200) if run.get("names") else 0.0
    b1 = "PASS" if m["acc9"] is not None and m["acc9"] >= B1_PASS else "KILL"
    b2 = b2_verdict(cost_200)
    L = ["# Kill-test Part B results", "",
         f"- Gold sha256 (verified equal to the expected value): `{gold_sha}`",
         f"- Run: {'FAKE (not a valid kill-test run)' if run.get('fake') else 'live'}, model `{run.get('model')}`, "
         f"deployment `{run.get('deployment')}`, {run.get('timestamp_utc')}",
         f"- Prompt: {run.get('prompt_version')} sha256 `{run.get('prompt_sha256')}`",
         f"- Tokens: {run.get('input_tokens')} in, {run.get('output_tokens')} out, cost ${run.get('cost_usd', 0):.4f}", "",
         f"## Headline: nine-category accuracy {_pct(m['acc9'])} ({n} names)", "",
         f"Eight-category accuracy (deduction_excluded folded into expense_excluded on both sides): {_pct(m['acc8'])}. "
         "The nine-category figure is the headline and the one B1 is judged on.", "",
         "| Subset | Names | Nine-category accuracy |", "|---|---|---|",
         f"| Rows marked AMBIGUOUS | {m['ambiguous']['n']} | {_pct(m['ambiguous']['acc9'])} |",
         f"| All other rows | {m['rest']['n']} | {_pct(m['rest']['acc9'])} |", "",
         f"UNMAPPED (invalid or missing, counted wrong): {m['unmapped']}", "",
         "## Per category", "", "| Category | Support | Predicted | Precision | Recall |", "|---|---|---|---|---|"]
    for c, v in m["per_category"].items():
        L.append(f"| {c} | {v['support']} | {v['predicted']} | {_pct(v['precision'])} | {_pct(v['recall'])} |")
    labels = list(CATEGORIES) + [UNMAPPED]
    L += ["", "## Confusion (rows gold, columns predicted)", "", "| gold \\ pred | " + " | ".join(labels) + " |",
          "|---" * (len(labels) + 1) + "|"]
    for t in CATEGORIES:
        L.append(f"| {t} | " + " | ".join(str(m["confusion"][t][p]) for p in labels) + " |")
    L += ["", "## Verdicts", "",
          f"- B1 (nine-category accuracy {_pct(m['acc9'])}, PASS needs >= 95%): **{b1}**",
          f"- B2 (cost per 200 names ${cost_200:.4f}; PASS < $0.02, KILL > $0.05, else REVIEW): **{b2}**", ""]
    if run.get("fake"):
        L.insert(2, "**This run used the fake client. It proves the plumbing only.**")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("--gold", "--pred", "--run", "--expect-sha", "--out"):
        parser.add_argument(flag, required=True)
    args = parser.parse_args(argv)
    try:
        actual = sha256_file(args.gold)
        if actual != args.expect_sha.strip().lower():
            print("refused: gold file sha256 does not match --expect-sha (the frozen labels must not change)",
                  file=sys.stderr)
            return 3
        gold = read_csv(args.gold)
        if not gold or not {"id", "category"} <= set(gold[0]):
            print("error: gold file needs id and category columns", file=sys.stderr)
            return 2
        pred = {r["id"]: r["category"] for r in read_csv(args.pred)}
        with open(args.run, encoding="utf-8") as handle:
            run = json.load(handle)
        text = render(compute(gold, pred), run, actual)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
