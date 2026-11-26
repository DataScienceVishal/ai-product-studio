# Review: p/holiday-pay-payroll-lookback-audit/T-154 (commit e2cd507)

Reviewer, 2026-11-26. Diff: `git diff origin/main...origin/p/holiday-pay-payroll-lookback-audit/T-154` (15 files, +175/-59).

## Verdict: CHANGES (small, docs and one regex)

The code is correct and the maths has not changed. But BRIEF.md still tells users `statutory` is a valid category, and the CLI now refuses it with exit 2. The task asked for docs that match, so this blocks. Both fixes take a few minutes.

## Evidence

- **Full suite on the branch tree:** `python3 -m unittest discover -s tests -q` gives `Ran 336 tests in 49.6s, OK` (329 on main plus 7 new tests in `tests/test_t154.py`).
- **Samples, before and after:** I ran `audit.py --include-flagged` on the samples in main's tree (where W003 has `statutory,116.75`) and in the branch's tree (`excluded_week,0.00`). `diff -r` of the two output folders: IDENTICAL. Both runs: 5 leave weeks and 4 exceptions; 13 rolled-up weeks and 8 exceptions.
- **Randomised engine comparison:** 1,500 random workers (variable_hours and fixed_pay, with and without a contract basic, 5 to 110 weeks, holiday_pay part-weeks, 15% marked weeks), 5,225 leave rows. Main's `lookback` got `statutory` with amount 30 to 120. The branch's `lookback` got `excluded_week` with amount 0. paid, due, difference, flags and the `working` dict were byte-identical, with no errors (script: scratchpad `cmp.py`).
- **Why it holds:** `statutory` was never in `COUNTS_FOR_NORMAL`. Its only engine uses were the yes/no tests in `_fixed_pay_refs` (`lookback.py:69,76-77`). Those now test `"excluded_week" not in p`, which matches the old `statutory > 0` because the loader forces the amount to be 0.
- **G6, full worker_id in messages:** all 8 sites security named are now `_mask_id(wid)` (`loader.py:236,249,264,266,268,280,284,301`). I grepped the whole product (`audit.py`, `ingest/`, `report/`, `engine/`, `mapper/`) for f-strings and prints that interpolate a worker ID. There are none left on stderr or stdout. The `_worker_id` validation messages never echo the value. The CLI's `note:` lines print only counts. Engine `ValueError` texts carry no ID. report.md and exceptions.csv still list worker IDs, which is by design (they are the audit output).
- **G1 tests:** `statutory` is refused with a migration message, a non-zero `excluded_week` is refused without echoing the amount, a zero one is accepted and kept in history, and the sample has no `statutory`. The differential and oracle suites were moved to `excluded_week` and write 0 to the CSV.
- **G6 test:** it triggers 6 or more message types and asserts that no full ID appears and that `SE***` does.
- **G8 tests:** the CLI exits 0 and the warning is masked; detection is checked on 6 IDs.

## Critical issues

1. **BRIEF.md is stale and now wrong.** `BRIEF.md:62` lists `statutory` as an accepted category; a user who follows it gets exit 2. `BRIEF.md:70` still describes the rate inference in terms of "non-statutory" and "SSP/SMP" weeks. *Fix:* change line 62 to the current `CATEGORIES` (`excluded_week`, plus the already-missing `rolled_up_holiday_pay`), and use "excluded_week" wording on line 70, as README.md already does.

## Suggestions (should fix in the same pass; not blocking alone)

2. **The G8 regex skips hyphens.** At `ingest/loader.py:85`, `_NAME_LIKE` joins parts with `[._ ]`. `-` is a valid worker_id character, but a space is not (the `_worker_id` rule refuses it). So `john-smith` gets no warning, and the space branch can never match. *Fix:* use `[._-]`, add `john-smith` to `test_detection`, and change FORMAT.md:5 from "`.`, `_` or space" to "`.`, `_` or `-`". You could also say that single-initial forms such as `j.smith` are not caught.
3. **The FORMAT.md:8 sentence is garbled.** The new clause sits between "from any column" and the parenthesised column list, so it reads as if the list belongs to worker_id. It also says worker_id shows "first 2 characters and the length", which contradicts `EM***`. *Fix:* "Error messages never print a full cell value from any column (`worker_id`, ...): they show the first 2 characters and the length ... A `worker_id` quoted in a message about another problem (duplicates, weekday mismatch, missing history) appears as `EM***`."
4. **FORMAT.md:29 grammar:** "a week with not `excluded_week`" should be "a week without `excluded_week`".
5. **Stale test text:** `tests/test_differential.py:14` (docstring) and `:130` (comment) still say `statutory`. `test_edge_cases.py` and `test_t136_oracle.py` pass `excluded_week: 99` and `money(...)` amounts straight into the engine. That is harmless, because the engine tests presence, but those inputs cannot occur through the loader. Using 0 would document the contract.
6. **DATA-DESIGN.md:32 and :59 still describe G1 and G6 as open.** Add "closed by T-154". Security's T-24 list item 8 (G8) also asked for a note in the attestation. Check that it was not dropped.
7. **Short IDs:** `_mask_id` shows a 1 or 2 character ID in full (`W1***`). This matches the existing `_mask` policy and the IDs are pseudonymous, so it is low risk. Consider noting it.
8. **Possibly misleading name:** "excluded_week" does not exclude a week that also has basic or other counting pay. That is the old behaviour and is correct for "maths unchanged", and FORMAT.md:12 says it. Keep it in mind for the adviser brief.

## Accepted as is

The mapper's `statutory_excluded` label is a separate vocabulary for pay-element names. Nothing converts it into a history.csv `element_category`, and it is pinned by the prompt hash. The Lead's acceptance stands.
