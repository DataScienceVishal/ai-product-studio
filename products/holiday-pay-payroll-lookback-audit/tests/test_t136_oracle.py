"""T-136 blind differential oracle: (1) fixed_pay with a changing basic / contract_weekly_basic, (2) rolled-up holiday pay.

Written from ingest/FORMAT.md, README.md, BRIEF.md, tests/test_rolled_up.py (documented behaviour only), gov.uk guidance and
black-box probes of the CLI; no engine/ or report/ source was read.  Helpers are copied from tests/test_differential.py.
Findings (T136-F*) are described in reviews/T-136-qa.md.

Part 1 rules (oracle):
  * workers.csv carries ONE contract_weekly_basic per worker; it cannot change over time (T136-F1).
  * contract given: normal rate = contract + 52-paid-week average of the variable elements; basic rate = contract, however
    the basic in the history moved (flag reference_week_basic_differs_from_contract when a reference week differs).
  * contract blank (T-137 rule, replaces the T-136 modal rule): rate inferred (flag rate_inferred_no_contract_basic) as the MOST
    RECENT basic > 0 among non-statutory (no SSP/SMP) weeks in the 8 calendar weeks before the leave week; if those 8 weeks hold no
    such basic, the latest NON-statutory basic > 0 anywhere before the leave week, then any basic > 0 (fallback). Flag rate_inferred_ambiguous when the 8-week window
    holds more than one distinct basic, or the fallback was used; flag no_basic_pay_found when the rate is 0 (no basic anywhere).
    A row with either of those two flags is ALWAYS an exception, even with difference 0 (direction "correct").
Part 2 rules (oracle): FORMAT.md "irregular_rolled_up" section, rolled-up pay = 12.07% x (basic + overtime + commission + allowance),
  rounded half-up to the penny once.
"""
import csv
import os
import random
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "audit.py")
CENT = Decimal("0.01")
NORMAL_CATS = ("basic", "regular_overtime", "commission", "allowance")
VARIABLE_CATS = ("regular_overtime", "commission", "allowance")
RU = "rolled_up_holiday_pay"
RATE = Fraction(1207, 10000)
ACCRUAL_START = date(2024, 4, 1)


def q(x):
    if isinstance(x, Fraction):
        n, d = x.numerator * 100, x.denominator
        return (Decimal((2 * n + d) // (2 * d)) / 100) if n >= 0 else -q(-x)
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def money(rng, lo, hi):
    return Decimal(rng.randint(int(lo * 100), int(hi * 100))) / 100


def leave_year_start(d, mmdd):
    m, dd = mmdd
    s = date(d.year, m, dd)
    return s if d >= s else date(d.year - 1, m, dd)


# ----------------------------------------------------------------------------- part 1 oracle
def window_weeks(pay, lw, n=104):
    return [(lw - timedelta(days=7 * k), pay.get(lw - timedelta(days=7 * k), {})) for k in range(1, n + 1)]


def inferred_basic(pay, lw):
    """Blank contract (T-137): (rate, ambiguous). Most recent basic>0 in the last 8 non-statutory weeks; else latest basic>0."""
    last8 = [p.get("basic", Decimal(0)) for _, p in window_weeks(pay, lw, 8)
             if p.get("basic", Decimal(0)) > 0 and p.get("statutory", Decimal(0)) <= 0]  # newest first
    if last8:
        return Fraction(last8[0]), len(set(last8)) > 1
    for stat_ok in (False, True):  # latest non-statutory basic first, then any basic
        for _, p in window_weeks(pay, lw, 104):
            if p.get("basic", Decimal(0)) > 0 and (stat_ok or p.get("statutory", Decimal(0)) <= 0):
                return Fraction(p["basic"]), True
    return Fraction(0), True  # no basic anywhere in the history: rate 0.00 and flag no_basic_pay_found


def oracle_fixed(wid, contract, mmdd, pay, leaves, threshold, details=None):
    """Return rows (wid, week, paid, due, diff, direction, n_used). details[(wid, week)] = (rate, set of flags)."""
    rows, cum = [], {}
    for lw, frac in leaves:
        ly = leave_year_start(lw, mmdd)
        before = cum.get(ly, Decimal(0))
        cum[ly] = before + frac
        normal_part = min(frac, max(Decimal(0), Decimal(4) - before))
        basic_part = frac - normal_part
        paid = pay.get(lw, {}).get("holiday_pay", Decimal(0))
        win = window_weeks(pay, lw)
        sums = [sum((p.get(c, Decimal(0)) for c in NORMAL_CATS), Decimal(0)) for _, p in win]
        if not any(s > 0 for s in sums):
            rows.append((wid, lw.isoformat(), q(paid), None, None, "cannot_check", 0))
            continue
        ambiguous = False
        if contract is not None:
            rate = Fraction(contract)
        else:
            rate, ambiguous = inferred_basic(pay, lw)
        var = [s - p.get("basic", Decimal(0)) for s, (_, p) in zip(sums, win) if s > 0][:52]
        avg_var = sum((Fraction(v) for v in var), Fraction(0)) / len(var)
        due = q((rate + avg_var) * Fraction(normal_part) + rate * Fraction(basic_part))
        diff = q(due - q(paid))
        if details is not None:
            flags = set()
            if contract is None:
                flags.add("rate_inferred_no_contract_basic")
            if ambiguous:
                flags.add("rate_inferred_ambiguous")
            if rate == 0:
                flags.add("no_basic_pay_found")
            used = [p.get("basic", Decimal(0)) for s, (_, p) in zip(sums, win) if s > 0][:52]
            if contract is not None and any(b > 0 and Fraction(b) != rate for b in used):
                flags.add("reference_week_basic_differs_from_contract")
            # the week immediately before the leave week, basic 0 when it has none (so a gap or a preceding leave week
            # raises the flag even though the rate is unchanged): probed, T136-F4
            latest = win[0][1].get("basic", Decimal(0))
            if Fraction(latest) != rate:
                flags.add("latest_week_basic_differs_from_rate_used")
            details[(wid, lw.isoformat())] = (q(rate), flags)
        if abs(diff) > threshold or ambiguous:  # an ambiguous / no-basic rate is always an exception
            rows.append((wid, lw.isoformat(), q(paid), due, diff,
                         "underpaid" if diff > 0 else "overpaid" if diff < 0 else "correct", len(var)))
    return rows


def gen_fixed(rng, wid, base, mode):
    """mode 'blank': contract cell blank, basic moves; 'given': contract supplied, history basic moves."""
    first = base + timedelta(days=7 * rng.randint(0, 10))
    n_hist = rng.choice([rng.randint(12, 51), rng.randint(52, 104), rng.randint(105, 130)])
    mmdd = rng.choice([(4, 1), (4, 1), (1, 1), (10, 1), (6, 1)])
    steps = sorted(rng.sample(range(1, n_hist), rng.randint(1, 3)))
    level = money(rng, 100, 500)
    levels, k = [], 0
    for i in range(n_hist):
        while k < len(steps) and i == steps[k]:
            level = max(Decimal("50"), level + money(rng, -80, 150))
            k += 1
        levels.append(level)
    contract = rng.choice([levels[0], levels[-1], money(rng, 100, 500)]) if mode == "given" else None
    pay, style = {}, rng.choice(["steady", "gappy", "recent_gap"])
    for i in range(n_hist):
        d = first + timedelta(days=7 * i)
        if style == "gappy" and rng.random() < 0.2:
            continue
        if style == "recent_gap" and i >= n_hist - rng.randint(0, 12) and rng.random() < 0.7:
            if rng.random() < 0.5:
                pay[d] = {"regular_overtime": money(rng, 5, 60)}  # overtime-only week, no basic
            continue
        r_stat = rng.random()
        if r_stat < 0.05:
            pay[d] = {"statutory": money(rng, 50, 120)}  # SSP/SMP only week: not a paid week, no basic
            continue
        rec = {"basic": levels[i]}
        if r_stat < 0.12:
            rec = {"basic": max(Decimal("10"), levels[i] / 2).quantize(CENT), "statutory": money(rng, 30, 100)}  # part-basic sick week
        for c in VARIABLE_CATS:
            if rng.random() < 0.3:
                rec[c] = money(rng, 1, 70)
        if rng.random() < 0.1:
            rec["bonus_non_regular"] = money(rng, 1, 200)
        if rng.random() < 0.15:
            rec[RU] = money(rng, 1, 30)  # rolled-up pay on a non-rolled-up worker never counts
        pay[d] = rec
    leave = set()
    for _ in range(rng.randint(1, 3)):
        s = first + timedelta(days=7 * rng.randint(2, n_hist + 20))
        for j in range(rng.choice([1, 1, 3, 6])):
            leave.add(s + timedelta(days=7 * j))
    leaves = [(d, rng.choice([Decimal(1), Decimal(1), Decimal("0.5")])) for d in sorted(leave)]
    return dict(type="fixed_pay", contract=contract, mmdd=mmdd, pay=pay, leaves=leaves, levels=levels, first=first)


def finish_paid(rng, wid, w):
    pay = w["pay"]
    for d, _ in w["leaves"]:
        pay.setdefault(d, {})["holiday_pay"] = Decimal(0)
    probe = oracle_fixed(wid, w["contract"], w["mmdd"], pay, w["leaves"], Decimal(-1))
    dues = {r[1]: r[3] for r in probe if r[3] is not None}
    for d, _ in w["leaves"]:
        due, r = dues.get(d.isoformat()), rng.random()
        if due is None or r < 0.2:
            amt = money(rng, 20, 500)
        elif r < 0.6:
            amt = due
        elif r < 0.75:
            amt = max(Decimal(0), due + Decimal(rng.choice([-2, -1, 1, 2])) / 100)
        else:
            amt = max(Decimal(0), due + money(rng, -40, 40))
        pay[d] = {"holiday_pay": q(amt)}  # leave weeks carry holiday_pay only


# ----------------------------------------------------------------------------- part 2 oracle
def oracle_rolled(wid, mmdd, pay, threshold):
    """Return (rows, checked_weeks). rows: (wid, week, paid, due|None, diff|None, direction, flag)."""
    rows, checked = [], set()
    for d in sorted(pay):
        p = pay[d]
        counts = sum((p.get(c, Decimal(0)) for c in NORMAL_CATS), Decimal(0))
        ru = p.get(RU)
        hp = p.get("holiday_pay", Decimal(0))
        accr = leave_year_start(d, mmdd) >= ACCRUAL_START
        if not accr:
            if ru is not None and ru > 0:
                rows.append((wid, d.isoformat(), q(ru), None, None, "rule_flag", "rolled_up_before_2024_rules"))
                checked.add(d)
        elif counts > 0 and ru is None:
            rows.append((wid, d.isoformat(), Decimal("0.00"), None, None, "rule_flag", "rolled_up_not_shown_separately"))
            checked.add(d)
        elif counts > 0 or ru is not None:
            checked.add(d)
            due = q(Fraction(counts) * RATE)
            diff = q(due - q(ru or Decimal(0)))
            if abs(diff) > threshold:
                rows.append((wid, d.isoformat(), q(ru or Decimal(0)), due, diff, "underpaid" if diff > 0 else "overpaid", ""))
        if hp > 0:
            checked.add(d)
            rows.append((wid, d.isoformat(), q(hp), None, None, "rule_flag", "holiday_pay_paid_to_rolled_up_worker"))
    return rows, checked


def gen_rolled(rng, wid, base):
    mmdd = rng.choice([(4, 1), (4, 1), (4, 1), (1, 1), (10, 1), (6, 1)])
    first = base + timedelta(days=7 * rng.randint(0, 12))
    n = rng.randint(1, 45)
    pay = {}
    for i in range(n):
        d = first + timedelta(days=7 * i)
        r = rng.random()
        if r < 0.1:
            continue
        rec = {}
        if r < 0.85:
            rec["basic"] = money(rng, 20, 400)
        for c in VARIABLE_CATS:
            if rng.random() < 0.25:
                rec[c] = money(rng, 1, 60)
        for c in ("bonus_non_regular", "expense_excluded", "statutory"):
            if rng.random() < 0.1:
                rec[c] = money(rng, 1, 150)
        counts = sum((rec.get(c, Decimal(0)) for c in NORMAL_CATS), Decimal(0))
        due = q(Fraction(counts) * RATE)
        r = rng.random()
        if r < 0.3:
            rec[RU] = due
        elif r < 0.45:
            rec[RU] = max(Decimal(0), due + Decimal(rng.choice([-1, 1])) / 100)
        elif r < 0.55:
            rec[RU] = max(Decimal(0), due + money(rng, -10, 10))
        elif r < 0.6:
            rec[RU] = Decimal(0)
        elif r < 0.65:
            rec[RU] = money(rng, 0, 20)
        # else: no rolled-up row
        if rng.random() < 0.06:
            rec["holiday_pay"] = money(rng, 10, 200)
        if rec:
            pay[d] = rec
    return dict(type="irregular_rolled_up", mmdd=mmdd, pay=pay, first=first)


# ----------------------------------------------------------------------------- IO
def write_inputs(tmp, workers, leave_rows):
    """workers: [(wid, type, mmdd, contract_cell, pay)]; leave_rows: [(wid, date, weeks_str)]; weeks column only if any."""
    with open(os.path.join(tmp, "history.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["worker_id", "week_ending", "element_category", "amount"])
        for wid, _, _, _, pay in workers:
            for d in sorted(pay):
                for c, a in sorted(pay[d].items()):
                    w.writerow([wid, d.isoformat(), c, f"{a:.2f}"])
    with open(os.path.join(tmp, "leave.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["worker_id", "week_ending", "weeks"])
        for wid, d, f in leave_rows:
            w.writerow([wid, d.isoformat(), f])
    with open(os.path.join(tmp, "workers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["worker_id", "worker_type", "leave_year_start", "contract_weekly_basic"])
        for wid, t, mmdd, cell, _ in workers:
            w.writerow([wid, t, "%02d-%02d" % mmdd, cell])


def run_cli(tmp, threshold):
    out = os.path.join(tmp, "out")
    p = subprocess.run([sys.executable, "-I", AUDIT, "--history", os.path.join(tmp, "history.csv"),
                        "--leave", os.path.join(tmp, "leave.csv"), "--workers", os.path.join(tmp, "workers.csv"),
                        "--out", out, "--threshold", str(threshold)], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError("CLI exit %s\n%s\n%s" % (p.returncode, p.stdout, p.stderr))
    with open(os.path.join(out, "exceptions.csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh)), p.stdout, p.stderr


def cli_lookback(rows):
    res = []
    for r in rows:
        if r["check"] != "leave_lookback":
            continue
        if r["direction"] == "cannot_check":
            res.append((r["worker_id"], r["leave_week"], Decimal(r["paid"]), None, None, "cannot_check", 0))
        else:
            res.append((r["worker_id"], r["leave_week"], Decimal(r["paid"]), Decimal(r["due"]), Decimal(r["difference"]),
                        r["direction"], int(r["ref_weeks_used"])))
    return sorted(res, key=lambda t: (t[0], t[1]))


def cli_rolled(rows):
    res = []
    for r in rows:
        if r["check"] != "rolled_up_pay":
            continue
        res.append((r["worker_id"], r["leave_week"], Decimal(r["paid"]),
                    Decimal(r["due"]) if r["due"] else None, Decimal(r["difference"]) if r["difference"] else None,
                    r["direction"], r["flags"]))
    return sorted(res, key=lambda t: (t[0], t[1], t[6]))


# ----------------------------------------------------------------------------- cases
def fixed_case(seed):
    rng = random.Random(seed)
    base = date(2022, 1, 1) + timedelta(days=7 * rng.randint(0, 40) + rng.randint(0, 6))
    threshold = rng.choice([Decimal("0.00"), Decimal("0.00"), Decimal("0.01"), Decimal("1.00")])
    workers, leave_rows, expected, kinds, details = [], [], [], {}, {}
    for i in range(rng.randint(1, 2)):
        wid = "EMP%03d%d" % (seed % 1000, i)
        mode = rng.choice(["blank", "given", "given"])
        w = gen_fixed(rng, wid, base, mode)
        finish_paid(rng, wid, w)
        cell = "" if w["contract"] is None else f"{w['contract']:.2f}"
        workers.append((wid, "fixed_pay", w["mmdd"], cell, w["pay"]))
        leave_rows += [(wid, d, f"{f}") for d, f in w["leaves"]]
        expected += oracle_fixed(wid, w["contract"], w["mmdd"], w["pay"], w["leaves"], threshold, details)
        kinds[wid] = mode
    expected.sort(key=lambda t: (t[0], t[1]))
    with tempfile.TemporaryDirectory() as tmp:
        write_inputs(tmp, workers, leave_rows)
        rows, _, _ = run_cli(tmp, threshold)
    return expected, cli_lookback(rows), kinds, details, rows


def rolled_case(seed):
    rng = random.Random(seed)
    base = date(2023, 6, 3) + timedelta(days=7 * rng.randint(0, 40) + rng.randint(0, 6))
    threshold = rng.choice([Decimal("0.00"), Decimal("0.00"), Decimal("0.01"), Decimal("1.00")])
    workers, leave_rows, expected, checked, flagged_exc = [], [], [], 0, 0
    other = rng.random() < 0.5  # a variable_hours worker alongside, with its own look-back
    n_ru = rng.randint(1, 3)
    for i in range(n_ru):
        wid = "RU%03d%d" % (seed % 1000, i)
        w = gen_rolled(rng, wid, base)
        # nudge one boundary: put the leave-year start exactly on a pay week sometimes
        if w["pay"] and rng.random() < 0.3:
            d = rng.choice(sorted(w["pay"]))
            if not (d.month == 2 and d.day == 29):
                w["mmdd"] = (d.month, d.day)
        rows, chk = oracle_rolled(wid, w["mmdd"], w["pay"], threshold)
        expected += rows
        checked += len(chk)
        cell = rng.choice(["", "", "250.00", "0"])  # ignored for rolled-up workers
        workers.append((wid, "irregular_rolled_up", w["mmdd"], cell, w["pay"]))
        # leave weeks of a rolled-up worker are not re-audited, with or without history rows
        for d in rng.sample(sorted(w["pay"]) or [base], min(2, max(1, len(w["pay"])))) if rng.random() < 0.5 else []:
            leave_rows.append((wid, d, "1"))
    if other:
        wid = "VH%03d" % (seed % 1000)
        pay = {}
        for k in range(30):
            d = base + timedelta(days=7 * k)
            pay[d] = {"basic": money(rng, 100, 300), RU: money(rng, 1, 40)}
        ld = base + timedelta(days=7 * 31)
        pay[ld] = {"holiday_pay": money(rng, 100, 300)}
        workers.append((wid, "variable_hours", (4, 1), rng.choice(["", "300.00"]), pay))
        leave_rows.append((wid, ld, "1"))
    expected.sort(key=lambda t: (t[0], t[1], t[6]))
    with tempfile.TemporaryDirectory() as tmp:
        write_inputs(tmp, workers, leave_rows)
        rows, stdout, stderr = run_cli(tmp, threshold)
    return expected, cli_rolled(rows), checked, stdout, rows, workers, bool(other)


class FixedPayChangingBasic(unittest.TestCase):
    N = 55

    def test_random_cases_match_oracle(self):
        bad, n_rows, by_mode = [], 0, {"blank": 0, "given": 0}
        for seed in range(self.N):
            expected, got, kinds, _, _ = fixed_case(seed)
            n_rows += len(expected)
            for m in kinds.values():
                by_mode[m] += 1
            if expected != got:
                bad.append((seed, expected, got))
        self.assertGreater(n_rows, 60)
        self.assertGreater(min(by_mode.values()), 10)
        if bad:
            seed, e, g = bad[0]
            self.fail("%d of %d cases disagree; first seed %d\nexpected-only: %s\ncli-only: %s"
                      % (len(bad), self.N, seed, [x for x in e if x not in g][:3], [x for x in g if x not in e][:3]))


    def test_rate_used_and_flags_match_oracle(self):
        """fixed_basic_rate column and the rate/flag columns of every look-back exception row."""
        bad, n = [], 0
        for seed in range(self.N):
            expected, got, kinds, details, rows = fixed_case(seed)
            for r in rows:
                if r["check"] != "leave_lookback" or r["direction"] == "cannot_check":
                    continue
                n += 1
                rate, flags = details[(r["worker_id"], r["leave_week"])]
                have = set(f for f in r["flags"].split(";") if f.startswith(("rate_", "reference_", "latest_", "no_basic")))
                if Decimal(r["fixed_basic_rate"]) != rate or have != flags:
                    bad.append((seed, r["worker_id"], r["leave_week"], r["fixed_basic_rate"], str(rate), sorted(have), sorted(flags)))
        self.assertGreater(n, 60)
        self.assertFalse(bad, "%d rows disagree, first: %s" % (len(bad), bad[:2]))  # noqa


class HandComputed(unittest.TestCase):
    """Hand-worked cases for the findings in reviews/T-136-qa.md (expected values computed on paper)."""

    def run_one(self, pay, leave, wtype, cell, paid="1.00", all_rows=False):
        wk0 = date(2025, 1, 4)
        hist = {wk0 + timedelta(days=7 * i): v for i, v in pay.items()}
        ld = wk0 + timedelta(days=7 * leave)
        hist.setdefault(ld, {})["holiday_pay"] = Decimal(paid)
        with tempfile.TemporaryDirectory() as tmp:
            write_inputs(tmp, [("A1", wtype, (4, 1), cell, hist)], [("A1", ld, "1")])
            rows, _, _ = run_cli(tmp, Decimal("0"))
        return rows if all_rows else rows[0]

    def test_f1_one_contract_rate_for_the_whole_history(self):
        # contract 200, but the basic paid was 100 until a rise at week 10; leave in week 10 (before the rise, paid 100 + 1.00 pay)
        pay = {i: {"basic": Decimal(100)} for i in range(10)}
        r = self.run_one(pay, 10, "fixed_pay", "200.00")
        self.assertEqual((r["due"], r["difference"], r["fixed_basic_rate"]), ("200.00", "199.00", "200.00"))
        self.assertIn("reference_week_basic_differs_from_contract", r["flags"])  # the only warning that the rate moved

    def test_f2_rise_three_weeks_before_leave_uses_new_rate_and_flags(self):
        # T-137: blank contract, rate = most recent basic in the last 8 weeks, flagged ambiguous (was: old modal rate 100.00)
        pay = {i: {"basic": Decimal(100 if i < 17 else 200)} for i in range(20)}
        r = self.run_one(pay, 20, "fixed_pay", "")
        self.assertEqual((r["due"], r["fixed_basic_rate"]), ("200.00", "200.00"))
        self.assertIn("rate_inferred_ambiguous", r["flags"])
        pay = {i: {"basic": Decimal(100 if i < 16 else 200)} for i in range(20)}  # 4 old, 4 new in the last 8
        self.assertEqual(self.run_one(pay, 20, "fixed_pay", "")["due"], "200.00")

    def test_f2_zero_difference_after_rise_is_still_an_exception(self):
        pay = {i: {"basic": Decimal(100 if i < 17 else 200)} for i in range(20)}
        rows = self.run_one(pay, 20, "fixed_pay", "", paid="200.00", all_rows=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["difference"], rows[0]["direction"]), ("0.00", "correct"))
        self.assertIn("rate_inferred_ambiguous", rows[0]["flags"])
        # an employer who paid the old rate is underpaid by the rise, not hidden
        r = self.run_one(pay, 20, "fixed_pay", "", paid="100.00")
        self.assertEqual((r["difference"], r["direction"]), ("100.00", "underpaid"))

    def test_report_md_explains_zero_difference_guessed_rate(self):
        pay = {i: {"basic": Decimal(100 if i < 17 else 200)} for i in range(20)}
        wk0 = date(2025, 1, 4)
        hist = {wk0 + timedelta(days=7 * i): v for i, v in pay.items()}
        ld = wk0 + timedelta(days=140)
        hist[ld] = {"holiday_pay": Decimal("200.00")}
        with tempfile.TemporaryDirectory() as tmp:
            write_inputs(tmp, [("A1", "fixed_pay", (4, 1), "", hist)], [("A1", ld, "1")])
            run_cli(tmp, Decimal("0.01"))
            with open(os.path.join(tmp, "out", "report.md"), encoding="utf-8") as fh:
                md = fh.read()
        for text in ("or weekly rate guessed): 1", "Leave weeks with a guessed weekly rate: 1",
                     "Listed although the difference is £0.00"):
            self.assertIn(text, md)

    def test_f3_partial_latest_week_is_flagged_even_when_paid_equals_due(self):
        pay = {i: {"basic": Decimal(100 if i < 19 else 40)} for i in range(20)}
        rows = self.run_one(pay, 20, "fixed_pay", "", paid="40.00", all_rows=True)
        self.assertEqual((rows[0]["due"], rows[0]["difference"]), ("40.00", "0.00"))
        self.assertIn("rate_inferred_ambiguous", rows[0]["flags"])

    def test_contract_given_has_no_new_flags_and_no_forced_exception(self):
        pay = {i: {"basic": Decimal(100 if i < 17 else 200)} for i in range(20)}
        self.assertEqual(self.run_one(pay, 20, "fixed_pay", "200.00", paid="200.00", all_rows=True), [])
        r = self.run_one(pay, 20, "fixed_pay", "200.00")
        self.assertNotIn("rate_inferred_ambiguous", r["flags"])
        self.assertNotIn("no_basic_pay_found", r["flags"])

    def test_f5_blank_contract_and_no_basic_anywhere_is_flagged(self):
        pay = {i: {"regular_overtime": Decimal(30)} for i in range(6)}
        r = self.run_one(pay, 6, "fixed_pay", "")
        self.assertEqual((r["due"], r["fixed_basic_rate"], r["direction"]), ("30.00", "0.00", "underpaid"))  # paid 1.00 by the helper
        self.assertIn("no_basic_pay_found", r["flags"])
        rows = self.run_one(pay, 6, "fixed_pay", "", paid="30.00", all_rows=True)  # still an exception at difference 0
        self.assertEqual(len(rows), 1)
        self.assertIn("no_basic_pay_found", rows[0]["flags"])


class RolledUpOracle(unittest.TestCase):
    N = 60

    def test_random_cases_match_oracle(self):
        bad, n_rows, flags = [], 0, set()
        for seed in range(1000, 1000 + self.N):
            expected, got, checked, stdout, rows, workers, other = rolled_case(seed)
            n_rows += len(expected)
            flags |= {r[6] for r in expected} | {r[5] for r in expected}
            lb_rolled = [r for r in rows if r["check"] == "leave_lookback" and r["worker_id"].startswith("RU")]
            if expected != got or lb_rolled:
                bad.append((seed, expected, got))
        self.assertGreater(n_rows, 150)
        for f in ("rolled_up_before_2024_rules", "rolled_up_not_shown_separately", "holiday_pay_paid_to_rolled_up_worker",
                  "underpaid", "overpaid"):
            self.assertIn(f, flags)
        if bad:
            seed, e, g = bad[0]
            self.fail("%d of %d cases disagree; first seed %d\nexpected-only: %s\ncli-only: %s"
                      % (len(bad), self.N, seed, [x for x in e if x not in g][:3], [x for x in g if x not in e][:3]))

    def test_stdout_counts_match_oracle(self):
        bad = []
        for seed in range(1000, 1030):
            expected, got, checked, stdout, rows, workers, other = rolled_case(seed)
            want = "%d rolled-up pay weeks checked, %d exceptions." % (checked, len(expected))
            if checked and want not in stdout.splitlines():
                bad.append((seed, want, stdout))
        self.assertFalse(bad, bad[:1])


if __name__ == "__main__":
    unittest.main()
