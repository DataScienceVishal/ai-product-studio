"""T-150 (T-149 security L-1): look-back sections in report.md are capped like rolled-up ones; exceptions.csv stays complete."""
import os
import unittest
from datetime import date, timedelta
from decimal import Decimal as D

import report.builder as b
from tests.test_t130 import Case, H, LV

W = "worker_id,worker_type,contract_weekly_basic\n"


def _guessed(n_workers, n_weeks):
    """fixed_pay workers with no contract basic and no basic pay: every leave week is a guessed-rate exception."""
    h, l, w = H, LV, W
    for k in range(n_workers):
        wid = f"F{k:03d}"
        w += f"{wid},fixed_pay,\n"
        for i in range(n_weeks):
            d = (date(2025, 4, 5) + timedelta(days=7 * i)).isoformat()
            if i % 2:
                h += f"{wid},{d},holiday_pay,100\n"
                l += f"{wid},{d}\n"
            else:
                h += f"{wid},{d},regular_overtime,100\n"
    return h, l, w


def _csv_rows(d):
    with open(os.path.join(d, "out", "exceptions.csv"), encoding="utf-8") as fh:
        return len(fh.read().splitlines()) - 1


class LookbackCapCLI(Case):
    def test_per_worker_cap_csv_complete(self):
        h, l, w = _guessed(1, 60)   # 30 leave weeks, all exceptions
        code, so, se, rep = self.run_cli(h, l, w)
        self.assertEqual(code, 0, se)
        self.assertEqual(_csv_rows(self.d), 30)
        self.assertEqual(rep.count(", week ending "), b.MAX_LOOKBACK_DETAILS)
        self.assertIn("### F000: and 10 more look-back exception(s)", rep)
        self.assertIn("are in exceptions.csv", rep)

    def test_total_cap_and_size_bound(self):
        h, l, w = _guessed(60, 60)  # 1,800 exceptions: uncapped this was one section each
        code, so, se, rep = self.run_cli(h, l, w)
        self.assertEqual(code, 0, se)
        self.assertEqual(_csv_rows(self.d), 1800)
        self.assertEqual(rep.count(", week ending "), b.MAX_LOOKBACK_TOTAL)
        self.assertEqual(rep.count("more look-back exception(s)\n"), b.MAX_LOOKBACK_SUMMARIES)
        self.assertIn("### and 300 more look-back exception(s) for 10 further worker(s)", rep)
        self.assertLess(len(rep.encode("utf-8")), 1_000_000)

    def test_small_input_not_capped(self):
        h, l, w = _guessed(2, 20)   # 10 leave weeks each: under the cap
        code, so, se, rep = self.run_cli(h, l, w)
        self.assertEqual(rep.count(", week ending "), 20)
        self.assertNotIn("more look-back exception", rep)


def _row(wid, week, diff, flags=()):
    return {"worker_id": wid, "week_end": date(2025, 4, 5) + timedelta(days=7 * week), "difference": D(diff),
            "flags": list(flags)}


class Priority(unittest.TestCase):
    def test_underpayments_shown_before_guessed_zero_rows(self):
        rows = [_row("A", i, "0", ["no_basic_pay_found"]) for i in range(30)] + [_row("A", 30, "250")]
        keep = b._pick_lookback(rows)
        self.assertEqual(len(keep), b.MAX_LOOKBACK_DETAILS)
        self.assertIn(30, keep)              # the one real underpayment, last in file order, is kept
        self.assertEqual(sorted(keep)[:19], list(range(19)))   # ties keep file order

    def test_order_underpaid_cannot_check_overpaid_zero(self):
        rows = [_row("A", 0, "0", ["rate_inferred_ambiguous"]), _row("A", 1, "-5"),
                _row("A", 2, "0", ["no_reference_weeks"]), _row("A", 3, "1"), _row("A", 4, "9")]
        order = sorted(range(len(rows)), key=lambda i: (b._lookback_priority(rows[i]), i))
        self.assertEqual(order, [4, 3, 2, 1, 0])

    def test_summary_line_counts_and_escapes(self):
        rs = [_row("a*b", 0, "10"), _row("a*b", 1, "-4"), _row("a*b", 2, "0", ["no_reference_weeks"]),
              _row("a*b", 3, "0", ["no_basic_pay_found"])]
        s = b._lookback_more_line("a*b", rs)
        self.assertIn("### a\\*b: and 4 more", s)
        self.assertIn("1 underpaid, £10.00 in total", s)
        self.assertIn("1 overpaid, £4.00 in total", s)
        self.assertIn("1 cannot be checked", s)
        self.assertIn("1 at £0.00 with a guessed weekly rate", s)

    def test_global_cap_prefers_underpayments_across_workers(self):
        rows = [_row(f"Z{k:03d}", i, "0", ["no_basic_pay_found"]) for k in range(30) for i in range(20)]
        rows.append(_row("U", 0, "99"))
        keep = b._pick_lookback(rows)
        self.assertEqual(len(keep), b.MAX_LOOKBACK_TOTAL)
        self.assertIn(len(rows) - 1, keep)


if __name__ == "__main__":
    unittest.main()
