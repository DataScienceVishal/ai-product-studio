"""Deterministic synthetic sample (pseudonymous IDs, Saturday week-endings).

Run: python3 -I samples/generate.py [OUT_DIR]   (default: this folder)
Leave year starts 1 April, so each leave week below is the worker's first in the leave year (normal-pay week).
Hand-computed expectations (asserted in tests/test_audit.py):
  W001 fixed pay, contract basic 500.00, no variable pay. Due 500.00, paid 500.00. No exception.
  W002 basic 400 + commission 30 + overtime alternating 40/60 (so 52 weeks average 50.00).
       Leave 2025-08-09: due 400+30+50 = 480.00, paid 400.00 -> UNDERPAID 80.00.
  W003 basic 300 but 5 weeks (2025-01-04..02-01) of statutory sick pay only (no basic): those weeks are skipped, so the
       average stays 300.00. Leave 2025-08-09 paid 310.00 -> OVERPAID 10.00.
  W004 leaver: basic 350 + commission 50, history 2024-07-06..2025-06-14 (only 47 weeks before the leave, so flag `shortened`).
       Leave 2025-05-31: due 400.00, paid 350.00 -> UNDERPAID 50.00.
  W005 pay rise 300 -> 330 from 2025-02-08. Leave 2025-08-09: the 52 weeks before it hold 26 weeks at 300
       and 26 at 330, average 315.00, paid 300.00 -> UNDERPAID 15.00.
Totals: 5 workers, 5 leave weeks, 3 underpayments totalling 145.00, overpaid 10.00, 1 worker with flags.
"""
import csv
import os
import sys
from datetime import date, timedelta

START, END = date(2024, 6, 1), date(2025, 8, 30)
LEAVE = date(2025, 8, 9)


def weeks(start=START, end=END):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=7)


def build():
    h = []

    def add(w, d, cat, amt):
        h.append((w, d.isoformat(), cat, f"{amt:.2f}"))

    for d in weeks():
        if d == LEAVE:
            add("W001", d, "holiday_pay", 500)
            add("W002", d, "holiday_pay", 400)
            add("W003", d, "holiday_pay", 310)
            add("W005", d, "holiday_pay", 300)
            continue
        add("W001", d, "basic", 500)
        add("W002", d, "basic", 400)
        add("W002", d, "commission", 30)
        add("W002", d, "regular_overtime", 40 if ((d - START).days // 7) % 2 else 60)
        if date(2025, 1, 4) <= d <= date(2025, 2, 8) and d != date(2025, 2, 8):
            add("W003", d, "statutory", 116.75)
        else:
            add("W003", d, "basic", 300)
        add("W005", d, "basic", 330 if d >= date(2025, 2, 8) else 300)
    for d in weeks(date(2024, 7, 6), date(2025, 6, 14)):
        if d == date(2025, 5, 31):
            add("W004", d, "holiday_pay", 350)
        else:
            add("W004", d, "basic", 350)
            add("W004", d, "commission", 50)
    h.sort()
    leave = [("W002", "2025-08-09"), ("W003", "2025-08-09"), ("W004", "2025-05-31"),
             ("W005", "2025-08-09"), ("W001", "2025-08-09")]
    workers = [("W001", "fixed_pay", "500.00"), ("W002", "variable_hours", ""), ("W003", "variable_hours", ""),
               ("W004", "variable_hours", ""), ("W005", "variable_hours", "")]
    return {
        "history.csv": (("worker_id", "week_ending", "element_category", "amount"), h),
        "leave.csv": (("worker_id", "week_ending"), sorted(leave)),
        "workers.csv": (("worker_id", "worker_type", "contract_weekly_basic"), workers),
    }


def write(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, (header, rows) in build().items():
        with open(os.path.join(out_dir, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)


if __name__ == "__main__":
    write(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
