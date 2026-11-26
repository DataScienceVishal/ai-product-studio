"""Write a names-only CSV (id, pay_element_name, source_style) from a labelled CSV. Never copies any other column.

    python3 -m mapper.extract_names --in gold.csv --out names.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys

if __package__ in (None, ""):
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KEEP = ("id", "pay_element_name", "source_style")


def extract(src: str, dst: str, expect_sha: str = "") -> int:
    if expect_sha:
        with open(src, "rb") as handle:
            if hashlib.sha256(handle.read()).hexdigest() != expect_sha.strip().lower():
                raise ValueError("input file sha256 does not match --expect-sha")
    with open(src, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in KEEP if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("input is missing required column(s): " + ", ".join(missing))
        rows = [{c: row.get(c) or "" for c in KEEP} for row in reader]
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids) or "" in ids:
        raise ValueError("ids must be unique and non-empty")
    with open(dst, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(KEEP), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expect-sha", default="", help="optional sha256 the input file must match")
    args = parser.parse_args(argv)
    try:
        count = extract(args.src, args.out, args.expect_sha)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {count} names to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
