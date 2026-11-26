"""Look-back: per-leave-week paid vs due, with working shown (kill-test A3).

Scope: workers WITHOUT normal working hours / variable pay (ERA 1996 s224,
52-week average) via worker_type="variable_hours" (default), and workers with
normal hours and fixed basic pay via worker_type="fixed_pay" (current basic
rate in force + 52-week average of variable elements). Assumption: the first 4
weeks of leave taken in each leave year are the reg 13 (normal pay) weeks.
A leave week belongs to the leave year containing its week-ending date.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Sequence

from .elements import normal_pay, basic_pay, VARIABLE
from .reference import reference_average, money, dec, MAX_LOOKBACK_WEEKS, MAX_PAID_WEEKS

NORMAL_WEEKS = Decimal(4)
WORKER_TYPES = ("variable_hours", "fixed_pay")


@dataclass(frozen=True)
class LeaveEntry:
    week_end: date                 # week-ending date of the holiday week (a key in history)
    weeks: Decimal = Decimal(1)    # leave taken, in weeks (1 = full week)


def _leave_year_start(d: date, month: int, day: int) -> date:
    s = date(d.year, month, day)
    return s if d >= s else date(d.year - 1, month, day)


def _dates(week_end, indices):
    """Week-ending dates of the reference weeks used, oldest first."""
    return sorted(week_end - timedelta(days=7 * (i + 1)) for i in indices)


def _summary(ref):
    return {"weeks_used": ref.weeks_used, "weeks_scanned": ref.weeks_scanned,
            "weeks_skipped": ref.weeks_skipped, "total": money(ref.total),
            "average": money(ref.average), "shortened": ref.shortened}


RATE_WINDOW = 8


def _fixed_pay_refs(recent_first, contract_basic=None):
    """Fixed-pay worker: contractual basic rate + average variable elements over weeks worked.

    Rate: explicit contract_basic if given. Otherwise inferred as the most common basic among
    non-statutory (no SSP/SMP) weeks with basic pay in the last RATE_WINDOW weeks, ties going to
    the most recent; if there are none, the most recent week with basic pay (fallback).
    Returns a list of flags to add: inferred rate, latest-week mismatch, contract mismatch.
    """
    basics = [basic_pay(p) for p in recent_first]
    flags = []
    if contract_basic is not None:
        current, source = dec(contract_basic), "contract"
    else:
        flags.append("rate_inferred_no_contract_basic")
        cands = [(i, b) for i, (p, b) in enumerate(zip(recent_first[:RATE_WINDOW], basics))
                 if b > 0 and dec(p.get("statutory", 0)) <= 0]
        if cands:
            counts = {}
            for i, b in cands:               # i ascending = most recent first
                n, first = counts.get(b, (0, i))
                counts[b] = (n + 1, first)
            current = min(counts, key=lambda b: (-counts[b][0], counts[b][1]))
            source = "modal_last_8_weeks"
        else:
            current, source = next((b for b in basics if b > 0), Decimal(0)), "latest_week_fallback"
    used, var_total, scanned, idx = 0, Decimal(0), 0, []
    for pos, (p, b) in enumerate(zip(recent_first[:MAX_LOOKBACK_WEEKS], basics)):
        scanned += 1
        if b == 0:
            continue
        used += 1
        idx.append(pos)
        var_total += normal_pay({k: v for k, v in p.items() if k in VARIABLE})
        if used == MAX_PAID_WEEKS:
            break
    var_avg = var_total / used if used else Decimal(0)
    work = {"weeks_used": used, "weeks_scanned": scanned, "weeks_skipped": scanned - used,
            "total": money(var_total), "average": money(var_avg), "shortened": used < MAX_PAID_WEEKS,
            "current_basic": money(current), "basic_source": source}
    if basics[0] != current:
        flags.append("latest_week_basic_differs_from_rate_used")
    if contract_basic is not None and any(basics[i] != current for i in idx):
        flags.append("reference_week_basic_differs_from_contract")
    return current + var_avg, current, work, dict(work), tuple(idx), flags


def lookback(history: Dict[date, dict], leave: Sequence[LeaveEntry],
             leave_year_month: int = 4, leave_year_day: int = 1,
             holiday_weeks_count: bool = False, uplift_all_leave: bool = False,
             worker_type: str = "variable_hours", contract_weekly_basic=None) -> List[dict]:
    """history: {week_end_date: {category: amount}} at 7-day steps; missing weeks = no pay.

    Raises ValueError if history keys are not all on one weekday or a leave
    week_end is not on that weekday, or leave weeks <= 0. Each row has `flags`:
    no_reference_weeks, shortened, leave_week_missing_from_history,
    fixed_pay adds rate_inferred_no_contract_basic, latest_week_basic_differs_from_rate_used,
    reference_week_basic_differs_from_contract. `working` lists weeks_used_dates.
    """
    if worker_type not in WORKER_TYPES:
        raise ValueError(f"worker_type must be one of {WORKER_TYPES}")
    weekdays = {d.weekday() for d in history}
    if len(weekdays) > 1:
        raise ValueError("history week-ending dates fall on different weekdays")
    for e in leave:
        if dec(e.weeks) <= 0:
            raise ValueError("leave weeks must be positive")
        if weekdays and e.week_end.weekday() not in weekdays:
            raise ValueError(f"leave week_end {e.week_end} is not on the pay-week ending day of the history")

    rows = []
    used_in_year: Dict[date, Decimal] = {}
    for entry in sorted(leave, key=lambda e: e.week_end):
        weeks = dec(entry.weeks)
        try:
            lys = _leave_year_start(entry.week_end, leave_year_month, leave_year_day)
        except ValueError:
            raise ValueError("invalid leave year start date")
        used = used_in_year.get(lys, Decimal(0))
        normal_w = weeks if uplift_all_leave else max(Decimal(0), min(weeks, NORMAL_WEEKS - used))
        basic_w = weeks - normal_w
        used_in_year[lys] = used + weeks

        recent_first = [history.get(entry.week_end - timedelta(days=7 * i), {})
                        for i in range(1, MAX_LOOKBACK_WEEKS + 1)]
        if worker_type == "fixed_pay":
            normal_rate, basic_rate, wn, wb, idx, extra_flags = _fixed_pay_refs(recent_first, contract_weekly_basic)
            nidx = bidx = idx
        else:
            nref = reference_average([normal_pay(p, holiday_weeks_count) for p in recent_first])
            bref = reference_average([basic_pay(p, holiday_weeks_count) for p in recent_first])
            normal_rate, basic_rate, wn, wb = nref.average, bref.average, _summary(nref), _summary(bref)
            nidx, bidx, extra_flags = nref.indices, bref.indices, []
        wn["weeks_used_dates"] = _dates(entry.week_end, nidx)
        wb["weeks_used_dates"] = _dates(entry.week_end, bidx)
        due = normal_w * normal_rate + basic_w * basic_rate
        paid = dec(history.get(entry.week_end, {}).get("holiday_pay", 0))
        flags = []
        if wn["weeks_used"] == 0:
            flags.append("no_reference_weeks")
        if wn["shortened"] and wn["weeks_used"] > 0:
            flags.append("shortened")
        flags.extend(extra_flags)
        if entry.week_end not in history:
            flags.append("leave_week_missing_from_history")
        rows.append({
            "week_end": entry.week_end, "leave_year_start": lys, "leave_weeks": weeks,
            "normal_weeks": normal_w, "basic_weeks": basic_w, "worker_type": worker_type,
            "paid": money(paid), "due": money(due), "difference": money(due) - money(paid),  # positive = underpaid
            "flags": flags, "working": {"normal": wn, "basic": wb},
        })
    return rows
