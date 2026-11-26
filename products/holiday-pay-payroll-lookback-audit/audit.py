"""Holiday pay look-back audit: python3 audit.py --history h.csv --leave l.csv [--workers w.csv] --out DIR"""
import argparse
import os
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest import load_workers, ValidationError   # noqa: E402
from report import audit, write_outputs, history_gaps, unlisted_holiday_pay, DEFAULT_THRESHOLD   # noqa: E402


MAX_ERRORS_SHOWN = 50
MAX_THRESHOLD = Decimal(1000000)


def _threshold(s):
    try:
        v = Decimal(s)
        if v.is_finite() and 0 <= v <= MAX_THRESHOLD:
            v.quantize(Decimal("0.01"))
            return v
    except InvalidOperation:
        pass
    raise argparse.ArgumentTypeError(f"invalid threshold {s[:20]!r}: use a number of pounds from 0 to {MAX_THRESHOLD}")


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
        for issue in e.issues[:MAX_ERRORS_SHOWN]:
            print(issue, file=sys.stderr)
        if len(e.issues) > MAX_ERRORS_SHOWN:
            print(f"... and {len(e.issues) - MAX_ERRORS_SHOWN} more", file=sys.stderr)
        print(f"{len(e.issues)} validation error(s); nothing written.", file=sys.stderr)
        return 2
    try:
        rows, exceptions = audit(workers, a.threshold, a.include_flagged)
    except (ValueError, OverflowError) as e:
        print(f"cannot audit this data: {e}", file=sys.stderr)
        return 2
    try:
        write_outputs(a.out, rows, exceptions, a.threshold, history_gaps(workers), len(workers),
                      unlisted_holiday_pay(workers))
    except OSError as e:
        print(f"cannot write output to '{a.out}': {e.strerror or e}", file=sys.stderr)
        return 2
    print(f"{len(rows)} leave weeks checked, {len(exceptions)} exceptions. Written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
