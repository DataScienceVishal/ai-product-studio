# Review: T-124 (`p/holiday-pay-payroll-lookback-audit/T-124`, head 9fbb0c9)

Reviewer, 2026-11-26. Diff: `git diff origin/main...9fbb0c9`. 6 files, +118/-8.

## Verdict: PASS

## Summary
- **contract_weekly_basic:** a zero value for a `fixed_pay` worker is now refused with `file:line` and exit 2. A negative value was already refused by `_amount`, which masks the value. A value on a `variable_hours` worker gives a `## Warning: contract_weekly_basic ignored` section in report.md, a summary count line and a stderr note, and the exit code stays 0. This closes T-119 QA L3 (fx2, fx4).
- **NI glued to a letter prefix:** this is still not detected, on purpose, and the reason is written in FORMAT.md. I re-ran the window scan from the test: it flags **12 of 30** plausible payroll IDs (the brief said 11), including the shape FORMAT.md itself recommends (`EMP100234`, `EMP100234A`). The scan does catch `EMPAB123456C`, but nothing in the ID's shape separates it from `STAFF100234A`, so refusing those IDs would break normal data. The decision is sound and documented, and FORMAT.md still says not to rely on the check.

## Evidence
- Full suite from the product folder, `python3 -I -m unittest discover -s tests -t .`: **Ran 228 tests, OK**.
- Samples: I ran `audit.py` on `samples/` with the main tree and with the branch. `diff -r` of the two output folders is empty (both print "5 leave weeks checked, 4 exceptions").
- Manual CLI run with a workers.csv containing variable_hours `0`, fixed_pay `0` and variable_hours `-1`: exit 2. Errors at `w.csv:3` (greater than 0) and `w.csv:4` (masked `'-1...'`). The variable_hours `0` row passes, as intended.
- Mutation runs (each mutation applied on its own, then the suite run):

| Mutation | Result |
|---|---|
| `amt == 0` changed to `amt < 0` | killed (2 failures) |
| `ignored_contract_basic` drops the worker_type filter | killed |
| report section removed | killed |
| stderr note removed | killed |
| `ignored` not passed to `write_outputs` | killed |
| `and worker_type == "fixed_pay"` dropped from the zero check | **survived** |
| summary count line removed | **survived** |
| `_md()` escaping removed from the warning list | survived (equivalent mutant: validated IDs have no Markdown characters) |
| `amt = None` after the zero error removed | survived (equivalent mutant: `ValidationError` is raised anyway) |

## Critical issues
None.

## Suggestions (not blocking)
1. **Missing test for variable_hours with `0`** (`tests/test_t124.py`). Add a test that a `variable_hours` worker with a value of `0` exits 0 and gets the warning. Without it, the surviving mutation above could start refusing valid files.
2. **Missing test for the summary line.** Assert `Workers whose contract_weekly_basic was ignored: 1` in report.md.
3. **Unmasked worker ID in the new error** (`ingest/loader.py:256`). The message prints the worker ID in full, `({wid})`. Existing loader messages do the same (`duplicate settings for {wid}`, `leave for worker '{wid}'`), so this branch is consistent with them. FORMAT.md L7, however, says error messages never print a full `worker_id`. Either mask the ID in every loader message or correct the doc. This needs a separate small task.
4. **FORMAT.md L25 wording.** "variable_hours: ignored" is not true for a negative or malformed value: it still exits 2 through the general money-format rule. Suggested wording: "ignored if it is a valid amount".
5. **Brief figure.** The builder quoted 11/30 false positives; the test's own scan gives 12/30. The test only asserts at least 5, so it still passes. Use 12/30 in any digest or decision entry.
