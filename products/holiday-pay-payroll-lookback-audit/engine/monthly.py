"""Monthly-paid workers: weekly pay from monthly pay and hours (gov.uk guidance)."""
from decimal import Decimal
from typing import Dict, List, Sequence, Tuple
from .reference import dec


def weekly_pay_from_monthly(months: Dict[str, Tuple[object, object]],
                            weeks: Sequence[Sequence[Tuple[str, object]]]) -> List[Decimal]:
    """Unrounded weekly pay for each week.

    months: {month_key: (month_pay, month_hours)}; hourly rate = pay / hours,
    kept unrounded (the published figures only reproduce unrounded).
    weeks: for each week a list of (month_key, hours_worked_in_that_month), so a
    week spanning two months uses both months' rates. Round with money() at the end.
    """
    rates = {}
    for k, (pay, hours) in months.items():
        h = dec(hours)
        if h <= 0:
            raise ValueError(f"month {k} has no hours")
        rates[k] = dec(pay) / h
    out = []
    for segs in weeks:
        total = Decimal(0)
        for key, hours in segs:
            if key not in rates:
                raise ValueError(f"no monthly data for {key}")
            total += rates[key] * dec(hours)
        out.append(total)
    return out
