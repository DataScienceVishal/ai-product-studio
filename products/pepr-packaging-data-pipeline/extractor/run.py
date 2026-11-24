"""CLI: python -m extractor.run --set tuning|test --provider fake|azure --out results/NAME

Writes <out>/<sheet>.json, <out>/ledger.jsonl (or --ledger, shared across runs so the USD 12 / 3M-token caps cover the
whole proof test), then runs benchmark/score.py on the predictions. Extraction itself (extract.py) never sees truth.
Run tuning and test sequentially, never in parallel: the ledger has no file lock."""
import argparse
import json
import sys
from pathlib import Path

from . import budget as budget_mod
from . import extract, providers

PRODUCT = Path(__file__).resolve().parents[1]
SETS = {"test": PRODUCT / "benchmark" / "data" / "sheets", "tuning": PRODUCT / "benchmark" / "data" / "tuning",
        "supplement": PRODUCT / "benchmark" / "supplement" / "data" / "sheets"}
DEFAULT_LEDGER = PRODUCT / "results" / "ledger.jsonl"


def _ledger_has_test_entries(ledger):
    ids = {p.stem for p in SETS["test"].glob("S*.pdf")}
    if not Path(ledger).exists():
        return False
    return any(json.loads(ln).get("sheet_id") in ids for ln in Path(ledger).read_text().splitlines() if ln.strip())


def make_provider(name):
    if name == "fake":
        return providers.FakeProvider()
    return providers.AzureResponsesProvider()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="extractor.run")
    ap.add_argument("--set", choices=sorted(SETS), required=True)
    ap.add_argument("--provider", choices=["fake", "azure"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", help="shared ledger (default results/ledger.jsonl; fake runs use <out>/ledger.jsonl)")
    ap.add_argument("--max-output-tokens", type=int, default=extract.MAX_OUTPUT_TOKENS)
    ap.add_argument("--no-score", action="store_true")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        provider = make_provider(a.provider)
    except (providers.SpendNotApproved, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    ledger = Path(a.ledger) if a.ledger else (DEFAULT_LEDGER if a.provider == "azure" else out / "ledger.jsonl")
    budget = budget_mod.Budget(ledger)
    if a.set == "supplement" and not _ledger_has_test_entries(ledger):  # Amendment 4: never before the test set
        print("refused: the supplement runs only after the test set (no test-set entries in the ledger); "
              "it would otherwise use budget the --set test preflight needs", file=sys.stderr)
        return 6
    pdfs = sorted(SETS[a.set].glob("S*.pdf"))
    if a.set == "test":  # run once only: do not start a run the guard would cut short
        try:
            budget_mod.preflight(budget, len(pdfs), a.max_output_tokens)
        except budget_mod.BudgetExceeded as e:
            print(f"refused to start the test set: {e}", file=sys.stderr)
            return 4
    for pdf in pdfs:
        try:
            pred = extract.extract_pdf(pdf, provider, budget, max_output_tokens=a.max_output_tokens)
        except budget_mod.BudgetExceeded as e:
            print(f"STOP, budget guard: {e}", file=sys.stderr)
            return 3
        except providers.ProviderError as e:
            print(f"{pdf.stem}: provider failed: {e}", file=sys.stderr)
            if e.fatal:
                return 5
            continue
        (out / f"{pdf.stem}.json").write_text(json.dumps(pred, indent=1, sort_keys=True))
        print(f"{pdf.stem}: {len(pred['components'])} components, USD {pred['usage']['usd']:.4f}")
    print(f"ledger {ledger}: USD {budget.spent_usd:.4f}, {budget.tokens} tokens")
    if a.no_score:
        return 0
    sys.path.insert(0, str(PRODUCT / "benchmark"))
    import score
    argv = ["--set", a.set, "--pred", str(out), "--ledger", str(ledger), "--out", str(out / "score.json")]
    return score.main(argv)


if __name__ == "__main__":
    sys.exit(main())
