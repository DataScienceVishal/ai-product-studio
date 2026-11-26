"""Tests for the Part B mapper. Invented fixtures only; no network (urlopen is mocked)."""
import contextlib
import csv
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.error

from mapper import extract_names, run, score
from mapper.mapper import AzureOpenAIClient, ClientError, Completion, FakeClient, map_names, validate_reply
from mapper.prompt import CATEGORIES, PROMPT_SHA256, SYSTEM_PROMPT


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
        write_csv(self.p("g.csv"), ["id", "pay_element_name", "source_style", "category", "note"],
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
        r, probs = validate_reply('[{"id":"a","category":"basic"},{"id":"b","category":"commission"}]', ["a", "b"])
        self.assertEqual(r, {"a": "basic", "b": "commission"})
        self.assertEqual(probs, [])

    def test_malformed_json(self):
        r, probs = validate_reply("not json", ["a"])
        self.assertEqual(r, {"a": "UNMAPPED"})
        self.assertTrue(probs)

    def test_fenced_json_is_not_repaired(self):
        r, _ = validate_reply('```json\n[{"id":"a","category":"basic"}]\n```', ["a"])
        self.assertEqual(r["a"], "UNMAPPED")

    def test_not_array(self):
        self.assertEqual(validate_reply('{"id":"a"}', ["a"])[0], {"a": "UNMAPPED"})

    def test_missing_id(self):
        r, probs = validate_reply('[{"id":"a","category":"basic"}]', ["a", "b"])
        self.assertEqual(r, {"a": "basic", "b": "UNMAPPED"})
        self.assertIn("id b missing", probs)

    def test_duplicate_id_unmapped_even_if_same(self):
        r, _ = validate_reply('[{"id":"a","category":"basic"},{"id":"a","category":"basic"}]', ["a"])
        self.assertEqual(r["a"], "UNMAPPED")

    def test_unknown_category(self):
        r, _ = validate_reply('[{"id":"a","category":"Basic"},{"id":"b","category":"salary"}]', ["a", "b"])
        self.assertEqual(r, {"a": "UNMAPPED", "b": "UNMAPPED"})

    def test_extra_id_ignored(self):
        r, probs = validate_reply('[{"id":"a","category":"basic"},{"id":"zz","category":"basic"}]', ["a"])
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
        reply = json.dumps([{"id": "1", "category": "basic"}, {"id": "2", "category": "regular_overtime"}])
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
        read(self.p("r/run.started")) if False else open(self.p("r/run.started"), "w").close()
        client = ScriptedClient("[]")
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


class ScoreTests(Tmp):
    def setUp(self):
        super().setUp()
        write_csv(self.p("gold.csv"), ["id", "pay_element_name", "source_style", "category", "note"], GOLD_ROWS)
        self.sha = hashlib.sha256(read(self.p("gold.csv"), "rb")).hexdigest()
        self.run_json = self.p("run.json")
        with open(self.run_json, "w") as h:
            json.dump({"fake": False, "model": "m", "deployment": "d", "prompt_version": "v", "prompt_sha256": "x",
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
        c, seen, _ = self.make([FakeResponse({"model": "gpt-5-mini-2025", "choices": [{"message": {"content": " [] "}}],
                                              "usage": {"prompt_tokens": 11, "completion_tokens": 7}})])
        out = c.complete("SYS", "USR")
        req, timeout = seen[0]
        body = json.loads(req.data)
        self.assertEqual(req.full_url, "https://res.openai.azure.com/openai/v1/chat/completions")
        self.assertEqual(req.get_header("Api-key"), "SECRETKEY")
        self.assertEqual(req.get_method(), "POST")
        self.assertNotIn("temperature", body)
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

    def test_unreadable_reply(self):
        c, _, _ = self.make([FakeResponse({"unexpected": 1})])
        with self.assertRaises(ClientError):
            c.complete("s", "u")

    def test_from_env_defaults(self):
        c = AzureOpenAIClient.from_env({"AZURE_OPENAI_ENDPOINT": "https://r.example", "AZURE_OPENAI_API_KEY": "k"})
        self.assertEqual(c.deployment, "gpt-5-mini")
        with self.assertRaises(ValueError):
            AzureOpenAIClient.from_env({})

    def test_end_to_end_through_map_names(self):
        reply = json.dumps([{"id": "1", "category": "basic"}])
        c, _, _ = self.make([FakeResponse({"choices": [{"message": {"content": reply}}],
                                           "usage": {"prompt_tokens": 3, "completion_tokens": 4}})])
        res = map_names([{"id": "1", "pay_element_name": "Salary", "source_style": "s"}], c)
        self.assertEqual((res.predictions, res.input_tokens, res.output_tokens), ({"1": "basic"}, 3, 4))


if __name__ == "__main__":
    unittest.main()
