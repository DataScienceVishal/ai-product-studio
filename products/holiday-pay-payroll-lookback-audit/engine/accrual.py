"""Entitlement, 12.07% accrual and rolled-up holiday pay."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from .reference import money

ACCRUAL_RATE = Decimal("0.1207")
RULES_START = date(2024, 4, 1)   # leave years starting on/after this date
STATUTORY_WEEKS = Decimal("5.6")
CAP_DAYS = Decimal("28")


def accrual_applies(leave_year_start: date) -> bool:
    """12.07% accrual / rolled-up pay only for leave years starting on or after 1 April 2024."""
    return leave_year_start >= RULES_START


def statutory_entitlement_days(days_per_week) -> Decimal:
    """5.6 x days per week, capped at 28 days (gov.uk)."""
    return min(Decimal(days_per_week) * STATUTORY_WEEKS, CAP_DAYS)


def accrual_hours(hours_worked, leave_year_start: date, rounding: str = "acas") -> Decimal:
    """Holiday hours accrued in a pay period: 12.07% of hours worked.

    rounding 'acas': whole hours, part-hour under 30 mins rounded down, 30 mins
    or more rounded up (Acas). 'none': unrounded (do not round down).
    """
    if not accrual_applies(leave_year_start):
        raise ValueError("12.07% accrual applies only to leave years starting on or after 2024-04-01")
    raw = Decimal(hours_worked) * ACCRUAL_RATE
    if rounding == "acas":
        return raw.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    if rounding == "none":
        return raw
    raise ValueError("rounding must be 'acas' or 'none'")


def rolled_up_pay(period_pay, leave_year_start: date) -> Decimal:
    """Rolled-up holiday pay: 12.07% of total pay in the pay period, to the penny."""
    if not accrual_applies(leave_year_start):
        raise ValueError("rolled-up holiday pay for irregular/part-year workers applies only to leave years starting on or after 2024-04-01")
    return money(Decimal(period_pay) * ACCRUAL_RATE)


def part_year_entitlement_weeks(days_employed, days_in_leave_year, round_up_2dp: bool = True) -> Decimal:
    """Leaver entitlement in weeks: proportion of year x 5.6.

    gov.uk worked example rounds the proportion and weeks up to 2dp; the
    unrounded product reproduces the published payment (see SOURCES.md).
    """
    prop = Decimal(days_employed) / Decimal(days_in_leave_year)
    return prop * STATUTORY_WEEKS
