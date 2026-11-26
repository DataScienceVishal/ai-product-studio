"""Holiday pay look-back audit: python3 audit.py --history h.csv --leave l.csv [--workers w.csv] --out DIR"""
import argparse
import os
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest.loader import _mask_id   # noqa: E402
from ingest import load_workers, ValidationError, name_like_id_warnings, excluded_week_with_pay   # noqa: E402
from report import audit, write_outputs, history_gaps, unlisted_holiday_pay, ignored_contract_basic, DEFAULT_THRESHOLD, split_rows, rolled_up_weeks_checked, rolled_up_leave_weeks, stray_rolled_up, holiday_pay_to_rolled_up, rolled_up_idle, rolled_up_leave_missing   # noqa: E402


MAX_ERRORS_SHOWN = 50
MAX_THRESHOLD = Decimal(1000000)


def _threshold(s):
    try:
        v = Decimal(s)
        if v.is_finite() and 0 <= v <= MAX_THRESHOLD:
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
    name_like = name_like_id_warnings(workers)
    for msg in name_like[:MAX_ERRORS_SHOWN]:
        print(msg, file=sys.stderr)
    if len(name_like) > MAX_ERRORS_SHOWN:
        print(f"... and {len(name_like) - MAX_ERRORS_SHOWN} more worker_id warning(s)", file=sys.stderr)
    excluded_pay = [(_mask_id(w), d) for w, d in excluded_week_with_pay(workers).items()]
    for masked, weeks in excluded_pay[:MAX_ERRORS_SHOWN]:
        print(f"warning: worker_id {masked}: excluded_week marked on a week that also has pay; the week was used as a normal week "
              f"(week ending {', '.join(str(d) for d in weeks[:10])}{f' and {len(weeks) - 10} more' if len(weeks) > 10 else ''})", file=sys.stderr)
    if len(excluded_pay) > MAX_ERRORS_SHOWN:
        print(f"... and {len(excluded_pay) - MAX_ERRORS_SHOWN} more excluded_week warning(s)", file=sys.stderr)
    try:
        rows, exceptions = audit(workers, a.threshold, a.include_flagged)
    except (ValueError, OverflowError) as e:
        print(f"cannot audit this data: {e}", file=sys.stderr)
        return 2
    ignored = ignored_contract_basic(workers)
    ru_workers = any(w.worker_type == "irregular_rolled_up" for w in workers.values())
    idle = rolled_up_idle(workers, split_rows(rows)[1])
    leave_missing = rolled_up_leave_missing(workers)
    if ignored:
        print(f"note: contract_weekly_basic ignored for {len(ignored)} worker(s) not set as fixed_pay; see report.md", file=sys.stderr)
    try:
        write_outputs(a.out, rows, exceptions, a.threshold, history_gaps(workers), len(workers),
                      unlisted_holiday_pay(workers), ignored, stray_rolled_up(workers), rolled_up_leave_weeks(workers),
                      holiday_pay_to_rolled_up(workers), idle, leave_missing,
                      {wid: w.leave_year_start for wid, w in workers.items()},
                      excluded_pay, len(name_like))
    except OSError as e:
        print(f"cannot write output to '{a.out}': {e.strerror or e}", file=sys.stderr)
        return 2
    lb_rows, ru_rows = split_rows(rows)
    lb_exc, ru_exc = split_rows(exceptions)
    print(f"{len(lb_rows)} leave weeks checked, {len(lb_exc)} exceptions. Written to {a.out}")
    if ru_rows or ru_workers:
        print(f"{rolled_up_weeks_checked(ru_rows)} rolled-up pay weeks checked, {len(ru_exc)} exceptions.")
    if idle:
        print(f"note: {len(idle)} irregular_rolled_up worker(s) had no pay week to check; see report.md")
    if leave_missing:
        print(f"note: {sum(len(v) for v in leave_missing.values())} leave week(s) of irregular_rolled_up worker(s) "
              "are missing from history; see report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
