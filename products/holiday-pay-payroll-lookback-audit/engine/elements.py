"""Which pay elements count for holiday pay.

Reg 13 (4 weeks, EU-derived): normal remuneration = basic + regular overtime +
commission + status-related allowances. Reg 13A (remaining 1.6 weeks): basic
pay is allowed. Bonuses that are not regular/linked to work, expenses, holiday
pay itself and statutory payments (SSP/SMP etc) are excluded. Treating
`allowance` as counting means status-related allowances (length of service,
seniority); non-status allowances need adviser review.
"""
from decimal import Decimal

CATEGORIES = ("basic", "regular_overtime", "commission", "bonus_non_regular",
              "allowance", "expense_excluded", "holiday_pay", "statutory")
COUNTS_FOR_NORMAL = frozenset({"basic", "regular_overtime", "commission", "allowance"})
BASIC_ONLY = frozenset({"basic"})


def _sum(pay: dict, cats) -> Decimal:
    unknown = set(pay) - set(CATEGORIES)
    if unknown:
        raise ValueError(f"unknown pay category: {sorted(unknown)}")
    return sum((Decimal(v) for k, v in pay.items() if k in cats), Decimal(0))


def normal_pay(pay: dict, include_holiday_pay: bool = False) -> Decimal:
    cats = set(COUNTS_FOR_NORMAL)
    if include_holiday_pay:      # no-regular-hours workers: holiday week counts (gov.uk Table 9)
        cats.add("holiday_pay")
    return _sum(pay, cats)


def basic_pay(pay: dict, include_holiday_pay: bool = False) -> Decimal:
    cats = set(BASIC_ONLY)
    if include_holiday_pay:
        cats.add("holiday_pay")
    return _sum(pay, cats)
