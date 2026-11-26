import unittest
from datetime import date, timedelta
from decimal import Decimal as D

from engine import (reference_average, lookback, LeaveEntry, accrual_hours, rolled_up_pay,
                    accrual_applies, normal_pay, basic_pay)

SAT = date(2025, 6, 7)


def hist(n, weekly, end=SAT, cat="basic"):
    """n weeks of pay ending `end` (inclusive), weekly pay dict or number."""
    out = {}
    for i in range(n):
        p = dict(weekly) if isinstance(weekly, dict) else {cat: weekly}
        out[end - timedelta(days=7 * i)] = p
    return out


class Reference(unittest.TestCase):
    def test_no_pay_weeks_skipped(self):
        r = reference_average([100, 0, 0, 200] + [100] * 60)
        self.assertEqual((r.weeks_used, r.weeks_skipped), (52, 2))

    def test_104_cap(self):
        r = reference_average([100] + [0] * 110)
        self.assertEqual((r.weeks_used, r.weeks_scanned, r.average), (1, 104, D(100)))

    def test_under_52_weeks(self):
        r = reference_average([100, 200, 300])
        self.assertEqual((r.weeks_used, r.average, r.shortened), (3, D(200), True))

    def test_zero_pay(self):
        r = reference_average([0] * 104)
        self.assertEqual((r.weeks_used, r.average), (0, D(0)))

    def test_empty(self):
        self.assertEqual(reference_average([]).average, D(0))

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            reference_average([10, -1])

    def test_tiny_pay_counts_as_paid(self):
        self.assertEqual(reference_average([D("0.01")] * 52).weeks_used, 52)


class Accrual(unittest.TestCase):
    def test_boundary_1_april_2024(self):
        self.assertTrue(accrual_applies(date(2024, 4, 1)))
        self.assertFalse(accrual_applies(date(2024, 3, 31)))
        self.assertEqual(rolled_up_pay(100, date(2024, 4, 1)), D("12.07"))
        with self.assertRaises(ValueError):
            rolled_up_pay(100, date(2024, 3, 31))
        with self.assertRaises(ValueError):
            accrual_hours(10, date(2024, 1, 1))

    def test_zero_hours_and_pay(self):
        self.assertEqual(accrual_hours(0, date(2025, 4, 1)), D(0))
        self.assertEqual(rolled_up_pay(0, date(2025, 4, 1)), D("0.00"))

    def test_unrounded(self):
        self.assertEqual(accrual_hours(70, date(2025, 4, 1), "none"), D("8.449"))

    def test_bad_rounding(self):
        with self.assertRaises(ValueError):
            accrual_hours(1, date(2025, 4, 1), "x")


class Elements(unittest.TestCase):
    P = {"basic": 400, "regular_overtime": 50, "commission": 25, "allowance": 10,
         "bonus_non_regular": 500, "expense_excluded": 40, "holiday_pay": 300, "statutory": 99}

    def test_normal_vs_basic(self):
        self.assertEqual(normal_pay(self.P), D(485))
        self.assertEqual(basic_pay(self.P), D(400))

    def test_holiday_week_option(self):
        self.assertEqual(normal_pay(self.P, True), D(785))

    def test_unknown_category(self):
        with self.assertRaises(ValueError):
            normal_pay({"mystery": 1})


class Lookback(unittest.TestCase):
    def setUp(self):
        # 110 weeks of 300 basic + 60 overtime; leave week has holiday paid at basic only
        self.h = hist(110, {"basic": 300, "regular_overtime": 60})
        self.leave_we = SAT + timedelta(days=7)
        self.h[self.leave_we] = {"holiday_pay": 300}

    def test_underpayment_shown_with_working(self):
        rows = lookback(self.h, [LeaveEntry(self.leave_we)])
        r = rows[0]
        self.assertEqual((r["paid"], r["due"], r["difference"]), (D("300.00"), D("360.00"), D("60.00")))
        self.assertEqual(r["working"]["normal"]["weeks_used"], 52)
        self.assertEqual(r["working"]["normal"]["average"], D("360.00"))
        self.assertEqual(r["working"]["basic"]["average"], D("300.00"))

    def test_fifth_week_basic_only(self):
        entries = []
        for i in range(5):
            we = self.leave_we + timedelta(days=7 * i)
            self.h[we] = {"holiday_pay": 300}
            entries.append(LeaveEntry(we))
        rows = lookback(self.h, entries)
        self.assertEqual([r["due"] for r in rows[:4]], [D("360.00")] * 4)
        self.assertEqual((rows[4]["due"], rows[4]["difference"]), (D("300.00"), D("0.00")))
        rows = lookback(self.h, entries, uplift_all_leave=True)
        self.assertEqual(rows[4]["due"], D("360.00"))

    def test_leave_year_boundary_resets_split(self):
        # 3 weeks in March 2025 (year 2024/25) then 1 week in April 2025 (new year)
        h = hist(150, {"basic": 300, "regular_overtime": 60}, end=date(2025, 5, 31))
        entries = [LeaveEntry(date(2025, 3, 15)), LeaveEntry(date(2025, 3, 22)), LeaveEntry(date(2025, 3, 29)),
                   LeaveEntry(date(2025, 4, 12))]
        rows = lookback(h, entries)
        self.assertEqual([r["leave_year_start"] for r in rows],
                         [date(2024, 4, 1)] * 3 + [date(2025, 4, 1)])
        self.assertEqual(rows[3]["normal_weeks"], D(1))

    def test_history_under_52_weeks(self):
        h = hist(10, {"basic": 200})
        we = SAT + timedelta(days=7)
        rows = lookback(h, [LeaveEntry(we)])
        w = rows[0]["working"]["normal"]
        self.assertEqual((w["weeks_used"], w["shortened"], rows[0]["due"]), (10, True, D("200.00")))

    def test_no_history_zero_due(self):
        rows = lookback({}, [LeaveEntry(SAT)])
        self.assertEqual((rows[0]["due"], rows[0]["paid"]), (D("0.00"), D("0.00")))

    def test_no_pay_weeks_skipped_within_104(self):
        h = hist(30, {"basic": 100}, end=SAT - timedelta(days=7 * 40))   # paid 30 weeks, then 40 empty weeks
        rows = lookback(h, [LeaveEntry(SAT + timedelta(days=7))])
        w = rows[0]["working"]["normal"]
        self.assertEqual((w["weeks_used"], w["weeks_scanned"]), (30, 104))

    def test_holiday_weeks_excluded_by_default(self):
        h = hist(60, {"basic": 300})
        for i in range(1, 5):
            h[SAT - timedelta(days=7 * i)] = {"holiday_pay": 50}
        rows = lookback(h, [LeaveEntry(SAT + timedelta(days=7))])
        self.assertEqual(rows[0]["working"]["normal"]["average"], D("300.00"))
        self.assertEqual(rows[0]["working"]["normal"]["weeks_skipped"], 4)


if __name__ == "__main__":
    unittest.main()
