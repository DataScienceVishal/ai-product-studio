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


class StraddleAndFlags(unittest.TestCase):
    def test_leave_row_straddling_four_week_point_is_split_pro_rata(self):
        h = {SAT + timedelta(days=7 * i): {"basic": 200} for i in range(10)}
        # basic-only average differs from normal pay: overtime in every week
        h = {d: {"basic": 100, "regular_overtime": 100} for d in h}
        leave = SAT + timedelta(days=7 * 10)
        # rows the CLI accepts (at most 1 week each): 1 + 1 + 1 + 0.5 = 3.5, then a 1.0 row straddles
        widths = [D("1"), D("1"), D("1"), D("0.5"), D("1")]
        entries = [LeaveEntry(leave + timedelta(days=7 * i), w) for i, w in enumerate(widths)]
        rows = lookback(h, entries)
        for r, w in zip(rows[:4], widths[:4]):
            self.assertEqual((r["normal_weeks"], r["basic_weeks"]), (w, 0))
        self.assertEqual((rows[4]["normal_weeks"], rows[4]["basic_weeks"]), (D("0.5"), D("0.5")))
        self.assertEqual(rows[4]["due"], D("150.00"))      # 0.5 x 200 normal + 0.5 x 100 basic

    def test_overtime_only_week_does_not_fire_basic_differs_flag(self):
        weeks = [{"basic": 100, "regular_overtime": 20}] * 4 + [{"regular_overtime": 40}]
        self.assertNotIn("reference_week_basic_differs_from_contract", run(weeks)["flags"])

    def test_part_basic_week_still_fires_basic_differs_flag(self):
        weeks = [{"basic": 100}] * 4 + [{"basic": 60}]
        self.assertIn("reference_week_basic_differs_from_contract", run(weeks)["flags"])


if __name__ == "__main__":
    unittest.main()
