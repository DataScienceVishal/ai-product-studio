"""Run the mapper once.

    python3 -m mapper.run --names names.csv --out results/ [--fake]

Live runs are ONE-SHOT: the kill test forbids re-running after seeing labels, so a second live run into the same
results folder is refused. Fake runs write to <out>/fake/ and are marked "fake": true.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper.mapper import AzureOpenAIClient, FakeClient, map_names
from mapper.prompt import PROMPT_SHA256, PROMPT_VERSION

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
    out_dir = os.path.join(args.out, "fake") if args.fake else args.out
    if not args.fake and live_run_exists(out_dir):
        print(f"refused: {out_dir} already holds a live run. The kill test allows one live run and no re-run "
              "after seeing labels.", file=sys.stderr)
        return 3
    if args.fake:
        client = FakeClient()
    elif client is None:
        try:
            client = AzureOpenAIClient.from_env()
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    os.makedirs(out_dir, exist_ok=True)
    if not args.fake:  # written before the call, so a crash after spend still blocks a second run
        with open(os.path.join(out_dir, "run.started"), "w", encoding="utf-8") as handle:
            handle.write("live run started; delete only with Vishal's approval\n")
    result = map_names(rows, client)
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
        "names": len(rows),
        "requests": result.requests,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "price_per_million_usd": {"input": DEFAULT_PRICE[0], "output": DEFAULT_PRICE[1]},
        "cost_usd": cost,
        "unmapped": result.unmapped,
        "problems": result.errors,
        "timestamp_utc": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(out_dir, "run.json"), "w", encoding="utf-8") as handle:
        json.dump(info, handle, indent=2)
        handle.write("\n")
    print(f"mapped {len(rows)} names, {result.unmapped} UNMAPPED, cost ${cost:.4f}, wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
