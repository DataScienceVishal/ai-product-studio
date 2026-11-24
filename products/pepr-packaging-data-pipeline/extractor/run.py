"""CLI: python -m extractor.run --set tuning|test --provider fake|azure --out results/NAME

Writes <out>/<sheet>.json, <out>/ledger.jsonl (or --ledger, shared across runs so the USD 12 / 3M-token caps cover the
whole proof test), then runs benchmark/score.py on the predictions. Extraction itself (extract.py) never sees truth.
Run tuning and test sequentially, never in parallel: the ledger has no file lock."""
import argparse
import json
import os
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
    entries = [json.loads(ln) for ln in Path(ledger).read_text().splitlines() if ln.strip()]  # parse every line: no short-circuit
    for e in entries:  # every line must be a usable ledger entry, as Budget requires
        float(e["usd"]), int(e["input_tokens"]), int(e["output_tokens"])
    return any(e.get("sheet_id") in ids for e in entries)

def _supplement_gate(ledger):
    """Return an error message if the supplement must not run, else None. An unreadable ledger never allows it."""
    try:
        has_test = _ledger_has_test_entries(ledger)
    except (ValueError, AttributeError, TypeError, KeyError, OSError, UnicodeDecodeError) as e:
        return f"refused: the ledger {ledger} is unreadable ({type(e).__name__}: {e}); the supplement will not run on an unreadable ledger"
    if not has_test:  # Amendment 4: never before the test set
        return ("refused: the supplement runs only after the test set (no test-set entries in the ledger); "
                "it would otherwise use budget the --set test preflight needs")
    return None


def resolve_max_output_tokens(flag, env=None):
    """CLI flag, else env T56_MAX_OUTPUT_TOKENS, else the default. Must be an integer >= 1000."""
    env = os.environ if env is None else env
    raw = flag if flag is not None else env.get("T56_MAX_OUTPUT_TOKENS")
    if raw in (None, ""):
        return extract.MAX_OUTPUT_TOKENS
    try:
        n = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"max output tokens must be an integer, got {raw!r}") from None
    if n < 1000:
        raise ValueError(f"max output tokens {n} is too small (minimum 1000)")
    return n


RESUME_MUST_MATCH = ("set", "deployment", "price_model", "reasoning_effort", "max_output_tokens")


def _resume_settings_error(first_path, info):
    """None if the first run's run.json matches this run on the settings that must not change, else a message."""
    try:
        first = json.loads(Path(first_path).read_text())
    except (OSError, ValueError):
        return f"--resume needs the first run's {first_path} to compare settings; it is missing or unreadable"
    diff = [f"{k}: first run {first.get(k)!r}, now {info.get(k)!r}" for k in RESUME_MUST_MATCH if first.get(k) != info.get(k)]
    return ("settings differ from the first run (" + "; ".join(diff) + "); set the same env or flags as the first run") if diff else None


def _ledger_rows(ledger):
    p = Path(ledger)
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.exists() else []


def _resume_plan(pdfs, out, ledger, budget, charge, note, max_out):
    """-> (pdfs still to run, skipped sheet ids). Charges worst-case rows first. Raises ValueError on an inconsistent state:
    an output with no ledger row of this price model, or a final (non-estimated) row with no output."""
    ids = {p.stem for p in pdfs}
    for sid in charge:
        if sid not in ids:
            raise ValueError(f"--charge-worst-case {sid}: not a sheet of this set")
        if (out / f"{sid}.json").exists() or any(r.get("sheet_id") == sid for r in _ledger_rows(ledger)):
            raise ValueError(f"--charge-worst-case {sid}: it already has an output or a ledger row; not charging twice")
        budget.record(sid, budget_mod.WORST_INPUT_TOKENS, max_out, estimated=True, note=note)
        print(f"charged {sid}: worst case {budget_mod.WORST_INPUT_TOKENS} in + {max_out} out at {budget.model} prices")
    rows = [r for r in _ledger_rows(ledger) if r.get("model") == budget.model]
    todo, skipped = [], []
    for pdf in pdfs:
        sid = pdf.stem
        mine = [r for r in rows if r.get("sheet_id") == sid]
        has_out = (out / f"{sid}.json").exists()
        if has_out and not mine:
            raise ValueError(f"{sid} has an output but no {budget.model} ledger row; fix by hand, nothing was called")
        if not has_out and any(not r.get("estimated") for r in mine):
            raise ValueError(f"{sid} has a billed ledger row but no output; fix by hand, nothing was called")
        (skipped if has_out else todo).append(sid if has_out else pdf)
    return todo, skipped


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
    ap.add_argument("--max-output-tokens", type=int, default=None,
                    help="output cap per call, reasoning included (default: env T56_MAX_OUTPUT_TOKENS, else "
                         f"{extract.MAX_OUTPUT_TOKENS}); a sheet that runs out is reported incomplete, not truncated")
    ap.add_argument("--resume", action="store_true",
                    help="skip sheets that already have <out>/SXXX.json and a ledger row of this price model; "
                         "an output without a ledger row, or a final (non-estimated) row without output, stops the run")
    ap.add_argument("--charge-worst-case", metavar="SHEET", action="append", default=[],
                    help="with --resume: first append one worst-case estimated ledger row for SHEET (a call that may have "
                         "been billed but left no output); refused if SHEET already has an output or a ledger row")
    ap.add_argument("--charge-note", default="connection reset in run bb8d test1, may have been billed",
                    help="note written on the --charge-worst-case row")
    ap.add_argument("--no-score", action="store_true")
    a = ap.parse_args(argv)

    try:
        max_out = resolve_max_output_tokens(a.max_output_tokens)
        provider = make_provider(a.provider)
    except (providers.SpendNotApproved, ValueError) as e:  # UnknownModel is a ValueError
        print(f"refused: {e}", file=sys.stderr)
        return 2
    a.max_output_tokens = max_out
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = Path(a.ledger) if a.ledger else (DEFAULT_LEDGER if a.provider == "azure" else out / "ledger.jsonl")
    if a.set == "supplement":
        msg = _supplement_gate(ledger)
        if msg:
            print(msg, file=sys.stderr)
            return 6
    budget = budget_mod.Budget(ledger, model=provider.price_model, deployment=provider.deployment)
    p_in, p_out = budget_mod.price_for(budget.model)
    info = {"set": a.set, "provider": a.provider, "deployment": provider.deployment, "price_model": budget.model,
            "usd_per_m_in": p_in, "usd_per_m_out": p_out, "max_output_tokens": max_out,
            "reasoning_effort": getattr(provider, "reasoning_effort", None)}
    if a.resume:  # same settings as the first run, or nothing is called; the first run.json is never overwritten
        msg = _resume_settings_error(out / "run.json", info)
        if msg:
            print(f"refused: {msg}", file=sys.stderr)
            return 7
        n = 1
        while (out / ("run-resume.json" if n == 1 else f"run-resume-{n}.json")).exists():
            n += 1
        (out / ("run-resume.json" if n == 1 else f"run-resume-{n}.json")).write_text(json.dumps(info, indent=1, sort_keys=True))
    else:
        (out / "run.json").write_text(json.dumps(info, indent=1, sort_keys=True))
    print("run: " + ", ".join(f"{k} {v}" for k, v in info.items()))
    pdfs = sorted(SETS[a.set].glob("S*.pdf"))
    incomplete = []
    if a.charge_worst_case and not a.resume:
        print("refused: --charge-worst-case needs --resume", file=sys.stderr)
        return 2
    if a.resume:
        try:
            pdfs, skipped = _resume_plan(pdfs, out, ledger, budget, a.charge_worst_case, a.charge_note, max_out)
        except ValueError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 7
        print(f"resume: skipped {len(skipped)} sheet(s) with output and ledger row: {', '.join(skipped) or '-'}; "
              f"to run: {', '.join(p.stem for p in pdfs) or '-'}")
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
            # not silent: the sheet is written with no components (its whole field set scores as missing) and a warning
            incomplete.append(pdf.stem)
            (out / f"{pdf.stem}.json").write_text(json.dumps(
                {"sheet_id": pdf.stem, "components": [], "pages": [], "warnings": [f"provider failed, no answer: {e}"],
                 "usage": {"input_tokens": e.input_tokens, "output_tokens": e.output_tokens, "usd": 0.0,
                           "model": provider.deployment}}, indent=1, sort_keys=True))
            continue
        (out / f"{pdf.stem}.json").write_text(json.dumps(pred, indent=1, sort_keys=True))
        print(f"{pdf.stem}: {len(pred['components'])} components, USD {pred['usage']['usd']:.4f}")
    if incomplete:
        print(f"WARNING: {len(incomplete)} sheet(s) without an answer (scored as missing): {', '.join(incomplete)}", file=sys.stderr)
    print(f"ledger {ledger}: USD {budget.spent_usd:.4f}, {budget.tokens} tokens")
    if a.no_score:
        return 0
    sys.path.insert(0, str(PRODUCT / "benchmark"))
    import score
    argv = ["--set", a.set, "--pred", str(out), "--ledger", str(ledger), "--out", str(out / "score.json")]
    return score.main(argv)


if __name__ == "__main__":
    sys.exit(main())
