"""Tests for the Part B mapper. Invented fixtures only; no network (urlopen is mocked)."""
import contextlib
import csv
import hashlib
import io
import json
import os
import tempfile
import unittest
import unittest.mock
import urllib.error

from mapper import extract_names, run, score
from mapper import mapper as mapper_mod
import http.client
from mapper.mapper import AzureOpenAIClient, ClientError, Completion, FakeClient, map_names, validate_reply
from mapper.prompt import CATEGORIES, PROMPT_SHA256, SYSTEM_PROMPT, config_sha256


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(header)
        w.writerows(rows)


def read(path, mode="r"):
    with open(path, mode) as h:
        return h.read()


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name

    def p(self, name):
        return os.path.join(self.d, name)


class ScriptedClient:
    deployment = "scripted"

    def __init__(self, text, inp=100, out=50):
        self.text, self.inp, self.out, self.calls = text, inp, out, 0

    def complete(self, system, user):
        self.calls += 1
        return Completion(self.text, self.inp, self.out)


class PromptTests(unittest.TestCase):
    def test_nine_categories_all_defined_in_prompt(self):
        self.assertEqual(len(CATEGORIES), 9)
        for c in CATEGORIES:
            self.assertIn(c, SYSTEM_PROMPT)

    def test_sha_matches_text(self):
        self.assertEqual(PROMPT_SHA256, hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest())


class ExtractTests(Tmp):
    def test_strips_other_columns(self):
        write_csv(self.p("g.csv"), ["id", "pay_element_name", "source_style", "gold_category", "note"],
                  [["1", "Basic Pay", "brightpay", "basic", "AMBIGUOUS: x"], ["2", "PAYE", "sage", "deduction_excluded", ""]])
        self.assertEqual(quiet(extract_names.main, ["--in", self.p("g.csv"), "--out", self.p("n.csv")]), 0)
        text = read(self.p("n.csv"))
        self.assertEqual(text.splitlines()[0], "id,pay_element_name,source_style")
        self.assertNotIn("basic,", text.replace("Basic Pay", ""))
        self.assertNotIn("AMBIGUOUS", text)
        self.assertNotIn("deduction_excluded", text)
        self.assertEqual(len(text.splitlines()), 3)

    def test_refuses_missing_columns(self):
        write_csv(self.p("g.csv"), ["id", "pay_element_name", "category"], [["1", "x", "basic"]])
        self.assertNotEqual(quiet(extract_names.main, ["--in", self.p("g.csv"), "--out", self.p("n.csv")]), 0)
        self.assertFalse(os.path.exists(self.p("n.csv")))

    def test_run_rejects_names_file_with_label_column(self):
        write_csv(self.p("n.csv"), ["id", "pay_element_name", "source_style", "category"], [["1", "x", "s", "basic"]])
        self.assertEqual(quiet(run.main, ["--names", self.p("n.csv"), "--out", self.p("r"), "--fake"]), 2)


class ValidateTests(unittest.TestCase):
    def test_valid(self):
        r, probs = validate_reply('{"mappings":[{"id":"a","category":"basic"},{"id":"b","category":"commission"}]}', ["a", "b"])
        self.assertEqual(r, {"a": "basic", "b": "commission"})
        self.assertEqual(probs, [])

    def test_malformed_json(self):
        r, probs = validate_reply("not json", ["a"])
        self.assertEqual(r, {"a": "UNMAPPED"})
        self.assertTrue(probs)

    def test_fenced_json_is_not_repaired(self):
        r, _ = validate_reply('```json\n{"mappings":[{"id":"a","category":"basic"}]}\n```', ["a"])
        self.assertEqual(r["a"], "UNMAPPED")

    def test_not_array(self):
        self.assertEqual(validate_reply('[{"id":"a","category":"basic"}]', ["a"])[0], {"a": "UNMAPPED"})

    def test_missing_id(self):
        r, probs = validate_reply('{"mappings":[{"id":"a","category":"basic"}]}', ["a", "b"])
        self.assertEqual(r, {"a": "basic", "b": "UNMAPPED"})
        self.assertIn("id b missing", probs)

    def test_duplicate_id_unmapped_even_if_same(self):
        r, _ = validate_reply('{"mappings":[{"id":"a","category":"basic"},{"id":"a","category":"basic"}]}', ["a"])
        self.assertEqual(r["a"], "UNMAPPED")

    def test_unknown_category(self):
        r, _ = validate_reply('{"mappings":[{"id":"a","category":"Basic"},{"id":"b","category":"salary"}]}', ["a", "b"])
        self.assertEqual(r, {"a": "UNMAPPED", "b": "UNMAPPED"})

    def test_extra_id_ignored(self):
        r, probs = validate_reply('{"mappings":[{"id":"a","category":"basic"},{"id":"zz","category":"basic"}]}', ["a"])
        self.assertEqual(r, {"a": "basic"})
        self.assertTrue(probs)

    def test_map_names_batches_and_counts_tokens(self):
        rows = [{"id": str(i), "pay_element_name": "Overtime", "source_style": "s"} for i in range(5)]
        res = map_names(rows, FakeClient(), batch_size=2)
        self.assertEqual(res.requests, 3)
        self.assertEqual(set(res.predictions.values()), {"regular_overtime"})
        res2 = map_names(rows, ScriptedClient("garbage"))
        self.assertEqual(res2.unmapped, 5)
        self.assertEqual(res2.input_tokens, 100)

    def test_client_error_marks_batch_unmapped(self):
        class Boom:
            def complete(self, s, u):
                raise ClientError("down")
        res = map_names([{"id": "1", "pay_element_name": "x", "source_style": ""}], Boom())
        self.assertEqual(res.predictions, {"1": "UNMAPPED"})
        self.assertTrue(res.errors)

    def test_duplicate_input_ids_rejected(self):
        with self.assertRaises(ValueError):
            map_names([{"id": "1", "pay_element_name": "x"}, {"id": "1", "pay_element_name": "y"}], FakeClient())

    def test_fake_client_baseline(self):
        rows = [{"id": str(i), "pay_element_name": n, "source_style": ""} for i, n in enumerate(
            ["PAYE Tax", "Holiday Pay", "SSP", "Sales Commission", "Christmas Bonus", "Mileage", "Shift Allowance", "Salary"])]
        got = list(map_names(rows, FakeClient()).predictions.values())
        self.assertEqual(got, ["deduction_excluded", "holiday_pay_paid", "statutory_excluded", "commission",
                               "bonus_non_regular", "expense_excluded", "allowance", "basic"])


class NoAnswerTests(Tmp):
    """A failure with no reply must not use the one shot."""

    def setUp(self):
        super().setUp()
        write_csv(self.p("n.csv"), ["id", "pay_element_name", "source_style"], [["1", "Salary", "a"], ["2", "Overtime", "a"]])
        self.args = ["--names", self.p("n.csv"), "--out", self.p("r")]

    def failing(self, error):
        class C:
            deployment = "d"

            def complete(self, s, u):
                raise error
        return C()

    def test_http_400_leaves_no_lock_and_logs_attempt(self):
        rc = quiet(run.main, self.args, client=self.failing(ClientError("HTTP 400 [x] nope", http_code=400, attempts=1)))
        self.assertEqual(rc, 4)
        for f in ("predictions.csv", "run.json", "run.started"):
            self.assertFalse(os.path.exists(self.p("r/" + f)), f)
        entry = json.loads(read(self.p("r/attempts.jsonl")).splitlines()[0])
        self.assertEqual(entry["prompt_sha256"], PROMPT_SHA256)
        self.assertEqual(entry["failures"][0]["http_code"], 400)
        self.assertTrue(entry["timestamp_utc"].endswith("Z"))

    def test_unexpected_exception_class_is_no_answer(self):
        self.assertEqual(quiet(run.main, self.args, client=self.failing(IndexError("boom"))), 4)
        self.assertFalse(os.path.exists(self.p("r/run.started")))
        self.assertIn("IndexError", read(self.p("r/attempts.jsonl")))

    def test_same_prompt_rerun_allowed_and_failed_attempt_recorded(self):
        quiet(run.main, self.args, client=self.failing(ClientError("down")))
        reply = json.dumps({"mappings": [{"id": "1", "category": "basic"}, {"id": "2", "category": "basic"}]})
        self.assertEqual(quiet(run.main, self.args, client=ScriptedClient(reply)), 0)
        info = json.loads(read(self.p("r/run.json")))
        self.assertEqual(len(info["failed_attempts"]), 1)
        self.assertEqual(info["reasoning_effort"], "low")
        self.assertEqual(quiet(run.main, self.args, client=ScriptedClient(reply)), 3)

    def test_changed_setting_refused(self):
        quiet(run.main, self.args, client=self.failing(ClientError("down")))
        c = ScriptedClient("{}")
        c.max_output_tokens = 999  # a different output cap changes the run config
        self.assertEqual(quiet(run.main, self.args, client=c), 3)
        self.assertEqual(c.calls, 0)

    def test_changed_names_file_refused(self):
        quiet(run.main, self.args, client=self.failing(ClientError("down")))
        write_csv(self.p("n.csv"), ["id", "pay_element_name", "source_style"], [["1", "Salary", "a"], ["2", "Overtime!", "a"]])
        self.assertEqual(quiet(run.main, self.args, client=ScriptedClient("{}")), 3)

    def test_config_sha_covers_each_input(self):
        base = config_sha256(100, "n")
        self.assertEqual(base, config_sha256(100, "n"))
        self.assertNotEqual(base, config_sha256(101, "n"))
        self.assertNotEqual(base, config_sha256(100, "m"))
        import mapper.prompt as pr
        for attr, val in (("REASONING_EFFORT", "high"), ("SCHEMA_NAME", "x"), ("SYSTEM_PROMPT", "x"), ("USER_TEMPLATE", "x")):
            old = getattr(pr, attr)
            setattr(pr, attr, val)
            try:
                self.assertNotEqual(base, config_sha256(100, "n"), attr)
            finally:
                setattr(pr, attr, old)

    def test_config_sha_recorded_in_attempts_and_run_json(self):
        quiet(run.main, self.args, client=self.failing(ClientError("down")))
        a = json.loads(read(self.p("r/attempts.jsonl")).splitlines()[0])
        reply = json.dumps({"mappings": [{"id": "1", "category": "basic"}, {"id": "2", "category": "basic"}]})
        quiet(run.main, self.args, client=ScriptedClient(reply))
        info = json.loads(read(self.p("r/run.json")))
        self.assertEqual(info["config_sha256"], a["config_sha256"])
        self.assertEqual(len(info["names_sha256"]), 64)

    def test_changed_prompt_sha_refused(self):
        os.makedirs(self.p("r"))
        with open(self.p("r/attempts.jsonl"), "w") as h:
            h.write(json.dumps({"prompt_sha256": "0" * 64}) + "\n")
        client = ScriptedClient("{}")
        self.assertEqual(quiet(run.main, self.args, client=client), 3)
        self.assertEqual(client.calls, 0)

    def test_invalid_reply_still_locks(self):
        self.assertEqual(quiet(run.main, self.args, client=ScriptedClient("garbage", 70, 30)), 0)
        info = json.loads(read(self.p("r/run.json")))
        self.assertEqual((info["unmapped"], info["input_tokens"], info["output_tokens"]), (2, 70, 30))
        self.assertEqual(quiet(run.main, self.args, client=ScriptedClient("{}")), 3)

    def test_partial_failure_locks_and_records_usage(self):
        class Half:
            deployment = "d"
            n = 0

            def complete(self, s, u):
                Half.n += 1
                if Half.n == 1:
                    return Completion(json.dumps({"mappings": [{"id": "1", "category": "basic"}]}), 5, 6, "stop")
                raise ClientError("down", input_tokens=2, output_tokens=3)
        import mapper.mapper as mm
        orig = mm.map_names
        run.map_names = lambda rows, c, into=None: orig(rows, c, batch_size=1, into=into)
        try:
            self.assertEqual(quiet(run.main, self.args, client=Half()), 0)
        finally:
            run.map_names = orig
        info = json.loads(read(self.p("r/run.json")))
        self.assertEqual((info["input_tokens"], info["output_tokens"], info["unmapped"]), (7, 9, 1))
        self.assertEqual(len(info["batch_failures"]), 1)

    def test_crash_in_map_names_writes_run_json_and_locks(self):
        orig = run.map_names
        def crash(rows, c, into=None):
            into.input_tokens, into.output_tokens, into.requests = 11, 22, 1
            raise RuntimeError("bug")
        run.map_names = crash
        try:
            self.assertEqual(quiet(run.main, self.args, client=ScriptedClient("{}")), 5)
        finally:
            run.map_names = orig
        info = json.loads(read(self.p("r/run.json")))
        self.assertEqual((info["crashed"], info["input_tokens"], info["output_tokens"]), ("RuntimeError", 11, 22))
        self.assertAlmostEqual(info["cost_usd"], run.cost_usd(11, 22))
        self.assertTrue(os.path.exists(self.p("r/run.started")))

    def test_duplicate_names_ids_refused(self):
        write_csv(self.p("n.csv"), ["id", "pay_element_name", "source_style"], [["1", "a", "s"], ["1", "b", "s"]])
        self.assertEqual(quiet(run.main, self.args, client=ScriptedClient("{}")), 2)


class RunTests(Tmp):
    def names(self):
        write_csv(self.p("n.csv"), ["id", "pay_element_name", "source_style"],
                  [["1", "Salary", "a"], ["2", "Overtime", "a"]])

    def test_fake_run_outputs(self):
        self.names()
        self.assertEqual(quiet(run.main, ["--names", self.p("n.csv"), "--out", self.p("r"), "--fake"]), 0)
        info = json.loads(read(self.p("r/fake/run.json")))
        self.assertTrue(info["fake"])
        self.assertEqual(info["prompt_sha256"], PROMPT_SHA256)
        self.assertEqual(info["cost_usd"], 0.0)
        rows = list(csv.reader(read(self.p("r/fake/predictions.csv")).splitlines()))
        self.assertEqual(rows, [["id", "category"], ["1", "basic"], ["2", "regular_overtime"]])
        self.assertFalse(os.path.exists(self.p("r/run.json")))

    def test_fake_can_repeat(self):
        self.names()
        for _ in range(2):
            self.assertEqual(quiet(run.main, ["--names", self.p("n.csv"), "--out", self.p("r"), "--fake"]), 0)

    def test_live_one_shot_guard(self):
        self.names()
        reply = json.dumps({"mappings": [{"id": "1", "category": "basic"}, {"id": "2", "category": "regular_overtime"}]})
        client = ScriptedClient(reply, 1000, 500)
        args = ["--names", self.p("n.csv"), "--out", self.p("r")]
        self.assertEqual(quiet(run.main, args, client=client), 0)
        info = json.loads(read(self.p("r/run.json")))
        self.assertFalse(info["fake"])
        self.assertEqual(info["cost_usd"], round((1000 * 0.25 + 500 * 2.0) / 1e6, 6))
        self.assertEqual(quiet(run.main, args, client=client), 3)
        self.assertEqual(client.calls, 1)
        # a fake run must not unlock or overwrite it
        quiet(run.main, args + ["--fake"])
        self.assertEqual(quiet(run.main, args, client=client), 3)

    def test_guard_trips_on_started_marker_after_crash(self):
        self.names()
        os.makedirs(self.p("r"))
        open(self.p("r/run.started"), "w").close()
        client = ScriptedClient("{}")
        self.assertEqual(quiet(run.main, ["--names", self.p("n.csv"), "--out", self.p("r")], client=client), 3)
        self.assertEqual(client.calls, 0)

    def test_live_without_env_fails_cleanly(self):
        self.names()
        old = os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
        try:
            self.assertEqual(quiet(run.main, ["--names", self.p("n.csv"), "--out", self.p("r")]), 2)
        finally:
            if old is not None:
                os.environ["AZURE_OPENAI_ENDPOINT"] = old
        self.assertFalse(os.path.exists(self.p("r/run.started")))

    def test_cost_calc(self):
        self.assertAlmostEqual(run.cost_usd(1_000_000, 1_000_000), 2.25)
        self.assertEqual(run.cost_usd(0, 0), 0)


GOLD_ROWS = [  # invented: id, name, style, category, note
    ["1", "Basic", "s", "basic", ""],
    ["2", "OT", "s", "regular_overtime", ""],
    ["3", "Comm", "s", "commission", "AMBIGUOUS: could be bonus"],
    ["4", "PAYE", "s", "deduction_excluded", ""],
    ["5", "Mileage", "s", "expense_excluded", ""],
    ["6", "Hol", "s", "holiday_pay_paid", "AMBIGUOUS: x"],
    ["7", "SSP", "s", "statutory_excluded", ""],
    ["8", "Bonus", "s", "bonus_non_regular", ""],
]


class ScoreRefusalTests(Tmp):
    def go(self, gold_rows, pred_rows, run_extra=None, fake=False):
        write_csv(self.p("gold.csv"), ["id", "pay_element_name", "source_style", "gold_category", "note"], gold_rows)
        write_csv(self.p("pred.csv"), ["id", "category"], pred_rows)
        info = {"fake": fake, "names": len(gold_rows), "prompt_sha256": PROMPT_SHA256, "cost_usd": 0.0001}
        info.update(run_extra or {})
        with open(self.p("run.json"), "w") as h:
            json.dump(info, h)
        sha = hashlib.sha256(read(self.p("gold.csv"), "rb")).hexdigest()
        return quiet(score.main, ["--gold", self.p("gold.csv"), "--pred", self.p("pred.csv"), "--run", self.p("run.json"),
                                  "--expect-sha", sha, "--out", self.p("R.md")])

    def test_ok_baseline(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""]], [["1", "basic"]]), 0)

    def test_gold_category_outside_nine(self):
        self.assertEqual(self.go([["1", "a", "s", "ssp_smp_excluded", ""]], [["1", "basic"]]), 3)
        self.assertFalse(os.path.exists(self.p("R.md")))

    def test_duplicate_gold_ids(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""], ["1", "b", "s", "basic", ""]], [["1", "basic"]]), 3)

    def test_extra_pred_id(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""]], [["1", "basic"], ["9", "basic"]]), 3)

    def test_duplicate_pred_id(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""]], [["1", "basic"], ["1", "basic"]]), 3)

    def test_missing_pred_counts_unmapped_not_refused(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""], ["2", "b", "s", "basic", ""]], [["1", "basic"]]), 0)
        self.assertIn("UNMAPPED (invalid or missing, counted wrong): 1", read(self.p("R.md")))

    def test_old_category_header_refused(self):
        write_csv(self.p("gold.csv"), ["id", "category"], [["1", "basic"]])
        write_csv(self.p("pred.csv"), ["id", "category"], [["1", "basic"]])
        sha = hashlib.sha256(read(self.p("gold.csv"), "rb")).hexdigest()
        self.assertEqual(quiet(score.main, ["--gold", self.p("gold.csv"), "--pred", self.p("pred.csv"), "--run", "x",
                                            "--expect-sha", sha, "--out", self.p("R.md")]), 3)

    def test_fake_run_verdicts_na(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""]], [["1", "basic"]], fake=True), 0)
        text = read(self.p("R.md"))
        self.assertIn("**N/A (fake)**", text)
        self.assertNotIn("**PASS**", text)

    def test_config_sha_mismatch_warns(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""]], [["1", "basic"]],
                                 {"config_sha256": "a", "failed_attempts": [{"config_sha256": "b"}]}), 0)
        self.assertIn("WARNING: run config sha256", read(self.p("R.md")))

    def test_prompt_sha_mismatch_warns_in_report(self):
        self.assertEqual(self.go([["1", "a", "s", "basic", ""]], [["1", "basic"]], {"prompt_sha256": "bad"}), 0)
        self.assertIn("WARNING: run.json prompt sha256 differs", read(self.p("R.md")))

    def test_ambiguous_prefix_is_case_sensitive(self):
        m = score.compute([{"id": "1", "gold_category": "basic", "note": "ambiguous: x"},
                           {"id": "2", "gold_category": "basic", "note": "AMBIGUOUS: x"}], {})
        self.assertEqual(m["ambiguous"]["n"], 1)


class ExtractMoreTests(Tmp):
    def test_duplicate_ids_refused(self):
        write_csv(self.p("g.csv"), ["id", "pay_element_name", "source_style"], [["1", "a", "s"], ["1", "b", "s"]])
        self.assertNotEqual(quiet(extract_names.main, ["--in", self.p("g.csv"), "--out", self.p("n.csv")]), 0)

    def test_expect_sha(self):
        write_csv(self.p("g.csv"), ["id", "pay_element_name", "source_style"], [["1", "a", "s"]])
        sha = hashlib.sha256(read(self.p("g.csv"), "rb")).hexdigest()
        self.assertEqual(quiet(extract_names.main, ["--in", self.p("g.csv"), "--out", self.p("n.csv"), "--expect-sha", sha]), 0)
        self.assertNotEqual(quiet(extract_names.main, ["--in", self.p("g.csv"), "--out", self.p("m.csv"), "--expect-sha", "0" * 64]), 0)
        self.assertFalse(os.path.exists(self.p("m.csv")))


class ScoreTests(Tmp):
    def setUp(self):
        super().setUp()
        write_csv(self.p("gold.csv"), ["id", "pay_element_name", "source_style", "gold_category", "note"], GOLD_ROWS)
        self.sha = hashlib.sha256(read(self.p("gold.csv"), "rb")).hexdigest()
        self.run_json = self.p("run.json")
        with open(self.run_json, "w") as h:
            json.dump({"fake": False, "model": "m", "deployment": "d", "prompt_version": "v", "prompt_sha256": PROMPT_SHA256,
                       "names": 8, "input_tokens": 1, "output_tokens": 1, "cost_usd": 0.004, "timestamp_utc": "t"}, h)

    def pred(self, mapping):
        write_csv(self.p("pred.csv"), ["id", "category"], [[k, v] for k, v in mapping.items()])

    def gold(self):
        return score.read_csv(self.p("gold.csv"))

    def test_maths(self):
        preds = {"1": "basic", "2": "regular_overtime", "3": "bonus_non_regular",  # 3 wrong (ambiguous)
                 "4": "expense_excluded",  # wrong on nine, right on eight
                 "5": "expense_excluded", "6": "holiday_pay_paid", "7": "statutory_excluded", "8": "UNMAPPED"}
        m = score.compute(self.gold(), preds)
        self.assertEqual(m["n"], 8)
        self.assertAlmostEqual(m["acc9"], 5 / 8)
        self.assertAlmostEqual(m["acc8"], 6 / 8)
        self.assertEqual(m["ambiguous"], {"n": 2, "acc9": 0.5})
        self.assertAlmostEqual(m["rest"]["acc9"], 4 / 6)
        self.assertEqual(m["unmapped"], 1)
        pc = m["per_category"]["expense_excluded"]
        self.assertEqual((pc["support"], pc["predicted"]), (1, 2))
        self.assertAlmostEqual(pc["precision"], 0.5)
        self.assertEqual(pc["recall"], 1.0)
        self.assertEqual(m["confusion"]["deduction_excluded"]["expense_excluded"], 1)
        self.assertEqual(m["confusion"]["bonus_non_regular"]["UNMAPPED"], 1)

    def test_missing_prediction_counts_wrong(self):
        self.assertEqual(score.compute(self.gold(), {})["unmapped"], 8)

    def test_unmapped_never_matches(self):
        self.assertEqual(score.compute(self.gold(), {"1": "UNMAPPED"})["acc9"], 0)

    def test_verdicts(self):
        self.assertEqual(score.b2_verdict(0.0199), "PASS")
        self.assertEqual(score.b2_verdict(0.02), "REVIEW")
        self.assertEqual(score.b2_verdict(0.05), "REVIEW")
        self.assertEqual(score.b2_verdict(0.0501), "KILL")

    def test_sha_mismatch_refused(self):
        self.pred({r[0]: r[3] for r in GOLD_ROWS})
        rc = quiet(score.main, ["--gold", self.p("gold.csv"), "--pred", self.p("pred.csv"), "--run", self.run_json,
                                "--expect-sha", "0" * 64, "--out", self.p("R.md")])
        self.assertEqual(rc, 3)
        self.assertFalse(os.path.exists(self.p("R.md")))

    def test_report_perfect_and_cost_per_200(self):
        self.pred({r[0]: r[3] for r in GOLD_ROWS})
        rc = quiet(score.main, ["--gold", self.p("gold.csv"), "--pred", self.p("pred.csv"), "--run", self.run_json,
                                "--expect-sha", self.sha, "--out", self.p("R.md")])
        self.assertEqual(rc, 0)
        text = read(self.p("R.md"))
        self.assertIn("Headline: nine-category accuracy 100.0%", text)
        self.assertIn("B1 (nine-category accuracy 100.0%, PASS needs >= 95%): **PASS**", text)
        self.assertIn("cost per 200 names $0.1000", text)  # 0.004 / 8 * 200
        self.assertIn("**KILL**", text)  # B2 only

    def test_report_kill_below_95(self):
        preds = {r[0]: r[3] for r in GOLD_ROWS}
        preds["1"] = "allowance"
        self.pred(preds)
        quiet(score.main, ["--gold", self.p("gold.csv"), "--pred", self.p("pred.csv"), "--run", self.run_json,
                           "--expect-sha", self.sha, "--out", self.p("R.md")])
        self.assertIn("accuracy 87.5%, PASS needs >= 95%): **KILL**", read(self.p("R.md")))


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode()

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class AzureClientTests(unittest.TestCase):
    def make(self, responses, **kw):
        seen = []

        def opener(request, timeout=None):
            seen.append((request, timeout))
            r = responses.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        sleeps = []
        c = AzureOpenAIClient("https://res.openai.azure.com/", "gpt-5-mini", "SECRETKEY", opener=opener,
                              sleep=sleeps.append, **kw)
        return c, seen, sleeps

    def test_chat_request_shape_and_usage(self):
        c, seen, _ = self.make([FakeResponse({"model": "gpt-5-mini-2025", "choices": [{"finish_reason": "stop", "message": {"content": " [] "}}],
                                              "usage": {"prompt_tokens": 11, "completion_tokens": 7}})])
        out = c.complete("SYS", "USR")
        req, timeout = seen[0]
        body = json.loads(req.data)
        self.assertEqual(req.full_url, "https://res.openai.azure.com/openai/v1/chat/completions")
        self.assertEqual(req.get_header("Api-key"), "SECRETKEY")
        self.assertEqual(req.get_method(), "POST")
        self.assertNotIn("temperature", body)
        self.assertEqual(body["reasoning_effort"], "low")
        rf = body["response_format"]["json_schema"]
        self.assertTrue(rf["strict"])
        self.assertEqual(rf["schema"]["properties"]["mappings"]["items"]["properties"]["category"]["enum"], list(CATEGORIES))
        self.assertEqual(out.finish_reason, "stop")
        self.assertEqual(body["model"], "gpt-5-mini")
        self.assertEqual(body["messages"][0], {"role": "system", "content": "SYS"})
        self.assertIn("max_completion_tokens", body)
        self.assertTrue(timeout)
        self.assertEqual((out.text, out.input_tokens, out.output_tokens), ("[]", 11, 7))
        self.assertEqual(c.reported_model, "gpt-5-mini-2025")

    def test_responses_request_and_usage(self):
        seen = []
        resp = FakeResponse({"status": "completed", "output": [{"type": "reasoning"},
                             {"type": "message", "content": [{"type": "output_text", "text": "[1]"}]}],
                             "usage": {"input_tokens": 5, "output_tokens": 9}})
        c = AzureOpenAIClient("https://res.openai.azure.com/openai/v1/responses", "dep", "k",
                              opener=lambda r, timeout=None: seen.append(r) or resp)
        out = c.complete("SYS", "USR")
        body = json.loads(seen[0].data)
        self.assertTrue(seen[0].full_url.endswith("/openai/v1/responses"))
        self.assertEqual(body["instructions"], "SYS")
        self.assertNotIn("temperature", body)
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertEqual((out.text, out.input_tokens, out.output_tokens), ("[1]", 5, 9))

    def test_retries_5xx_with_backoff_then_succeeds(self):
        err = urllib.error.HTTPError("u", 503, "x", {}, None)
        ok = FakeResponse({"choices": [{"message": {"content": "[]"}}], "usage": {}})
        c, seen, sleeps = self.make([err, ok])
        self.assertEqual(c.complete("s", "u").text, "[]")
        self.assertEqual(len(seen), 2)
        self.assertEqual(sleeps, [2])

    def test_4xx_not_retried_and_key_not_in_message(self):
        c, seen, _ = self.make([urllib.error.HTTPError("u", 400, "bad", {}, None)])
        with self.assertRaises(ClientError) as cm:
            c.complete("s", "u")
        self.assertEqual(len(seen), 1)
        self.assertIn("400", str(cm.exception))
        self.assertNotIn("SECRETKEY", str(cm.exception))

    def test_gives_up_after_retries(self):
        c, seen, _ = self.make([urllib.error.URLError("host https://x"), TimeoutError(), OSError()])
        with self.assertRaises(ClientError) as cm:
            c.complete("s", "u")
        self.assertEqual(len(seen), 3)
        self.assertNotIn("https://x", str(cm.exception))

    def test_wrong_shape_keeps_usage_and_gives_empty_text(self):
        for payload in ({"unexpected": 1, "usage": {"prompt_tokens": 6, "completion_tokens": 9}},
                        {"choices": [], "usage": {"prompt_tokens": 6, "completion_tokens": 9}}):
            c, _, _ = self.make([FakeResponse(payload)])
            out = c.complete("s", "u")
            self.assertEqual((out.text, out.input_tokens, out.output_tokens), ("", 6, 9))

    def test_responses_non_dict_output_item(self):
        c = AzureOpenAIClient("https://r.example/openai/v1/responses", "d", "k", opener=lambda r, timeout=None: FakeResponse(
            {"output": ["junk"], "usage": {"input_tokens": 4, "output_tokens": 8}}))
        out = c.complete("s", "u")
        self.assertEqual((out.text, out.input_tokens, out.output_tokens), ("", 4, 8))

    def test_responses_incomplete_status_recorded(self):
        c = AzureOpenAIClient("https://r.example/openai/v1/responses", "d", "k", opener=lambda r, timeout=None: FakeResponse(
            {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
             "usage": {"input_tokens": 1, "output_tokens": 2}}))
        self.assertEqual(c.complete("s", "u").finish_reason, "incomplete:max_output_tokens")

    def test_not_json_body_is_no_answer(self):
        class Raw(FakeResponse):
            def __init__(self):
                self.raw = b"<html>"
        c, _, _ = self.make([Raw()])
        with self.assertRaises(ClientError):
            c.complete("s", "u")

    def test_incomplete_read_is_retried_as_network_error(self):
        ok = FakeResponse({"choices": [{"message": {"content": "{}"}}], "usage": {}})
        c, seen, _ = self.make([http.client.IncompleteRead(b"x"), ok])
        self.assertEqual(c.complete("s", "u").attempts, 2)

    def test_4xx_detail_included_and_key_redacted(self):
        body = io.BytesIO(json.dumps({"error": {"code": "unsupported_value",
                                                "message": "bad SECRETKEY param " + "x" * 500}}).encode())
        c, _, _ = self.make([urllib.error.HTTPError("u", 400, "bad", {}, body)])
        with self.assertRaises(ClientError) as cm:
            c.complete("s", "u")
        msg = str(cm.exception)
        self.assertIn("unsupported_value", msg)
        self.assertNotIn("SECRETKEY", msg)
        self.assertLess(len(msg), 450)
        self.assertEqual(cm.exception.http_code, 400)

    def test_from_env_defaults(self):
        c = AzureOpenAIClient.from_env({"AZURE_OPENAI_ENDPOINT": "https://r.example", "AZURE_OPENAI_API_KEY": "k"})
        self.assertEqual(c.deployment, "gpt-5-mini")
        with self.assertRaises(ValueError):
            AzureOpenAIClient.from_env({})

    def test_end_to_end_through_map_names(self):
        reply = json.dumps({"mappings": [{"id": "1", "category": "basic"}]})
        c, _, _ = self.make([FakeResponse({"choices": [{"message": {"content": reply}}],
                                           "usage": {"prompt_tokens": 3, "completion_tokens": 4}})])
        res = map_names([{"id": "1", "pay_element_name": "Salary", "source_style": "s"}], c)
        self.assertEqual((res.predictions, res.input_tokens, res.output_tokens), ({"1": "basic"}, 3, 4))


if __name__ == "__main__":
    unittest.main()


class SpendCapTests(Tmp):
    def names(self, n, text="Salary"):
        write_csv(self.p("n.csv"), ["id", "pay_element_name", "source_style"], [[str(i), text, "a"] for i in range(n)])
        return ["--names", self.p("n.csv"), "--out", self.p("r")]

    def go(self, args, client=None):
        client = client or ScriptedClient('{"mappings":[]}')
        return quiet(run.main, args, client=client), client

    def test_too_many_names_refused_before_any_call(self):
        rc, c = self.go(self.names(run.MAX_NAMES + 1))
        self.assertEqual((rc, c.calls), (2, 0))
        self.assertFalse(os.path.exists(self.p("r/run.started")))

    def test_long_name_refused(self):
        rc, c = self.go(self.names(2, "x" * (run.MAX_NAME_CHARS + 1)))
        self.assertEqual((rc, c.calls), (2, 0))

    def test_name_at_limit_ok(self):
        rc, _ = self.go(self.names(2, "x" * run.MAX_NAME_CHARS))
        self.assertEqual(rc, 0)

    def test_request_size_cap(self):
        rows = [{"id": str(i), "pay_element_name": "x" * 120, "source_style": "a"} for i in range(500)]
        with unittest.mock.patch.object(run, "MAX_REQUEST_CHARS", 1000):
            total, reason = run.preflight(rows, ScriptedClient(""), 2.0)
        self.assertIn("characters", reason)

    def test_default_cap_is_two_dollars_and_normal_run_fits(self):
        self.assertEqual(run.DEFAULT_MAX_USD, 2.0)
        rows = [{"id": str(i), "pay_element_name": "x" * 120, "source_style": "a"} for i in range(200)]
        total, reason = run.preflight(rows, ScriptedClient(""), 2.0)
        self.assertEqual(reason, "")
        self.assertGreater(total, 0.05)

    def test_lower_cap_refuses_and_records_nothing(self):
        rc, c = self.go(self.names(2) + ["--max-usd", "0.01"])
        self.assertEqual((rc, c.calls), (2, 0))
        self.assertFalse(os.path.exists(self.p("r/run.started")))

    def test_cap_above_hard_max_needs_flag(self):
        rc, c = self.go(self.names(2) + ["--max-usd", "5"])
        self.assertEqual((rc, c.calls), (2, 0))
        rc, c = self.go(self.names(2) + ["--max-usd", "5", "--allow-over-cap"])
        self.assertEqual((rc, c.calls), (0, 1))

    def test_bad_max_usd_values(self):
        for v in ("0", "-1", "nan", "inf"):
            rc, c = self.go(self.names(2) + ["--max-usd", v])
            self.assertEqual((rc, c.calls), (2, 0), v)

    def test_missing_or_nonpositive_price_refused(self):
        rows = [{"id": "1", "pay_element_name": "Salary", "source_style": "a"}]
        for bad in (None, (0, 2.0), (0.25, 0), (-1, 2), (float("nan"), 1), ("a", "b"), ()):
            total, reason = run.preflight(rows, ScriptedClient(""), 2.0, price=bad)
            self.assertTrue(reason, bad)

    def test_retries_counted_in_estimate(self):
        rows = [{"id": "1", "pay_element_name": "Salary", "source_style": "a"}]
        a, b = ScriptedClient(""), ScriptedClient("")
        a.retries, b.retries = 0, 2
        self.assertAlmostEqual(run.preflight(rows, b, 2.0)[0], 3 * run.preflight(rows, a, 2.0)[0], places=6)

    def test_run_json_records_cap_and_estimate(self):
        rc, _ = self.go(self.names(2))
        info = json.loads(read(self.p("r/run.json")))
        self.assertEqual(info["spend_cap_usd"], 2.0)
        self.assertGreater(info["worst_case_estimate_usd"], 0)

    def test_prompt_sha_unchanged_by_cap(self):
        from mapper.prompt import PROMPT_SHA256
        self.assertEqual(PROMPT_SHA256, "ae175fa9c2fa89f244dba58854abe9ea0739d86ea35cfe9a917b746b88a4a5ed")  # the sha on main

    def test_client_counts_retries_against_cap(self):
        calls = []

        def opener(request, timeout=None):
            calls.append(1)
            raise urllib.error.HTTPError("https://x", 503, "x", {}, None)
        c = AzureOpenAIClient("https://r.example", "d", "k", opener=opener, sleep=lambda s: None)
        worst = mapper_mod.worst_case_usd(mapper_mod.estimate_input_tokens("s", "u"), c.max_output_tokens, run.DEFAULT_PRICE)
        c.set_spend_cap(worst * 2.5, run.DEFAULT_PRICE)  # room for two attempts, not three
        with self.assertRaises(ClientError) as ctx:
            c.complete("s", "u")
        self.assertEqual(len(calls), 2)
        self.assertIn("cap", str(ctx.exception))

    def test_client_refuses_bad_price_for_cap(self):
        c = AzureOpenAIClient("https://r.example", "d", "k", opener=lambda r, timeout=None: None)
        with self.assertRaises(ValueError):
            c.set_spend_cap(2.0, (0, 0))


class TransportSecurityTests(unittest.TestCase):
    def test_http_endpoint_refused(self):
        for url in ("http://res.openai.azure.com", "ftp://x", "res.openai.azure.com", "http://127.0.0.1:1"):
            with self.assertRaises(ValueError, msg=url):
                AzureOpenAIClient(url, "d", "k")

    def test_http_localhost_only_with_explicit_flag(self):
        AzureOpenAIClient("http://127.0.0.1:1", "d", "k", allow_insecure_localhost=True)
        with self.assertRaises(ValueError):
            AzureOpenAIClient("http://evil.example", "d", "k", allow_insecure_localhost=True)
        with self.assertRaises(ValueError):
            AzureOpenAIClient("http://localhost.evil.example", "d", "k", allow_insecure_localhost=True)

    def test_from_env_refuses_http(self):
        with self.assertRaises(ValueError):
            AzureOpenAIClient.from_env({"AZURE_OPENAI_ENDPOINT": "http://x.example", "AZURE_OPENAI_API_KEY": "k"})

    def test_redirect_not_followed_and_key_not_forwarded(self):
        import http.server
        import threading
        hits = []

        class Second(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.headers.get("api-key"))
                self.send_response(200)
                self.end_headers()
            do_POST = do_GET

            def log_message(self, *a):
                pass
        second = http.server.HTTPServer(("127.0.0.1", 0), Second)

        class First(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{second.server_port}/steal")
                self.end_headers()

            def log_message(self, *a):
                pass
        first = http.server.HTTPServer(("127.0.0.1", 0), First)
        for srv in (first, second):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        sleeps = []
        try:
            c = AzureOpenAIClient(f"http://127.0.0.1:{first.server_port}", "d", "TESTKEY", sleep=sleeps.append,
                                  allow_insecure_localhost=True, timeout=5)
            with self.assertRaises(ClientError) as ctx:
                c.complete("s", "u")
        finally:
            first.shutdown()
            second.shutdown()
        self.assertEqual(hits, [])
        self.assertEqual(ctx.exception.http_code, 302)
        self.assertEqual(sleeps, [])  # not retried
        self.assertNotIn("TESTKEY", str(ctx.exception))
