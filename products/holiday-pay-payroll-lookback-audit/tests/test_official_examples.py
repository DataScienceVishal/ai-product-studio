"""One test per encoded official example. IDs match benchmark/examples/SOURCES.md."""
import unittest
from datetime import date
from decimal import Decimal as D

from engine import (reference_average, money, statutory_entitlement_days, accrual_hours,
                    rolled_up_pay, part_year_entitlement_weeks, weekly_pay_from_monthly)
from tests import fixtures_gov_monthly as F

NEW = date(2024, 4, 1)

class OfficialExamples(unittest.TestCase):
    def test_E1_part_time_3_days(self):                       # gov.uk: 3 x 5.6 = 16.8
        self.assertEqual(statutory_entitlement_days(3), D("16.8"))

    def test_E2_six_day_cap(self):                            # gov.uk: 6 days/week -> 28
        self.assertEqual(statutory_entitlement_days(6), D(28))

    def test_E3_acas_jamie_70_hours(self):                    # Acas: 70h in June -> 8 hours
        self.assertEqual(accrual_hours(70, NEW, "acas"), D(8))

    def test_E4_acas_round_up_30_mins(self):                  # Acas rule: 30+ minutes rounds up
        self.assertEqual(accrual_hours(D("43.5"), NEW, "acas"), D(5))  # 5.25 -> 5
        self.assertEqual(accrual_hours(D("45"), NEW, "acas"), D(5))    # 5.43 -> 5
        self.assertEqual(accrual_hours(D("46"), NEW, "acas"), D(6))    # 5.55 -> 6

    def test_E5_jian_june_rolled_up(self):                    # Acas: 1000 -> 120.70
        self.assertEqual(rolled_up_pay(1000, NEW), D("120.70"))

    def test_E6_jian_july_rolled_up(self):                    # Acas: 500 -> 60.35
        self.assertEqual(rolled_up_pay(500, NEW), D("60.35"))

    def test_E7_mo_52_week_average(self):                     # Acas: avg 250 -> 250
        r = reference_average([250] * 52)
        self.assertEqual((r.weeks_used, r.average_rounded), (52, D("250.00")))

    def test_E8_corey_26_weeks(self):                         # Acas: use the 26 weeks
        r = reference_average([100] * 26)
        self.assertEqual(r.weeks_used, 26)
        self.assertTrue(r.shortened)

    def test_E9_pat_sick_flat_36(self):                       # Acas: avg 36 -> 36 per week
        self.assertEqual(reference_average([36] * 52).average_rounded, D("36.00"))

    def test_E10_fixed_hours_500(self):                       # gov.uk: 500 a week -> 500
        self.assertEqual(reference_average([500] * 52).average_rounded, D("500.00"))

    def test_E11_table5_paid_unpaid_weeks(self):              # gov.uk Table 5, 12,040/52
        w = [300] + [350] * 4 + [0, 10] + [100] * 15 + [0] * 3 + [400] * 15 + [200] * 5 + [0] * 3 + [180] * 6 + [150] * 5
        self.assertEqual(len(w), 59)
        r = reference_average(w)
        self.assertEqual((r.weeks_used, r.weeks_skipped, r.total), (52, 7, D(12040)))
        # The published figure is 231.34; 12040/52 is 231.54 (arithmetic error in source, see SOURCES.md).
        self.assertEqual(r.average_rounded, D("231.54"))

    def test_E12_table4_monthly_worker(self):                 # gov.uk Tables 3-4: from monthly pay/hours
        weekly = weekly_pay_from_monthly(F.MONTHS, F.WEEKS)
        self.assertEqual([money(w) for w in weekly], [D(x) for x in F.PUBLISHED_WEEKLY])
        # published total 14,606.66 is the sum of the penny-rounded weekly figures (unrounded sum is 14,606.67)
        rounded = [money(w) for w in weekly]
        self.assertEqual(sum(rounded), D("14606.66"))
        self.assertEqual(reference_average(rounded).average_rounded, D("280.90"))
        self.assertEqual(reference_average(weekly).average_rounded, D("280.90"))

    def test_E12b_table4_weeks_9_to_43_average(self):         # gov.uk: weeks 9-43 average 281.56
        weekly = weekly_pay_from_monthly(F.MONTHS, F.WEEKS)
        self.assertEqual(reference_average(weekly[8:43]).average_rounded, D("281.56"))

    def test_E13_hourly_rate_from_monthly(self):              # 1250/130h; weekly from unrounded rate
        out = weekly_pay_from_monthly({"m": (1250, 130)}, [[("m", 25)], [("m", 20)], [("m", 35)], [("m", 35)]])
        self.assertEqual([money(x) for x in out], [D("240.38"), D("192.31"), D("336.54"), D("336.54")])
        self.assertEqual(money(D(1250) / 130), D("9.62"))

    def test_E14_ben_45_of_104(self):                         # gov.uk: paid 45 of 104 weeks -> 45 weeks
        w = ([100] * 5 + [0] * 5) * 9 + [0] * 14               # 45 paid within 104 weeks
        self.assertEqual(len(w), 104)
        r = reference_average(w)
        self.assertEqual((r.weeks_used, r.weeks_scanned), (45, 104))

    def test_E15_amy_75_of_104(self):                         # gov.uk: paid 75 of 104 -> most recent 52 paid
        w = [100] * 75 + [0] * 29                                # 75 paid weeks in 104
        r = reference_average(w)
        self.assertEqual(r.weeks_used, 52)
        self.assertEqual(r.weeks_scanned, 52)

    def test_E16_rachel_20_weeks(self):                       # gov.uk: 20 weeks of service -> average of 20
        r = reference_average([200] * 20)
        self.assertEqual((r.weeks_used, r.average_rounded), (20, D("200.00")))

    def test_E17_leaver_payment_in_lieu(self):                # gov.uk Table 7: 20,520/52 = 394.62; pays 652.09
        w = [324] * 10 + [380] * 20 + [440] * 22
        r = reference_average(w)
        self.assertEqual(r.total, D(20520))
        self.assertEqual(r.average_rounded, D("394.62"))
        weeks = part_year_entitlement_weeks(108, 366)
        self.assertEqual(money(r.average * weeks), D("652.09"))
        # Published method text says 1.66 weeks; 394.62 x 1.66 = 655.07, not 652.09 (see SOURCES.md).
        self.assertEqual(money(D("394.62") * D("1.66")), D("655.07"))


if __name__ == "__main__":
    unittest.main()
