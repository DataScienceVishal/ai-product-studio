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
from mapper.mapper import MAX_OUTPUT_TOKENS
from mapper.prompt import PROMPT_SHA256, PROMPT_VERSION, REASONING_EFFORT, config_sha256

# gpt-5-mini USD per million tokens. Input $0.25 and output $2.00 (reasoning bills as output): the figures recorded in
# state/BUDGET.md (run bb8d, T-56). products/_starter/backend/app/aicost.py keeps only the $2.00 output price as a
# conservative blend; here input and output are priced separately. Estimate: the Azure spend report has the last word.
PRICE_PER_MILLION = {"gpt-5-mini": (0.25, 2.00)}
DEFAULT_PRICE = PRICE_PER_MILLION["gpt-5-mini"]


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
        return [json.loads(line) for line in handle if line.strip()]


def _utc(now) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None, client=None, now=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--names", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--fake", action="store_true")
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
            client = AzureOpenAIClient.from_env()
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
        entry = {"timestamp_utc": stamp, "prompt_sha256": PROMPT_SHA256, "config_sha256": config_sha, "failures": result.failures,
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
