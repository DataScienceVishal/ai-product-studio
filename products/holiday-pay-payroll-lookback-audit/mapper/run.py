"""Run the mapper once.

    python3 -m mapper.run --names names.csv --out results/ [--fake]

Live runs are ONE-SHOT: the kill test forbids re-running after seeing labels, so a second live run into the same
results folder is refused. Fake runs write to <out>/fake/ and are marked "fake": true.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper.mapper import UNMAPPED, AzureOpenAIClient, FakeClient, MapResult, map_names
from mapper.mapper import MAX_OUTPUT_TOKENS, check_price, estimate_input_tokens, worst_case_usd
from mapper.prompt import SYSTEM_PROMPT, build_user_message
from mapper.prompt import PROMPT_SHA256, PROMPT_VERSION, REASONING_EFFORT, config_sha256

# gpt-5-mini USD per million tokens. Input $0.25 and output $2.00 (reasoning bills as output): the figures recorded in
# state/BUDGET.md (run bb8d, T-56). products/_starter/backend/app/aicost.py keeps only the $2.00 output price as a
# conservative blend; here input and output are priced separately. Estimate: the Azure spend report has the last word.
PRICE_PER_MILLION = {"gpt-5-mini": (0.25, 2.00)}
DEFAULT_PRICE = PRICE_PER_MILLION["gpt-5-mini"]


# Spend and size limits (security review T-120 M-2). The cap is the Q-16 approval; lowering it is free, raising it
# above HARD_MAX_USD needs --allow-over-cap.
HARD_MAX_USD = 2.00
DEFAULT_MAX_USD = 2.00
MAX_NAMES = 500
MAX_NAME_CHARS = 120
MAX_REQUEST_CHARS = 100_000  # one request's user message


def preflight(rows: list[dict], client, max_usd: float, price: tuple[float, float] = DEFAULT_PRICE,
              batch_size: int = 200, earlier: list[dict] | None = None) -> tuple[float, str]:
    """(worst-case USD, "") or (0, reason to refuse). Pure: sends nothing.

    The cap is cumulative over the out dir: earlier no-answer attempts count at their recorded worst case
    (a legacy entry without one counts at this run's worst case), so re-runs cannot each spend a full cap."""
    if len(rows) > MAX_NAMES:
        return 0.0, f"{len(rows)} names is over the limit of {MAX_NAMES}"
    for row in rows:
        if len(row["pay_element_name"]) > MAX_NAME_CHARS:
            return 0.0, f"id {row['id']}: pay_element_name is over {MAX_NAME_CHARS} characters"
    try:
        price = check_price(price)
    except ValueError as error:
        return 0.0, str(error)
    max_out = getattr(client, "max_output_tokens", MAX_OUTPUT_TOKENS)
    attempts = getattr(client, "retries", 2) + 1
    total = 0.0
    for start in range(0, len(rows), batch_size):
        user = build_user_message(rows[start:start + batch_size])
        if len(user) > MAX_REQUEST_CHARS:
            return 0.0, f"a request would be {len(user)} characters, over the limit of {MAX_REQUEST_CHARS}"
        total += worst_case_usd(estimate_input_tokens(SYSTEM_PROMPT, user), max_out, price) * attempts
    if total > max_usd:
        return total, f"worst-case spend ${total:.4f} (all retries counted) is over the cap ${max_usd:.2f}"
    try:
        before = earlier_worst_case(earlier or [], total)
    except ValueError as error:
        return 0.0, f"attempts.jsonl is corrupt ({error})"
    if before + total > max_usd:
        return total, (f"cumulative worst-case spend ${before + total:.4f} (earlier attempts ${before:.4f} + this run "
                       f"${total:.4f}) is over the cap ${max_usd:.2f}")
    return total, ""


def earlier_worst_case(earlier: list[dict], this_run: float) -> float:
    """Sum of earlier attempts' recorded worst-case USD. Raises ValueError on anything malformed (fail closed)."""
    total = 0.0
    for entry in earlier:
        if not isinstance(entry, dict):
            raise ValueError("an entry is not an object")
        value = entry.get("worst_case_usd")
        if value is None:
            value = this_run  # legacy entry: assume it was as big as this run
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0 <= value < float("inf")):
            raise ValueError("an entry has an invalid worst_case_usd")
        total += value
    return total


def cost_usd(input_tokens: int, output_tokens: int, price: tuple[float, float] = DEFAULT_PRICE) -> float:
    return round((input_tokens * price[0] + output_tokens * price[1]) / 1_000_000, 6)


def read_names(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != ["id", "pay_element_name", "source_style"]:
            raise ValueError("names file must have exactly the columns id,pay_element_name,source_style "
                             "(make it with mapper.extract_names so no labels are present)")
        return list(reader)


def live_run_exists(out_dir: str) -> bool:
    for name in ("run.started", "predictions.csv"):
        if os.path.exists(os.path.join(out_dir, name)):
            return True
    path = os.path.join(out_dir, "run.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as handle:
                return not json.load(handle).get("fake", False)
        except (OSError, ValueError):
            return True  # unreadable: treat as a live run, fail safe
    return False


def read_attempts(out_dir: str) -> list[dict]:
    path = os.path.join(out_dir, "attempts.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        entries = [json.loads(line) for line in handle if line.strip()]
    if not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("attempts.jsonl holds a line that is not an object")
    return entries


def _utc(now) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None, client=None, now=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--names", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD,
                        help=f"hard cap on worst-case spend, default {DEFAULT_MAX_USD}")
    parser.add_argument("--allow-over-cap", action="store_true", help=f"needed to set --max-usd above {HARD_MAX_USD}")
    parser.add_argument("--allow-insecure-localhost", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        rows = read_names(args.names)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if not rows:
        print("error: no names to map", file=sys.stderr)
        return 2
    if len({r["id"] for r in rows}) != len(rows):
        print("error: duplicate ids in names file", file=sys.stderr)
        return 2
    live = not args.fake
    if not (args.max_usd > 0 and args.max_usd == args.max_usd and args.max_usd != float("inf")):
        print("error: --max-usd must be a number above zero", file=sys.stderr)
        return 2
    if args.max_usd > HARD_MAX_USD and not args.allow_over_cap:
        print(f"error: --max-usd above {HARD_MAX_USD} needs --allow-over-cap (the Q-16 cap)", file=sys.stderr)
        return 2
    with open(args.names, "rb") as handle:
        names_sha = hashlib.sha256(handle.read()).hexdigest()
    out_dir = args.out if live else os.path.join(args.out, "fake")
    earlier: list[dict] = []
    if live:
        if live_run_exists(out_dir):
            print(f"refused: {out_dir} already holds a live run. The kill test allows one live run and no re-run "
                  "after seeing labels.", file=sys.stderr)
            return 3
        try:
            earlier = read_attempts(out_dir)
        except (OSError, ValueError):
            print("refused: attempts.jsonl is unreadable", file=sys.stderr)
            return 3
    if not live:
        client = FakeClient()
    elif client is None:
        try:
            client = AzureOpenAIClient.from_env(allow_insecure_localhost=args.allow_insecure_localhost)
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    estimate, reason = preflight(rows, client, args.max_usd, earlier=earlier)
    if reason:
        print(f"refused before any call: {reason}", file=sys.stderr)
        return 2
    before_usd = earlier_worst_case(earlier, estimate)  # validated by preflight
    if live and hasattr(client, "set_spend_cap"):
        try:
            client.set_spend_cap(args.max_usd - before_usd, DEFAULT_PRICE)
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    config_sha = config_sha256(getattr(client, "max_output_tokens", MAX_OUTPUT_TOKENS), names_sha)
    if live and any(a.get("config_sha256") != config_sha for a in earlier):
        print("refused: an earlier no-answer attempt used a different run config (prompt, schema, reasoning effort, "
              "output cap, message template or names file). A re-run is allowed only with the identical config.",
              file=sys.stderr)
        return 3
    os.makedirs(out_dir, exist_ok=True)
    marker = os.path.join(out_dir, "run.started")
    if live:  # written before the call, so a crash after spend still blocks a second run
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("live run started\n")
    stamp = _utc(now)
    crashed = ""
    result = MapResult(predictions={})
    try:
        map_names(rows, client, into=result)
    except Exception as error:  # map_names handles per-batch failures itself; this is a bug or a reply-handling crash
        crashed = type(error).__name__
        result.errors.append(f"crashed: {crashed}")  # tokens counted before the crash stay in result
    for row in rows:
        result.predictions.setdefault(row["id"], UNMAPPED)
    if live and result.replies == 0 and not crashed:
        # No answer at all: nothing was learnt, so the shot is not used. Log it, release the lock, fail.
        entry = {"timestamp_utc": stamp, "prompt_sha256": PROMPT_SHA256, "config_sha256": config_sha, "worst_case_usd": round(estimate, 6),
                 "failures": result.failures,
                 "input_tokens": result.input_tokens, "output_tokens": result.output_tokens}
        with open(os.path.join(out_dir, "attempts.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        os.remove(marker)
        print("error: no answer from the API (nothing scored, the one shot is not used). See attempts.jsonl: "
              + "; ".join(f"{f['error_class']} {f['http_code'] or ''} {f['message']}".strip() for f in result.failures),
              file=sys.stderr)
        return 4
    with open(os.path.join(out_dir, "predictions.csv"), "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["id", "category"])
        for row in rows:
            writer.writerow([row["id"], result.predictions[row["id"]]])
    cost = 0.0 if args.fake else cost_usd(result.input_tokens, result.output_tokens)
    info = {
        "fake": bool(args.fake),
        "model": getattr(client, "reported_model", "") or client.deployment,
        "deployment": client.deployment,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": PROMPT_SHA256,
        "config_sha256": config_sha,
        "names_sha256": names_sha,
        "reasoning_effort": REASONING_EFFORT,
        "settings": client.settings() if hasattr(client, "settings") else {},
        "names": len(rows),
        "requests": result.requests,
        "replies": result.replies,
        "transport_attempts": result.transport_attempts,
        "finish_reasons": result.finish_reasons,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "price_per_million_usd": {"input": DEFAULT_PRICE[0], "output": DEFAULT_PRICE[1]},
        "cost_usd": cost,
        "spend_cap_usd": args.max_usd,
        "worst_case_estimate_usd": round(estimate, 6),
        "earlier_attempts_worst_case_usd": round(before_usd, 6),
        "cumulative_worst_case_usd": round(before_usd + estimate, 6),
        "unmapped": result.unmapped,
        "problems": result.errors,
        "failed_attempts": earlier,
        "batch_failures": result.failures,
        "crashed": crashed or False,
        "timestamp_utc": stamp,
    }
    with open(os.path.join(out_dir, "run.json"), "w", encoding="utf-8") as handle:
        json.dump(info, handle, indent=2)
        handle.write("\n")
    print(f"mapped {len(rows)} names, {result.unmapped} UNMAPPED, cost ${cost:.4f}, wrote {out_dir}")
    return 0 if not crashed else 5


if __name__ == "__main__":
    sys.exit(main())
