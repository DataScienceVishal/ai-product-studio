"""Randomised differential test of the look-back audit (T-135).

The oracle below was written from the documented rules only (README, BRIEF, ingest/FORMAT.md,
samples/generate.py, benchmark/examples/SOURCES.md, gov.uk guidance), never from the engine source.
The CLI is run as a black box on seeded random inputs and its exceptions.csv rows are compared
with the oracle's to the penny.

Rules encoded in the oracle (see reviews/T-135-qa.md for which ones were learned by probing the CLI):
  * leave year starts on the worker's MM-DD (default 04-01); a week ending on the start date belongs to the new year.
  * leave rows are taken in date order; the leave-week count in the year accumulates `weeks` (default 1).
    The first 4.0 leave weeks are "normal pay", the rest "basic only"; a row that straddles 4.0 is split pro rata.
  * reference period: the 104 weeks before the leave week; the most recent 52 paid weeks inside it; no-pay weeks skipped.
  * normal pay (variable_hours): average over paid weeks of basic + regular_overtime + commission + allowance
    (bonus_non_regular, expense_excluded, statutory, holiday_pay, rolled_up never count).
  * basic only (variable_hours): average basic over the most recent 52 weeks that have basic pay > 0 (probed, DOC AMBIGUITY).
  * fixed_pay: contract basic + 52-paid-week average of the variable elements (normal part); contract basic (basic part).
  * due = amount * leave-weeks fraction; an exception is a |paid - due| > threshold (2dp, half-up).
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
NON_COUNTING = ("bonus_non_regular", "expense_excluded", "statutory")


def q(x):
    """Round half-up to the penny; exact for Fraction and Decimal inputs."""
    if isinstance(x, Fraction):
        n, d = x.numerator * 100, x.denominator
        return (Decimal((2 * n + d) // (2 * d)) / 100) if n >= 0 else -q(-x)
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------------- oracle
def leave_year_of(d, mmdd):
    m, dd = mmdd
    start = date(d.year, m, dd)
    return start.year if d >= start else start.year - 1


def window_weeks(pay, leave_week):
    """(week, {cat: amount}) for the 104 weeks before leave_week, newest first."""
    out = []
    for k in range(1, 105):
        w = leave_week - timedelta(days=7 * k)
        out.append((w, pay.get(w, {})))
    return out


def avg_of_most_recent(values):
    """values newest first, only paid weeks; returns (average rounded half-up, n) or None."""
    vals = values[:52]
    if not vals:
        return None
    return sum((Fraction(v) for v in vals), Fraction(0)) / len(vals), len(vals)


def oracle_worker(wid, wtype, contract, mmdd, pay, leaves, threshold):
    """pay: {date: {cat: Decimal}}; leaves: [(date, Decimal fraction)] sorted. Returns exception tuples."""
    rows = []
    cum = {}
    for lw, frac in leaves:
        ly = leave_year_of(lw, mmdd)
        before = cum.get(ly, Decimal(0))
        cum[ly] = before + frac
        normal_part = min(frac, max(Decimal(0), Decimal(4) - before))
        basic_part = frac - normal_part
        paid = pay.get(lw, {}).get("holiday_pay", Decimal(0))
        win = window_weeks(pay, lw)
        normal_sums = [sum((p.get(c, Decimal(0)) for c in NORMAL_CATS), Decimal(0)) for _, p in win]
        normal_paid = [s for s in normal_sums if s > 0]
        if not normal_paid:
            rows.append((wid, lw.isoformat(), q(paid), None, None, "cannot_check", 0))
            continue
        if wtype == "fixed_pay":
            var = [s - p.get("basic", Decimal(0)) for s, (_, p) in zip(normal_sums, win) if s > 0]
            avg_var, n = avg_of_most_recent(var)
            normal_rate = Fraction(contract) + avg_var
            basic_rate = Fraction(contract)
        else:
            normal_rate, n = avg_of_most_recent(normal_paid)
            basics = [p.get("basic", Decimal(0)) for _, p in win if p.get("basic", Decimal(0)) > 0]
            basic_rate = avg_of_most_recent(basics)[0] if basics else Fraction(0)
        due = q(normal_rate * Fraction(normal_part) + basic_rate * Fraction(basic_part))
        diff = q(due - q(paid))
        if abs(diff) > threshold:
            rows.append((wid, lw.isoformat(), q(paid), due, diff, "underpaid" if diff > 0 else "overpaid", n))
    return rows


# ----------------------------------------------------------------------------- case generation
def money(rng, lo, hi):
    return Decimal(rng.randint(int(lo * 100), int(hi * 100))) / 100


def gen_worker(rng, wid, base, case_kind):
    """returns dict(type, contract, mmdd, pay, leaves, weekday_start)"""
    wtype = rng.choice(["variable_hours", "variable_hours", "fixed_pay"])
    mmdd = rng.choice([(4, 1), (4, 1), (1, 1), (10, 1), (2, 15), (12, 31), (6, 1)])
    n_hist = {"short": rng.randint(1, 51), "normal": rng.randint(40, 70), "long": rng.randint(105, 140),
              "mid": rng.randint(52, 104)}[case_kind]
    first = base + timedelta(days=7 * rng.randint(0, 20))
    contract = money(rng, 100, 600) if wtype == "fixed_pay" else None
    style = rng.choice(["steady", "noisy", "gappy", "sparse"])
    pay = {}
    for i in range(n_hist):
        d = first + timedelta(days=7 * i)
        r = rng.random()
        if style == "gappy" and r < 0.25:
            continue
        if style == "sparse" and r < 0.5:
            continue
        if r > 0.95:  # statutory only
            pay[d] = {"statutory": money(rng, 50, 120)}
            continue
        if r > 0.92:  # bonus only
            pay[d] = {"bonus_non_regular": money(rng, 10, 300)}
            continue
        if r > 0.9:  # overtime only
            pay[d] = {"regular_overtime": money(rng, 5, 90)}
            continue
        rec = {}
        if wtype == "fixed_pay":
            rec["basic"] = contract
        else:
            rec["basic"] = money(rng, 80, 500) if style != "steady" else Decimal(250)
        for c in VARIABLE_CATS:
            if rng.random() < 0.35:
                rec[c] = money(rng, 1, 80)
        for c in ("bonus_non_regular", "expense_excluded"):
            if rng.random() < 0.08:
                rec[c] = money(rng, 1, 200)
        pay[d] = rec
    # leave weeks: after some history, some scattered, some in runs, over one or several leave years
    leave_dates = set()
    last = first + timedelta(days=7 * n_hist)
    for _ in range(rng.randint(1, 4)):
        start = first + timedelta(days=7 * rng.randint(1, n_hist + 60))
        for j in range(rng.choice([1, 1, 2, 5, 7])):
            leave_dates.add(start + timedelta(days=7 * j))
    if rng.random() < 0.4:  # a second leave year
        start = last + timedelta(days=7 * rng.randint(30, 60))
        for j in range(rng.choice([1, 3, 6])):
            leave_dates.add(start + timedelta(days=7 * j))
    leaves = []
    for d in sorted(leave_dates):
        frac = rng.choice(["1", "1", "1", "0.5", "0.5", "0.25", "0.75", "0.1", "0.33", ""])
        leaves.append((d, frac))
    blank = wtype == "fixed_pay" and rng.random() < 0.25  # contract cell left blank: rate inferred (constant basic)
    return dict(blank=blank, type=wtype, contract=contract, mmdd=mmdd, pay=pay, leaves=leaves, first=first)


def finish_paid(rng, wid, w, threshold):
    """Insert holiday_pay rows using the oracle's due (so exact, near and wrong payments all occur)."""
    pay = w["pay"]
    fr = [(d, Decimal(f or "1")) for d, f in w["leaves"]]
    # holiday_pay rows go in a leave week; the oracle ignores holiday_pay in reference weeks
    for d, _ in fr:
        pay.setdefault(d, {})["holiday_pay"] = Decimal(0)
    probe = oracle_worker(wid, w["type"], w["contract"], w["mmdd"], pay, fr, Decimal(-1))
    dues = {r[1]: r[3] for r in probe if r[3] is not None}
    for d, _ in fr:
        due = dues.get(d.isoformat())
        r = rng.random()
        if due is None or r < 0.3:
            amount = money(rng, 20, 500)
        elif r < 0.6:
            amount = due
        elif r < 0.75:
            amount = max(Decimal(0), due + Decimal(rng.choice([-2, -1, 1, 2])) / 100)
        else:
            amount = max(Decimal(0), due + money(rng, -40, 40))
        pay[d] = {"holiday_pay": q(amount)}  # leave weeks carry holiday_pay only
    return fr


def write_inputs(tmp, workers, with_weeks_col):
    with open(os.path.join(tmp, "history.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["worker_id", "week_ending", "element_category", "amount"])
        for wid, wk in workers:
            for d in sorted(wk["pay"]):
                for c, a in sorted(wk["pay"][d].items()):
                    w.writerow([wid, d.isoformat(), c, f"{a:.2f}"])
    with open(os.path.join(tmp, "leave.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["worker_id", "week_ending"] + (["weeks"] if with_weeks_col else []))
        for wid, wk in workers:
            for d, f in wk["leaves"]:
                w.writerow([wid, d.isoformat()] + ([f or "1"] if with_weeks_col else []))
    with open(os.path.join(tmp, "workers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["worker_id", "worker_type", "leave_year_start", "contract_weekly_basic"])
        for wid, wk in workers:
            w.writerow([wid, wk["type"], "%02d-%02d" % wk["mmdd"], wk["contract"] if wk["contract"] is not None and not wk["blank"] else ""])


def run_cli(tmp, threshold):
    out = os.path.join(tmp, "out")
    p = subprocess.run([sys.executable, "-I", AUDIT, "--history", os.path.join(tmp, "history.csv"),
                        "--leave", os.path.join(tmp, "leave.csv"), "--workers", os.path.join(tmp, "workers.csv"),
                        "--out", out, "--threshold", str(threshold)], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError("CLI exit %s\n%s\n%s" % (p.returncode, p.stdout, p.stderr))
    with open(os.path.join(out, "exceptions.csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cli_rows(rows):
    res = []
    for r in rows:
        if r["check"] != "leave_lookback":
            continue
        if r["direction"] == "cannot_check":
            # due/difference of a cannot_check row are not comparable (see reviews/T-135-qa.md, F-1)
            res.append((r["worker_id"], r["leave_week"], Decimal(r["paid"]), None, None, "cannot_check", 0))
            continue
        res.append((r["worker_id"], r["leave_week"], Decimal(r["paid"]), Decimal(r["due"]),
                    Decimal(r["difference"]), r["direction"], int(r["ref_weeks_used"])))
    return sorted(res, key=lambda t: (t[0], t[1]))


LAST_TYPES = {}


def run_case(seed):
    rng = random.Random(seed)
    base = date(2022, 1, 1) + timedelta(days=7 * rng.randint(0, 60) + rng.randint(0, 6))  # any weekday
    kinds = ["short", "normal", "long", "mid"]
    threshold = rng.choice([Decimal("0.00"), Decimal("0.00"), Decimal("0.01"), Decimal("0.50"), Decimal("5.00")])
    workers = []
    for i in range(rng.randint(1, 3)):
        wid = "EMP%03d%d" % (seed % 1000, i)
        w = gen_worker(rng, wid, base, rng.choice(kinds))
        fr = finish_paid(rng, wid, w, threshold)
        workers.append((wid, w))
    with_weeks = any(f for _, w in workers for _, f in w["leaves"]) or rng.random() < 0.5
    expected = []
    for wid, w in workers:
        fr = [(d, Decimal(f or "1")) for d, f in w["leaves"]]
        expected += oracle_worker(wid, w["type"], w["contract"], w["mmdd"], w["pay"], fr, threshold)
    expected.sort(key=lambda t: (t[0], t[1]))
    LAST_TYPES.update({wid: w["type"] for wid, w in workers})
    with tempfile.TemporaryDirectory() as tmp:
        write_inputs(tmp, workers, with_weeks)
        got = cli_rows(run_cli(tmp, threshold))
    return expected, got


class DifferentialLookback(unittest.TestCase):
    N = 330

    def test_random_cases_match_oracle(self):
        bad = []
        n_rows = 0
        for seed in range(self.N):
            expected, got = run_case(seed)
            n_rows += len(expected)
            if expected != got:
                bad.append((seed, expected, got))
        self.assertGreater(n_rows, 300, "generator produced too few exceptions to be meaningful")
        if bad:
            seed, e, g = bad[0]
            self.fail("%d of %d cases disagree; first seed %d\nexpected-only: %s\ncli-only: %s"
                      % (len(bad), self.N, seed, [x for x in e if x not in g][:3], [x for x in g if x not in e][:3]))


class SampleHandComputed(unittest.TestCase):
    """The oracle's own sanity check: samples/generate.py documents these four look-back results by hand."""

    def test_sample_rows(self):
        s = os.path.join(ROOT, "samples")
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run([sys.executable, "-I", AUDIT, "--history", os.path.join(s, "history.csv"),
                                "--leave", os.path.join(s, "leave.csv"), "--workers", os.path.join(s, "workers.csv"),
                                "--out", os.path.join(tmp, "out")], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr)
            with open(os.path.join(tmp, "out", "exceptions.csv"), newline="", encoding="utf-8") as fh:
                rows = [r for r in csv.DictReader(fh) if r["check"] == "leave_lookback"]
        self.assertEqual([(r["worker_id"], r["difference"]) for r in rows],
                         [("W002", "80.00"), ("W003", "-10.00"), ("W004", "50.00"), ("W005", "15.00")])


if __name__ == "__main__":
    unittest.main()
