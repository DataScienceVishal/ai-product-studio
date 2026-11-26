import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal as D

import audit as cli
from ingest import load_workers, ValidationError
from samples import generate

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(HERE, "samples")
H = "worker_id,week_ending,element_category,amount\n"
L = "worker_id,week_ending\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        p = os.path.join(self.tmp.name, name)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return p

    def issues(self, history, leave=L + "W1,2025-06-14\n", workers=None):
        h, l = self.write("h.csv", history), self.write("l.csv", leave)
        w = self.write("w.csv", workers) if workers is not None else None
        with self.assertRaises(ValidationError) as cm:
            load_workers(h, l, w)
        return [str(i) for i in cm.exception.issues]

    def has(self, issues, *words):
        self.assertTrue(any(all(w in i for w in words) for i in issues), (words, issues))


class Validation(Base):
    def test_valid_minimal(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100.00\nW1,2025-06-14,holiday_pay,100\n")
        w = load_workers(h, self.write("l.csv", L + "W1,2025-06-14\n"))
        self.assertEqual(w["W1"].history[next(iter(w["W1"].history))], {"basic": D("100.00")})
        self.assertEqual(len(w["W1"].leave), 1)

    def test_collects_all_errors_with_line_numbers(self):
        iss = self.issues(H + "W1,2025-13-01,basic,1\nW1,2025-06-07,bogus,1\nW1,2025-06-07,basic,abc\n"
                          "W1,2025-06-07,basic,NaN\nW1,2025-06-07,basic,Infinity\nW1,2025-06-07,basic,-5\n")
        for line in range(2, 8):
            self.has(iss, f"h.csv:{line}:")
        self.has(iss, "valid YYYY-MM-DD"); self.has(iss, "unknown element_category 'bo...' (5 chars)")
        self.has(iss, "NaN"); self.has(iss, "Infinity")

    def test_missing_and_extra_columns(self):
        iss = self.issues("worker_id,week_ending,amount,colour\nW1,2025-06-07,1,red\n")
        self.has(iss, "h.csv:1", "missing column 'element_category'")
        self.has(iss, "unexpected column 'colour'")

    def test_bad_field_count(self):
        self.has(self.issues(H + "W1,2025-06-07,basic\n"), "h.csv:2", "expected 4 fields")

    def test_duplicates(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\nW1,2025-06-07,basic,2\nW1,2025-06-14,basic,1\n",
                          leave=L + "W1,2025-06-14\nW1,2025-06-14\n")
        self.has(iss, "h.csv:3", "duplicate row", "line 2")
        self.has(iss, "l.csv:3", "duplicate leave week")

    def test_week_pattern_alignment(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\nW1,2025-06-14,basic,1\nW1,2025-06-21,basic,1\nW1,2025-06-25,basic,1\n",
                          leave=L + "W1,2025-06-18\n")
        self.has(iss, "h.csv:5", "Wednesday", "Saturday")
        self.has(iss, "l.csv:2", "Wednesday")

    def test_empty_files(self):
        h, l = self.write("h.csv", ""), self.write("l.csv", L)
        with self.assertRaises(ValidationError) as cm:
            load_workers(h, l)
        msgs = [str(i) for i in cm.exception.issues]
        self.has(msgs, "h.csv: file is empty"); self.has(msgs, "l.csv: no data rows")

    def test_personal_data_header_refused(self):
        for col in ("name", "ni_number", "Employee Name", "email"):
            iss = self.issues(f"worker_id,{col},week_ending,element_category,amount\nW1,x,2025-06-07,basic,1\n")
            self.has(iss, "personal data")

    def test_ni_number_in_worker_id_refused(self):
        iss = self.issues(H + "QQ123456C,2025-06-07,basic,1\nqq 12 34 56 c,2025-06-07,basic,1\n", leave=L + "QQ123456C,2025-06-14\n")
        self.has(iss, "h.csv:2", "National Insurance"); self.has(iss, "h.csv:3", "National Insurance")
        self.has(iss, "l.csv:2", "National Insurance")

    def test_leave_and_worker_settings_errors(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\n", leave=L.strip() + ",weeks\nW9,2025-06-07,1\nW1,2025-06-07,0\n",
                          workers="worker_id,worker_type\nW1,magic\nW1,fixed_pay\nW8,fixed_pay\n")
        self.has(iss, "l.csv:2", "no payroll history"); self.has(iss, "l.csv:3", "greater than 0")
        self.has(iss, "w.csv:2", "worker_type 'ma...' (5 chars)"); self.has(iss, "w.csv:3", "duplicate settings")
        self.has(iss, "w.csv:4", "no payroll history")


class Hardening(Base):
    def test_duplicate_column(self):
        self.has(self.issues("worker_id,week_ending,amount,element_category,amount\nW1,2025-06-07,1,basic,1\n"),
                 "h.csv:1", "duplicate column 'amount'")

    def test_bad_contract_basic(self):
        for bad in ("abc", "-1"):
            self.has(self.issues(H + "W1,2025-06-07,basic,1\n", workers=f"worker_id,worker_type,contract_weekly_basic\nW1,fixed_pay,{bad}\n"),
                     "w.csv:2", "contract_weekly_basic")

    def test_too_many_fields(self):
        self.has(self.issues(H + "W1,2025-06-07,basic,1,extra\n"), "h.csv:2", "expected 4 fields, found 5")

    def test_leave_weeks_above_one_rejected(self):
        iss = self.issues(H + "W1,2025-06-07,basic,100\n", leave="worker_id,week_ending,weeks\nW1,2025-06-07,50\nW1,2025-06-14,1.5\n")
        self.has(iss, "l.csv:2", "at most 1"); self.has(iss, "l.csv:3", "at most 1")

    def test_worker_id_allowlist(self):
        for bad in ('=HYPERLINK("x")', "a@b.com", "<script>", "-1", "bob smith"):
            self.has(self.issues(H + f'"{bad.replace(chr(34), chr(34)*2)}",2025-06-07,basic,1\n'), "h.csv:2", "worker_id must be")

    def test_output_escaping(self):
        from report.builder import _safe, _md
        self.assertEqual([_safe(c) for c in ("=1", "+1", "-1", "@x", "\tx", "\rx", "ok")],
                         ["'=1", "'+1", "'-1", "'@x", "'\tx", "'\rx", "ok"])
        self.assertEqual(_md("a_b*c#"), "a\\_b\\*c\\#")

    def test_no_tracebacks_on_hostile_numbers(self):
        for amt in ("1" * 40, "\u0661\u0660\u0660", "1e5", '"1,000"', "1.123"):
            self.has(self.issues(H + f"W1,2025-06-07,basic,{amt}\n"), "h.csv:2", "amount")

    def test_oversized_field_is_a_row_error(self):
        import csv as _csv
        old = _csv.field_size_limit(1000)
        self.addCleanup(_csv.field_size_limit, old)
        self.has(self.issues(H + "W1,2025-06-07,basic," + "9" * 2000 + "\n"), "h.csv:", "malformed CSV")


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(args))
    return code, err.getvalue()


class EndToEnd(Base):
    def audit(self, *extra):
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv",
                            "--workers", f"{SAMPLES}/workers.csv", "--out", out, *extra)
        self.assertEqual((code, err), (0, ""))
        with open(f"{out}/exceptions.csv", newline="") as fh:
            return out, list(csv.DictReader(fh))

    def test_sample_files_match_generator(self):
        generate.write(os.path.join(self.tmp.name, "gen"))
        for n in ("history.csv", "leave.csv", "workers.csv"):
            with open(f"{SAMPLES}/{n}") as a, open(f"{self.tmp.name}/gen/{n}") as b:
                self.assertEqual(a.read(), b.read(), n)

    def test_known_underpayments_and_totals(self):
        out, rows = self.audit()
        rows = [r for r in rows if r["check"] == "leave_lookback"]
        by = {r["worker_id"]: r for r in rows}
        self.assertEqual({k: (v["paid"], v["due"], v["difference"], v["direction"]) for k, v in by.items()}, {
            "W002": ("400.00", "480.00", "80.00", "underpaid"),
            "W003": ("310.00", "300.00", "-10.00", "overpaid"),
            "W004": ("350.00", "400.00", "50.00", "underpaid"),
            "W005": ("300.00", "315.00", "15.00", "underpaid")})
        self.assertEqual(by["W004"]["flags"], "shortened")
        self.assertEqual((by["W003"]["ref_weeks_used"], by["W003"]["ref_weeks_skipped"],
                          by["W003"]["ref_weeks_before_first_record"]), ("52", "5", "0"))
        self.assertEqual((by["W004"]["ref_weeks_skipped"], by["W004"]["ref_weeks_before_first_record"]), ("0", "57"))
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("Not legal advice; a payroll professional signs off", md.split("\n")[2])
        for s in ("Workers loaded: 8", "Workers with leave: 5", "Leave weeks checked: 5", "Underpayments: 3, total underpaid £145.00",
                  "Overpayments: 1, total overpaid £10.00", "Workers with flags: 1 (W004)",
                  "### W002, week ending 2025-08-09", "underpaid by £80.00",
                  "57 week(s) before the first payroll record in the file not counted"):
            self.assertIn(s, md)

    def test_threshold(self):
        def lb(*a):
            return [r["worker_id"] for r in self.audit(*a)[1] if r["check"] == "leave_lookback"]
        self.assertEqual(lb("--threshold", "20"), ["W002", "W004"])     # only 80.00 and 50.00 exceed 20
        self.assertEqual(lb("--threshold", "80"), [])                   # strictly greater than
        self.assertEqual(lb("--threshold", "80", "--include-flagged"), ["W004"])

    def test_validation_failure_exit_2_writes_nothing(self):
        bad = self.write("bad.csv", H + "W1,not-a-date,basic,1\nW1,2025-06-07,zzz,1\n")
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", bad, "--leave", f"{SAMPLES}/leave.csv", "--out", out)
        self.assertEqual(code, 2)
        self.assertIn("bad.csv:2:", err); self.assertIn("bad.csv:3:", err)
        self.assertFalse(os.path.exists(out))

    def test_without_workers_file_defaults_to_variable_hours(self):
        out = os.path.join(self.tmp.name, "o2")
        self.assertEqual(run_cli("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv", "--out", out)[0], 0)
        self.assertTrue(os.path.exists(f"{out}/report.md"))


class OutputHandling(Base):
    def args(self, out, history=None):
        return ("--history", history or f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv", "--out", out)

    def test_out_is_existing_file(self):
        f = self.write("afile", "x")
        code, err = run_cli(*self.args(f))
        self.assertEqual(code, 2)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("cannot write output", err)
        self.assertNotIn("Traceback", err)

    def test_out_parent_not_writable_or_missing(self):
        f = self.write("afile", "x")
        code, err = run_cli(*self.args(os.path.join(f, "sub")))   # parent is a file
        self.assertEqual((code, len(err.strip().splitlines())), (2, 1))
        self.assertIn("cannot write output", err)

    def test_second_write_failure_leaves_no_partial_outputs(self):
        from unittest import mock
        import report.builder as b
        out = os.path.join(self.tmp.name, "out")
        # old outputs exist and must stay untouched when the new write fails
        os.makedirs(out)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n), "w") as fh:
                fh.write("OLD " + n)
        # fail during the second temp write (report.md) before anything is renamed
        real_fdopen = os.fdopen
        n_open = []

        def fdopen(fd, *a, **kw):
            n_open.append(1)
            if len(n_open) == 2:
                os.close(fd)
                raise OSError("disk full")
            return real_fdopen(fd, *a, **kw)
        with mock.patch.object(b.os, "fdopen", fdopen):
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 2)
        self.assertIn("disk full", err)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n)) as fh:
                self.assertEqual(fh.read(), "OLD " + n)
        self.assertEqual(sorted(os.listdir(out)), ["exceptions.csv", "report.md"])   # no temp files left

    def test_rename_failure_cleans_temps_and_fresh_dir_has_no_outputs(self):
        from unittest import mock
        import report.builder as b
        out = os.path.join(self.tmp.name, "fresh")

        def boom(src, dst):
            raise OSError("rename failed")
        with mock.patch.object(b.os, "replace", boom):
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 2)
        self.assertEqual(os.listdir(out), [])

    def _fail_second_replace(self):
        from unittest import mock
        import report.builder as b
        real = os.replace

        def flaky(src, dst):
            if os.path.basename(dst) == "report.md" and src.endswith(".tmp"):
                raise OSError("second rename failed")
            return real(src, dst)
        return mock.patch.object(b.os, "replace", flaky)

    def test_second_rename_failure_rolls_back_to_old_pair(self):
        out = os.path.join(self.tmp.name, "out")
        os.makedirs(out)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n), "w") as fh:
                fh.write("OLD " + n)
        with self._fail_second_replace():
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 2)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n)) as fh:
                self.assertEqual(fh.read(), "OLD " + n)
        self.assertEqual(sorted(os.listdir(out)), ["exceptions.csv", "report.md"])

    def test_failed_rollback_keeps_backup_and_names_it(self):
        from unittest import mock
        import report.builder as b
        out = os.path.join(self.tmp.name, "out")
        os.makedirs(out)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n), "w") as fh:
                fh.write("OLD " + n)
        real = os.replace

        def flaky(src, dst):
            if src.endswith(".bak") or (os.path.basename(dst) == "report.md" and src.endswith(".tmp")):
                raise OSError("replace refused")
            return real(src, dst)
        with mock.patch.object(b.os, "replace", flaky):
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 2)
        baks = [n for n in os.listdir(out) if n.endswith(".bak")]
        self.assertEqual(len(baks), 1)
        self.assertIn(os.path.join(out, baks[0]), err)
        self.assertIn("rollback failed", err)
        with open(os.path.join(out, baks[0])) as fh:
            self.assertEqual(fh.read(), "OLD exceptions.csv")
        self.assertFalse([n for n in os.listdir(out) if n.endswith(".tmp")])

    def test_link_unavailable_uses_copy_fallback_and_rolls_back(self):
        from unittest import mock
        import errno
        import report.builder as b
        out = os.path.join(self.tmp.name, "out")
        os.makedirs(out)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n), "w") as fh:
                fh.write("OLD " + n)
        def nolink(*a, **k):
            raise OSError(errno.EPERM, "no links")
        with mock.patch.object(b.os, "link", nolink), self._fail_second_replace():
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 2)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n)) as fh:
                self.assertEqual(fh.read(), "OLD " + n)
        self.assertEqual(sorted(os.listdir(out)), ["exceptions.csv", "report.md"])

    def _old_outputs(self):
        out = os.path.join(self.tmp.name, "out")
        os.makedirs(out)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n), "w") as fh:
                fh.write("OLD " + n)
        return out

    def test_only_link_fails_copy_fallback_succeeds(self):
        from unittest import mock
        import errno
        import report.builder as b
        out = self._old_outputs()

        def nolink(*a, **k):
            raise OSError(errno.EPERM, "no links")
        with mock.patch.object(b.os, "link", nolink):
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(os.listdir(out)), ["exceptions.csv", "report.md"])
        with open(os.path.join(out, "exceptions.csv")) as fh:
            self.assertTrue(fh.read().startswith("worker_id,"))
        with open(os.path.join(out, "report.md")) as fh:
            self.assertIn("# Holiday pay look-back audit", fh.read())

    def test_link_not_implemented_uses_copy_fallback(self):
        from unittest import mock
        import report.builder as b

        def nolink(*a, **k):
            raise NotImplementedError("follow_symlinks")
        out = self._old_outputs()
        with mock.patch.object(b.os, "link", nolink):
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(os.listdir(out)), ["exceptions.csv", "report.md"])

    def test_interrupt_with_failed_rollback_reraises_interrupt_and_keeps_backup(self):
        from unittest import mock
        import report.builder as b
        out = self._old_outputs()
        real = os.replace

        def flaky(src, dst):
            if src.endswith(".bak"):
                raise OSError("replace refused")
            if os.path.basename(dst) == "report.md" and src.endswith(".tmp"):
                raise KeyboardInterrupt()
            return real(src, dst)
        err = io.StringIO()
        with mock.patch.object(b.os, "replace", flaky), redirect_stderr(err):
            with self.assertRaises(KeyboardInterrupt) as cm:
                b.write_outputs(out, [], [])
        baks = [n for n in os.listdir(out) if n.endswith(".bak")]
        self.assertEqual(len(baks), 1)
        with open(os.path.join(out, baks[0])) as fh:
            self.assertEqual(fh.read(), "OLD exceptions.csv")
        self.assertIn(os.path.join(out, baks[0]), err.getvalue())
        if hasattr(cm.exception, "__notes__"):
            self.assertIn("kept at", "\n".join(cm.exception.__notes__))
        self.assertFalse([n for n in os.listdir(out) if n.endswith(".tmp")])

    def test_second_rename_failure_without_old_files_leaves_nothing(self):
        out = os.path.join(self.tmp.name, "fresh")
        with self._fail_second_replace():
            code, err = run_cli(*self.args(out))
        self.assertEqual(code, 2)
        self.assertEqual(os.listdir(out), [])

    def test_success_leaves_no_backups_and_owner_only_files(self):
        out = os.path.join(self.tmp.name, "out")
        os.makedirs(out)
        for n in ("exceptions.csv", "report.md"):
            with open(os.path.join(out, n), "w") as fh:
                fh.write("OLD")
        self.assertEqual(run_cli(*self.args(out))[0], 0)
        self.assertEqual(sorted(os.listdir(out)), ["exceptions.csv", "report.md"])
        for n in os.listdir(out):
            self.assertEqual(os.stat(os.path.join(out, n)).st_mode & 0o777, 0o600)

    def test_week_ranges_single_run_and_two_runs(self):
        from datetime import date, timedelta
        from report.builder import _week_ranges
        d0 = date(2025, 1, 4)
        wk = lambda *ns: [d0 + timedelta(days=7 * n) for n in ns]
        self.assertEqual(_week_ranges(wk(0)), ["2025-01-04"])
        self.assertEqual(_week_ranges(wk(0, 1, 2, 3, 4)), ["2025-01-04 to 2025-02-01 (5 weeks)"])
        self.assertEqual(_week_ranges(wk(0, 1, 5, 7, 8)),
                         ["2025-01-04 to 2025-01-11 (2 weeks)", "2025-02-08", "2025-02-22 to 2025-03-01 (2 weeks)"])

    def test_gap_section_uses_ranges(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100\nW1,2025-07-19,basic,100\n")
        l = self.write("l.csv", L + "W1,2025-07-19\n")
        out = os.path.join(self.tmp.name, "out")
        self.assertEqual(run_cli("--history", h, "--leave", l, "--out", out)[0], 0)
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            self.assertIn("W1: 5 week(s): 2025-06-14 to 2025-07-12 (5 weeks)", fh.read())

    def test_gaps_none_omits_summary_line(self):
        import report
        out = os.path.join(self.tmp.name, "out")
        report.write_outputs(out, [], [])
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            self.assertNotIn("weeks missing from the export", fh.read())
        report.write_outputs(out, [], [], gaps={})
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            self.assertIn("Workers with weeks missing from the export: 0", fh.read())

    def test_history_gaps_exported(self):
        import report
        self.assertTrue(callable(report.history_gaps))

    def test_mid_history_gap_warning(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100\nW1,2025-06-14,basic,100\n"
                       "W1,2025-06-28,basic,100\nW1,2025-07-12,basic,100\n"
                       "W2,2025-06-07,basic,100\nW2,2025-06-14,basic,100\n")
        l = self.write("l.csv", L + "W1,2025-07-12\n")
        out = os.path.join(self.tmp.name, "out")
        self.assertEqual(run_cli("--history", h, "--leave", l, "--out", out)[0], 0)
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("weeks missing from the export", md)
        self.assertIn("W1: 2 week(s): 2025-06-21, 2025-07-05", md)
        self.assertNotIn("W2:", md)
        self.assertIn("Workers loaded: 2", md)
        self.assertIn("Workers with leave: 1", md)
        self.assertIn("Workers with weeks missing from the export: 1", md)

    def test_no_gap_section_for_sample(self):
        out = os.path.join(self.tmp.name, "out")
        self.assertEqual(run_cli(*self.args(out), "--workers", f"{SAMPLES}/workers.csv")[0], 0)
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        # the only warning is the holiday_pay one for the rolled-up sample worker W008 (T-126)
        self.assertEqual(md.count("## Warning"), 1)
        self.assertIn("## Warning: holiday_pay recorded for an irregular_rolled_up worker", md)

    def test_history_file_error_suppresses_no_history_noise(self):
        iss = self.issues(H + "W1,not-a-date,basic,1\n", leave=L + "W1,2025-06-14\nW2,2025-06-14\n")
        self.has(iss, "h.csv:2:")
        self.assertFalse(any("no payroll history" in i for i in iss), iss)

    def test_no_history_message_kept_when_history_is_fine(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\n", leave=L + "W2,2025-06-14\n")
        self.has(iss, "no payroll history")


if __name__ == "__main__":
    unittest.main()
