"""Holiday pay look-back audit: python3 audit.py --history h.csv --leave l.csv [--workers w.csv] --out DIR"""
import argparse
import os
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest import load_workers, ValidationError   # noqa: E402
from report import audit, write_outputs, DEFAULT_THRESHOLD   # noqa: E402
from report.builder import history_gaps   # noqa: E402


def _threshold(s):
    try:
        v = Decimal(s)
        if v.is_finite() and v >= 0:
            return v
    except InvalidOperation:
        pass
    raise argparse.ArgumentTypeError(f"invalid threshold '{s}'")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--history", required=True)
    p.add_argument("--leave", required=True)
    p.add_argument("--workers")
    p.add_argument("--out", required=True)
    p.add_argument("--threshold", type=_threshold, default=DEFAULT_THRESHOLD,
                   help="report leave weeks where |difference| is more than this many pounds (default 0.01)")
    p.add_argument("--include-flagged", action="store_true",
                   help="also list leave weeks that carry engine flags, whatever the difference")
    a = p.parse_args(argv)
    try:
        workers = load_workers(a.history, a.leave, a.workers)
    except ValidationError as e:
        for issue in e.issues:
            print(issue, file=sys.stderr)
        print(f"{len(e.issues)} validation error(s); nothing written.", file=sys.stderr)
        return 2
    rows, exceptions = audit(workers, a.threshold, a.include_flagged)
    try:
        write_outputs(a.out, rows, exceptions, a.threshold, history_gaps(workers), len(workers))
    except OSError as e:
        print(f"cannot write output to '{a.out}': {e.strerror or e}", file=sys.stderr)
        return 2
    print(f"{len(rows)} leave weeks checked, {len(exceptions)} exceptions. Written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
