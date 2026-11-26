"""Look-back: per-leave-week paid vs due, with working shown (kill-test A3)."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Sequence

from .elements import normal_pay, basic_pay
from .reference import reference_average, money

NORMAL_WEEKS = Decimal(4)


@dataclass(frozen=True)
class LeaveEntry:
    week_end: date                 # week-ending date of the holiday week (a key in history)
    weeks: Decimal = Decimal(1)    # leave taken, in weeks (1 = full week)


def _leave_year_start(d: date, month: int, day: int) -> date:
    s = date(d.year, month, day)
    return s if d >= s else date(d.year - 1, month, day)


def lookback(history: Dict[date, dict], leave: Sequence[LeaveEntry],
             leave_year_month: int = 4, leave_year_day: int = 1,
             holiday_weeks_count: bool = False, uplift_all_leave: bool = False) -> List[dict]:
    """history: {week_end_date: {category: amount}} at 7-day steps; missing weeks = no pay.

    For each leave entry the reference period is the weeks before the leave week.
    The first 4 weeks of leave in each leave year are due at normal pay
    (basic + regular overtime + commission + status allowances); later leave at
    basic pay (minimum), or normal pay too if `uplift_all_leave`. `paid` is the
    holiday_pay element recorded in the leave week. Weeks of holiday pay are
    excluded from the reference average unless `holiday_weeks_count`.
    """
    rows = []
    used_in_year: Dict[date, Decimal] = {}
    for entry in sorted(leave, key=lambda e: e.week_end):
        lys = _leave_year_start(entry.week_end, leave_year_month, leave_year_day)
        used = used_in_year.get(lys, Decimal(0))
        normal_w = max(Decimal(0), min(entry.weeks, NORMAL_WEEKS - used))
        if uplift_all_leave:
            normal_w = entry.weeks
        basic_w = entry.weeks - normal_w
        used_in_year[lys] = used + entry.weeks

        recent_first = [history.get(entry.week_end - timedelta(days=7 * i), {}) for i in range(1, 105)]
        normal_ref = reference_average([normal_pay(p, holiday_weeks_count) for p in recent_first])
        basic_ref = reference_average([basic_pay(p, holiday_weeks_count) for p in recent_first])
        due = normal_w * normal_ref.average + basic_w * basic_ref.average
        paid = Decimal(history.get(entry.week_end, {}).get("holiday_pay", 0))
        rows.append({
            "week_end": entry.week_end,
            "leave_year_start": lys,
            "leave_weeks": entry.weeks,
            "normal_weeks": normal_w,
            "basic_weeks": basic_w,
            "paid": money(paid),
            "due": money(due),
            "difference": money(due) - money(paid),   # positive = underpaid
            "working": {
                "normal": {"weeks_used": normal_ref.weeks_used, "weeks_scanned": normal_ref.weeks_scanned,
                           "weeks_skipped": normal_ref.weeks_skipped, "total": money(normal_ref.total),
                           "average": money(normal_ref.average), "shortened": normal_ref.shortened},
                "basic": {"weeks_used": basic_ref.weeks_used, "weeks_scanned": basic_ref.weeks_scanned,
                          "weeks_skipped": basic_ref.weeks_skipped, "total": money(basic_ref.total),
                          "average": money(basic_ref.average), "shortened": basic_ref.shortened},
            },
        })
    return rows
