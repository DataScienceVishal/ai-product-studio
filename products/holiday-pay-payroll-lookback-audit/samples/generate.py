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
Totals for the five look-back workers: 5 leave weeks, 3 underpayments totalling 145.00, overpaid 10.00, 1 worker with flags.

Irregular-hours workers paid rolled-up holiday pay (worker_type irregular_rolled_up). Each pay week is checked on its own:
  W006 basic 200 a week, weeks ending 2024-03-16 to 2024-04-13, rolled-up pay 24.14 (12.07% of 200.00) every week.
       The leave year starting 2023-04-01 covers 2024-03-16, -23 and -30: 3 weeks flagged rolled_up_before_2024_rules.
       2024-04-06 and 2024-04-13 are in the leave year starting 2024-04-01 and are correct.
  W007 basic 150 a week, weeks ending 2025-06-07 to 2025-06-28. Rolled-up pay 18.11 (12.07% of 150.00, rounded) is shown
       in the first two weeks only: 2025-06-21 and -28 are flagged rolled_up_not_shown_separately.
  W008 weeks ending 2025-06-07 to 2025-06-28, basic 200. Rolled-up pay 24.14 (correct), 20.00 (recalculated 24.14, underpaid
       4.14), 30.00 (overpaid 5.86); the last week is a leave week with holiday_pay only, so nothing counts and nothing is checked.
       Its leave row is not re-audited by the 52-week look-back.
Totals: 8 workers, 6 leave rows, 12 rolled-up pay weeks checked, 7 rolled-up exceptions, 11 exceptions in all.
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
        if date(2025, 1, 4) <= d < date(2025, 2, 8):
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
    RU = "rolled_up_holiday_pay"
    for d in weeks(date(2024, 3, 16), date(2024, 4, 13)):
        add("W006", d, "basic", 200)
        add("W006", d, RU, 24.14)
    for i, d in enumerate(weeks(date(2025, 6, 7), date(2025, 6, 28))):
        add("W007", d, "basic", 150)
        if i < 2:
            add("W007", d, RU, 18.11)
    for d, ru in zip(weeks(date(2025, 6, 7), date(2025, 6, 21)), (24.14, 20.00, 30.00)):
        add("W008", d, "basic", 200)
        add("W008", d, RU, ru)
    add("W008", date(2025, 6, 28), "holiday_pay", 200)
    h.sort()
    leave = [("W002", "2025-08-09"), ("W003", "2025-08-09"), ("W004", "2025-05-31"),
             ("W005", "2025-08-09"), ("W001", "2025-08-09"), ("W008", "2025-06-28")]
    workers = [("W001", "fixed_pay", "500.00"), ("W002", "variable_hours", ""), ("W003", "variable_hours", ""),
               ("W004", "variable_hours", ""), ("W005", "variable_hours", ""),
               ("W006", "irregular_rolled_up", ""), ("W007", "irregular_rolled_up", ""), ("W008", "irregular_rolled_up", "")]
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
