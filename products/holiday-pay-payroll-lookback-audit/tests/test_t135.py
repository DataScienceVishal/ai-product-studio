import unittest
from datetime import date, timedelta
from decimal import Decimal as D

from engine import lookback, LeaveEntry

SAT = date(2025, 6, 7)


def run(weeks_oldest_first):
    """History ends the week before the leave week."""
    n = len(weeks_oldest_first)
    leave = SAT + timedelta(days=7 * n)
    h = {SAT + timedelta(days=7 * i): p for i, p in enumerate(weeks_oldest_first)}
    return lookback(h, [LeaveEntry(leave)], worker_type="fixed_pay", contract_weekly_basic=100)[0]


class F3FixedPayPaidWeeks(unittest.TestCase):
    def test_overtime_only_week_counts_as_paid(self):
        weeks = [{"basic": 100, "regular_overtime": 20}] * 4 + [{"regular_overtime": 40}]
        r = run(weeks)
        self.assertEqual(r["due"], D("124.00"))
        self.assertEqual(r["working"]["normal"]["weeks_used"], 5)

    def test_zero_pay_week_still_skipped(self):
        weeks = [{"basic": 100, "regular_overtime": 20}] * 4 + [{}, {"holiday_pay": 50}]
        r = run(weeks)
        self.assertEqual(r["due"], D("120.00"))
        self.assertEqual(r["working"]["normal"]["weeks_used"], 4)


if __name__ == "__main__":
    unittest.main()
