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
        # 5 weeks in March 2025 (year 2024/25), then 1 week in April 2025 (new year):
        # 5th old-year week is basic only; first new-year week is back to normal pay.
        h = hist(150, {"basic": 300, "regular_overtime": 60}, end=date(2025, 5, 31))
        marches = [date(2025, 3, d) for d in (1, 8, 15, 22, 29)]
        rows = lookback(h, [LeaveEntry(d) for d in marches] + [LeaveEntry(date(2025, 4, 5))])
        self.assertEqual(rows[4]["basic_weeks"], D(1))
        self.assertEqual(rows[4]["due"], D("300.00"))
        self.assertEqual(rows[5]["leave_year_start"], date(2025, 4, 1))
        self.assertEqual((rows[5]["normal_weeks"], rows[5]["basic_weeks"], rows[5]["due"]), (D(1), D(0), D("360.00")))

    def test_fixed_pay_rise_no_false_overpayment(self):
        h = hist(60, {"basic": 400})
        for i in range(4):                                    # pay rise to 500 in last 4 weeks
            h[SAT - timedelta(days=7 * i)] = {"basic": 500}
        we = SAT + timedelta(days=7)
        h[we] = {"holiday_pay": 500}
        r = lookback(h, [LeaveEntry(we)], worker_type="fixed_pay")[0]
        self.assertEqual((r["paid"], r["due"], r["difference"]), (D("500.00"), D("500.00"), D("0.00")))
        v = lookback(h, [LeaveEntry(we)])[0]                  # variable-hours treatment averages
        self.assertEqual(v["due"], D("407.69"))

    def _fixed(self, last_week, **kw):
        h = hist(60, {"basic": 500})
        h[SAT] = last_week
        we = SAT + timedelta(days=7)
        h[we] = {"holiday_pay": 500}
        return lookback(h, [LeaveEntry(we)], worker_type="fixed_pay", **kw)[0]

    def test_fixed_pay_sick_week_before_leave_ssp(self):
        r = self._fixed({"basic": 100, "statutory": 99})
        self.assertEqual((r["due"], r["difference"]), (D("500.00"), D("0.00")))
        self.assertIn("latest_week_basic_differs_from_rate_used", r["flags"])

    def test_fixed_pay_short_week_before_leave(self):
        # T-137: the rate is the most recent basic in the last 8 weeks, so a part week is used and flagged ambiguous
        r = self._fixed({"basic": 100})
        self.assertEqual((r["due"], r["difference"]), (D("100.00"), D("-400.00")))
        self.assertNotIn("latest_week_basic_differs_from_rate_used", r["flags"])   # the latest week IS the rate now
        self.assertIn("rate_inferred_ambiguous", r["flags"])
        self.assertEqual(r["working"]["normal"]["basic_source"], "latest_basic_last_8_weeks")

    def test_fixed_pay_explicit_contract_basic(self):
        r = self._fixed({"basic": 100}, contract_weekly_basic=520)
        self.assertEqual(r["due"], D("520.00"))
        self.assertEqual(r["working"]["normal"]["basic_source"], "contract")
        self.assertIn("latest_week_basic_differs_from_rate_used", r["flags"])

    def test_fixed_pay_no_flag_when_latest_matches(self):
        self.assertNotIn("latest_week_basic_differs_from_rate_used", self._fixed({"basic": 500})["flags"])

    def test_reference_week_dates_reported(self):
        h = hist(60, {"basic": 100})
        h[SAT - timedelta(days=7)] = {}                       # a no-pay week inside the period
        we = SAT + timedelta(days=7)
        r = lookback(h, [LeaveEntry(we)])[0]["working"]["normal"]
        dates = r["weeks_used_dates"]
        self.assertEqual(len(dates), 52)
        self.assertEqual(dates[-1], SAT)                      # most recent week used
        self.assertNotIn(SAT - timedelta(days=7), dates)      # skipped no-pay week
        self.assertEqual(dates[0], SAT - timedelta(days=7 * 52))  # 53 back, one skipped
        self.assertEqual(dates, sorted(dates))

    def test_fixed_pay_back_pay_week_not_the_rate(self):
        r = self._fixed({"basic": 1000})                      # one-off back pay week before leave: now used, but flagged (T-137)
        self.assertEqual((r["due"], r["difference"]), (D("1000.00"), D("500.00")))
        self.assertIn("rate_inferred_ambiguous", r["flags"])
        self.assertIn("rate_inferred_no_contract_basic", r["flags"])

    def test_fixed_pay_contract_flags_deviating_reference_week(self):
        r = self._fixed({"basic": 1000}, contract_weekly_basic=500)
        self.assertEqual(r["due"], D("500.00"))
        self.assertIn("reference_week_basic_differs_from_contract", r["flags"])
        self.assertNotIn("rate_inferred_no_contract_basic", r["flags"])

    def test_fixed_pay_rate_excludes_ssp_weeks(self):
        h = hist(60, {"basic": 500})
        for i in range(5):                                    # 5 of last 8 weeks are SSP weeks at basic 300
            h[SAT - timedelta(days=7 * i)] = {"basic": 300, "statutory": 99}
        we = SAT + timedelta(days=7)
        r = lookback(h, [LeaveEntry(we)], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("500.00"))

    def test_fixed_pay_rate_window_is_8_weeks(self):
        h = hist(60, {"basic": 400})
        for i in range(2, 8):                                 # weeks 3-8 back at 500, week 1-2 at 400, older 400
            h[SAT - timedelta(days=7 * i)] = {"basic": 500}
        we = SAT + timedelta(days=7)
        r = lookback(h, [LeaveEntry(we)], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("400.00"))   # most recent wins
        self.assertIn("rate_inferred_ambiguous", r["flags"])
        for i in range(8):                                    # all 8 weeks at 500, 400 only before the window
            h[SAT - timedelta(days=7 * i)] = {"basic": 500}
        r = lookback(h, [LeaveEntry(we)], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("500.00"))
        self.assertNotIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_rate_is_most_recent_not_most_common(self):
        h = hist(60, {"basic": 400})
        for i in range(4):
            h[SAT - timedelta(days=7 * i)] = {"basic": 450}
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("450.00"))
        self.assertIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_dates_reported(self):
        r = self._fixed({"basic": 500})
        dates = r["working"]["normal"]["weeks_used_dates"]
        self.assertEqual((len(dates), dates[-1]), (52, SAT))
        self.assertEqual(r["working"]["basic"]["weeks_used_dates"], dates)

    def test_fixed_pay_all_recent_weeks_ssp_fallback(self):
        h = hist(60, {"basic": 500})
        for i in range(8):
            h[SAT - timedelta(days=7 * i)] = {"basic": 200 + i, "statutory": 50}
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("500.00"))   # latest NON-statutory basic, not the SSP one
        self.assertEqual(r["working"]["normal"]["basic_source"], "latest_week_fallback")
        self.assertIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_long_sickness_uses_last_full_pay_rate(self):
        h = hist(60, {"basic": 500})
        for i in range(10):                                   # 10 SSP weeks at basic 100 just before leave
            h[SAT - timedelta(days=7 * i)] = {"basic": 100, "statutory": 99}
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("500.00"))
        self.assertIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_fallback_skips_part_leave_week(self):
        h = hist(60, {"basic": 500})
        for i in range(10):                                   # 10 weeks before leave with no basic in the window
            h[SAT - timedelta(days=7 * i)] = {"regular_overtime": 20}
        h[SAT - timedelta(days=7 * 3)] = {"basic": 200, "holiday_pay": 300}   # part-leave week
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("500.00"))
        self.assertEqual(r["working"]["normal"]["basic_source"], "latest_week_fallback")
        self.assertIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_fallback_tier2_prefers_part_leave_over_newer_ssp(self):
        h = hist(60, {"regular_overtime": 20})                # no full week with basic anywhere
        h[SAT] = {"basic": 80, "statutory": 99}               # SSP week, most recent
        h[SAT - timedelta(days=7 * 3)] = {"basic": 200, "holiday_pay": 300}   # older part-leave week
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("200.00"))   # tier 2, not tier 3's 80
        self.assertEqual(r["working"]["normal"]["basic_source"], "latest_week_fallback")
        self.assertIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_only_ssp_weeks_carry_basic(self):
        h = hist(8, {"basic": 100, "statutory": 99})
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("100.00"))
        self.assertNotIn("no_basic_pay_found", r["flags"])

    def test_fixed_pay_no_basic_anywhere(self):
        h = hist(6, {"regular_overtime": 30})
        r = lookback(h, [LeaveEntry(SAT + timedelta(days=7))], worker_type="fixed_pay")[0]
        self.assertEqual(r["working"]["normal"]["current_basic"], D("0.00"))
        self.assertIn("no_basic_pay_found", r["flags"])
        self.assertIn("rate_inferred_ambiguous", r["flags"])

    def test_fixed_pay_contract_given_no_new_flags(self):
        r = self._fixed({"basic": 100}, contract_weekly_basic=500)
        self.assertNotIn("rate_inferred_ambiguous", r["flags"])
        self.assertNotIn("no_basic_pay_found", r["flags"])

    def test_fixed_pay_plus_variable_average(self):
        h = hist(60, {"basic": 300, "regular_overtime": 60})
        we = SAT + timedelta(days=7)
        r = lookback(h, [LeaveEntry(we)], worker_type="fixed_pay")[0]
        self.assertEqual(r["due"], D("360.00"))

    def test_bad_worker_type(self):
        with self.assertRaises(ValueError):
            lookback({}, [], worker_type="x")

    def test_misaligned_leave_date_raises(self):
        h = hist(60, {"basic": 300})                          # Saturdays
        with self.assertRaises(ValueError):
            lookback(h, [LeaveEntry(SAT + timedelta(days=6))])   # a Friday

    def test_mixed_weekday_history_raises(self):
        h = hist(10, {"basic": 300})
        h[SAT - timedelta(days=1)] = {"basic": 1}
        with self.assertRaises(ValueError):
            lookback(h, [LeaveEntry(SAT)])

    def test_bad_leave_weeks(self):
        for w in (D(0), D(-1)):
            with self.assertRaises(ValueError):
                lookback(hist(10, {"basic": 1}), [LeaveEntry(SAT, w)])

    def test_float_input_no_binary_noise(self):
        self.assertEqual(normal_pay({"basic": 0.1, "commission": 0.2}), D("0.3"))

    def test_history_under_52_weeks(self):
        h = hist(10, {"basic": 200})
        we = SAT + timedelta(days=7)
        rows = lookback(h, [LeaveEntry(we)])
        w = rows[0]["working"]["normal"]
        self.assertEqual((w["weeks_used"], w["shortened"], rows[0]["due"]), (10, True, D("200.00")))
        self.assertIn("shortened", rows[0]["flags"])

    def test_no_history_is_flagged_not_silent(self):
        rows = lookback({}, [LeaveEntry(SAT)])
        self.assertEqual((rows[0]["due"], rows[0]["paid"]), (D("0.00"), D("0.00")))
        self.assertIn("no_reference_weeks", rows[0]["flags"])
        self.assertIn("leave_week_missing_from_history", rows[0]["flags"])

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


class AlwaysException(unittest.TestCase):
    def test_always_exception_flags(self):
        from report.builder import always_exception
        self.assertTrue(always_exception({"flags": ["rate_inferred_ambiguous"]}))
        self.assertTrue(always_exception({"flags": ["no_basic_pay_found"]}))
        self.assertTrue(always_exception({"flags": ["shortened", "rate_inferred_ambiguous", "no_basic_pay_found"]}))
        self.assertFalse(always_exception({"flags": []}))
        self.assertFalse(always_exception({"flags": ["rate_inferred_no_contract_basic", "shortened", "no_reference_weeks"]}))


if __name__ == "__main__":
    unittest.main()

