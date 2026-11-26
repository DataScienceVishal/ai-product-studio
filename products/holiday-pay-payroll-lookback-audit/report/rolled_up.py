"""Week-by-week check of rolled-up holiday pay for irregular_rolled_up workers.

Rules (the engine decides lawfulness by leave year, see engine.accrual.accrual_applies):
- a week in a leave year that started before 2024-04-01 with rolled_up_holiday_pay > 0: flag
  `rolled_up_before_2024_rules` (rolled-up pay was not allowed under the rules of that time);
- a week in a leave year that started on or after 2024-04-01 with pay that counts > 0 and no rolled_up_holiday_pay
  row: flag `rolled_up_not_shown_separately`;
- otherwise the rolled-up amount is recalculated as 12.07% of the pay that counts and compared with what was paid.
A week with no pay that counts and no rolled-up row has nothing to check and produces no row.
Leave years start on 1 April and a week belongs to the year containing its week-ending date.
"""
from decimal import Decimal

from engine import accrual_applies, normal_pay, rolled_up_pay, ROLLED_UP, money, dec
from engine.lookback import ROLLED_UP_TYPE, _leave_year_start

BEFORE_2024 = "rolled_up_before_2024_rules"
NOT_SEPARATE = "rolled_up_not_shown_separately"
HOLIDAY_PAID = "holiday_pay_paid_to_rolled_up_worker"
FLAG_TEXT = {
    HOLIDAY_PAID: "holiday_pay was paid in this week to a worker whose holiday pay is rolled up into each wage packet; "
                  "check whether this is a second payment of the same holiday pay or whether the worker is not on rolled-up pay",
    BEFORE_2024: "rolled-up holiday pay is recorded in a leave year that started before 1 April 2024; "
                 "the rolled-up method only applies to leave years starting on or after that date, so no recalculation is made",
    NOT_SEPARATE: "this week has pay that counts but no rolled_up_holiday_pay row; rolled-up holiday pay must be shown "
                  "as a separate item on the payslip, so a figure cannot be compared",
}


def check_week(worker_id, week_end, pay, threshold):
    """Return a result row for one pay week of an irregular_rolled_up worker, or None if there is nothing to check.

    The row has kind 'rolled_up', paid (the rolled-up amount recorded), counts (pay that counts), due (the amount
    recalculated under these settings, or None when the rules do not allow one), difference (positive = paid
    less than recalculated), flags and `exception` (True when it belongs in exceptions.csv).
    """
    lys = _leave_year_start(week_end, 4, 1)
    has_row = ROLLED_UP in pay
    paid = money(dec(pay.get(ROLLED_UP, 0)))
    counts = normal_pay(pay)
    row = {"kind": "rolled_up", "worker_id": worker_id, "week_end": week_end, "leave_year_start": lys,
           "paid": paid, "counts": money(counts), "due": None, "difference": None, "flags": [], "exception": False}
    if not accrual_applies(lys):
        if paid > 0:
            row["flags"].append(BEFORE_2024)
            row["exception"] = True
            return row
        return None
    if counts > 0 and not has_row:
        row["flags"].append(NOT_SEPARATE)
        row["exception"] = True
        return row
    if not has_row and counts == 0:
        return None
    row["due"] = rolled_up_pay(counts, lys)
    row["difference"] = row["due"] - paid
    row["exception"] = abs(row["difference"]) > threshold
    return row


def holiday_pay_row(worker_id, week_end, pay):
    """An exception row when an irregular_rolled_up worker has holiday_pay above 0 in a week, else None."""
    amount = money(dec(pay.get("holiday_pay", 0)))
    if amount <= 0:
        return None
    return {"kind": "rolled_up", "worker_id": worker_id, "week_end": week_end,
            "leave_year_start": _leave_year_start(week_end, 4, 1), "paid": amount, "counts": money(normal_pay(pay)),
            "due": None, "difference": None, "flags": [HOLIDAY_PAID], "exception": True}


def audit_rolled_up(workers, threshold):
    """Return (checked_rows, exceptions) over every irregular_rolled_up worker's pay weeks, in worker then week order."""
    checked = []
    for wid in sorted(workers):
        w = workers[wid]
        if w.worker_type != ROLLED_UP_TYPE:
            continue
        for d in sorted(w.history):
            r = check_week(wid, d, w.history[d], threshold)
            if r is not None:
                checked.append(r)
            h = holiday_pay_row(wid, d, w.history[d])
            if h is not None:
                checked.append(h)
    return checked, [r for r in checked if r["exception"]]


def rolled_up_leave_weeks(workers):
    """{worker_id: number of leave.csv weeks} for irregular_rolled_up workers; the look-back does not re-audit them."""
    return {wid: len(w.leave) for wid, w in sorted(workers.items()) if w.worker_type == ROLLED_UP_TYPE and w.leave}


def holiday_pay_to_rolled_up(workers):
    """{worker_id: [week endings with holiday_pay above 0]} for irregular_rolled_up workers."""
    out = {}
    for wid in sorted(workers):
        w = workers[wid]
        if w.worker_type == ROLLED_UP_TYPE:
            weeks = sorted(d for d, p in w.history.items() if dec(p.get("holiday_pay", 0)) > 0)
            if weeks:
                out[wid] = weeks
    return out


def stray_rolled_up(workers):
    """{worker_id: [week endings with a rolled_up_holiday_pay row]} for workers not set as irregular_rolled_up."""
    out = {}
    for wid in sorted(workers):
        w = workers[wid]
        if w.worker_type == ROLLED_UP_TYPE:
            continue
        weeks = sorted(d for d, p in w.history.items() if ROLLED_UP in p)
        if weeks:
            out[wid] = weeks
    return out


def explain_rolled_up(r, gbp, esc=str):
    """Plain-English working for one result row; gbp formats pounds, esc escapes untrusted text."""
    if r["flags"] == [HOLIDAY_PAID]:
        return (f"### {esc(r['worker_id'])}, pay week ending {r['week_end']} (rolled-up holiday pay)\n\n"
                f"- holiday_pay recorded: {gbp(r['paid'])}. Pay that counts this week: {gbp(r['counts'])}.\n"
                f"- Flag `{HOLIDAY_PAID}`: {FLAG_TEXT[HOLIDAY_PAID]}.\n")
    lines = [f"### {esc(r['worker_id'])}, pay week ending {r['week_end']} (rolled-up holiday pay)", "",
             f"- Leave year starting {r['leave_year_start']}. Pay that counts this week: {gbp(r['counts'])}. "
             f"Rolled-up holiday pay recorded: {gbp(r['paid'])}."]
    if r["due"] is not None:
        d = r["difference"]
        lines.append(f"- Recalculated under these settings: 12.07% x {gbp(r['counts'])} = {gbp(r['due'])}. "
                     f"Result: {'underpaid' if d > 0 else 'overpaid' if d < 0 else 'correct'} by {gbp(abs(d))}.")
    for f in r["flags"]:
        lines.append(f"- Flag `{f}`: {FLAG_TEXT[f]}.")
    return "\n".join(lines) + "\n"
