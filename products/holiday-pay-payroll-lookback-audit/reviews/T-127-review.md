# T-127 review: per-worker leave_year_start, distinct rolled-up counts, stdout, BRIEF nits

Branch `p/holiday-pay-payroll-lookback-audit/T-127`, head 5ba1570, base main 7843483. Reviewer (opus).

## Verdict: CHANGES

The code is correct. Two small fixes are needed before merge: a test that does not protect one of the three leave-year uses, and a documentation claim that is false.

## Summary

- Adds `leave_year_start` (MM-DD, default 04-01) to workers.csv (`ingest/loader.py`). It is passed to the look-back first-4-weeks count (`report/builder.py:73-74`), the `holiday_pay_week_not_in_leave_file` check (`builder.py:75`), and the rolled-up checks (`report/rolled_up.py` `check_week` and `holiday_pay_row`, which are passed `w.leave_year_start` in `audit_rolled_up`).
- `rolled_up_weeks_checked` counts distinct (worker, week) pairs. holiday_pay rows are now their own group in the report.md breakdown. stdout line 1 counts look-back exceptions only.
- Diff against main for `engine/`, `mapper/` and `benchmark/`: empty (`git diff main...5ba1570 --stat` shows nothing under those paths).

## Evidence

- Full suite on the branch tree (scratch worktree, product dir, `python3 -I -m unittest discover -s tests -t . -v`): **Ran 268 tests, OK**. Main: 251 tests, OK.
- CLI on the samples with `--workers`: main prints `5 leave weeks checked, 12 exceptions.` / `13 rolled-up pay weeks checked, 8 of the exceptions are rolled-up pay.`. The branch prints `5 leave weeks checked, 4 exceptions.` / `13 rolled-up pay weeks checked, 8 exceptions.`. exit 0.
- Without `--workers`: `6 leave weeks checked, 4 exceptions.` on both. `diff -r` of the outputs is empty.
- Branch vs main output, with `--workers`: exceptions.csv is byte-identical. report.md differs only on lines 18-19, which are the intended count lines:
  ```
  < - Rolled-up pay weeks checked: 13
  < - Rolled-up pay exceptions: 8 (6 rule flags, 2 differences from 12.07% of pay that counts)
  > - Rolled-up pay weeks checked (worker-weeks, each counted once): 13
  > - Rolled-up pay exceptions: 8 (5 rule flags, 2 differences from 12.07% of pay that counts, 1 holiday_pay week(s) paid to a rolled-up worker)
  ```
- How the goldens were made: `tests/golden/main_exceptions.csv`, `main_nw_exceptions.csv` and `main_nw_report.md` are byte-identical to main's real output. `main_report.md` is **not** main's output. It is the branch output, with the two lines above. The content is right, but the name and the test docstring are wrong (see C2).
- 01-01 run on the samples (every worker set to `01-01`): exit 0, `13 rolled-up pay weeks checked, 10 exceptions.`. W006 2024-04-06 and 2024-04-13 become `rolled_up_before_2024_rules` (they were recalculated as correct under 04-01). Every "leave year starting" line moves to 2024-01-01 / 2025-01-01. This is correct, and it is the demo-relevant case the task was for.
- Boundary maths (`engine/lookback.py:32`, unchanged): `d >= date(d.year, m, d)`. A week ending on the start date belongs to the new year. I checked: start 03-01 with week 2024-02-29 gives 2023-03-01. Start 02-28 with 2024-02-29 gives 2024-02-28. Start 02-28 with 2025-02-28 gives 2025-02-28. Start 12-31 works. `02-29` is refused through `date(2023, m, d)`. `00-00`, `12-32`, full-width digits and a leading or trailing space are refused (cells are stripped before this check anyway).
- Validation messages: `_mask` shows the first 2 characters and the length. The tests assert the full cell is absent (`SECRET-CELL-VALUE-123`) and check line numbers on row 3.
- Mutation check (8 mutants, full suite each):

  | Mutant | Result |
  |---|---|
  | M2: look-back gets 4/1 | caught |
  | M3: check_week uses 4/1 | caught |
  | M5: audit_rolled_up drops the start | caught |
  | M6: leap-year date(2024) in validator | caught |
  | M7: distinct count becomes len() | caught |
  | M8: `>=` becomes `>` at the boundary | caught |
  | **M1: unlisted holiday_pay check uses 4/1** | **survives** |
  | M4: holiday_pay_row drops the start | survives, but equivalent: the field is never output (explain_rolled_up does not print it for HOLIDAY_PAID rows) |

## Critical issues (must fix)

**C1. `holiday_pay_week_not_in_leave_file` with a custom start has no test that can fail.** `tests/test_t127.py` `FirstFourWeeks.test_unlisted_holiday_week_flag_uses_the_workers_year`
- Why it matters: this is one of the three uses T-127 had to deliver. The test checks two cases. With 01-01 and an unlisted week of 2024-12-25, no flag is expected. With 04-01, a flag is expected. The old hard-coded `_leave_year_start(d, 4, 1)` gives the same answer in both cases, so mutant M1 passes all 268 tests. A regression back to 1 April would go unseen.
- I ran a case that tells the two apart. Worker `01-01`, unlisted `holiday_pay` in week 2025-02-05, leave week 2025-03-12. The branch flags the leave week (`shortened;leave_week_without_holiday_pay;holiday_pay_week_not_in_leave_file`). M1 drops the flag. So the code is right and only the test is weak.
- Fix: add that positive case, or any case where the unlisted week falls between the custom start and 1 April. Assert the flag appears with 01-01 and does not appear with 04-01.

**C2. Two false claims of byte-identical output.** `ingest/FORMAT.md` (leave_year_start paragraph) says "With no column the outputs are byte-identical to earlier versions". The `tests/test_t127.py` `DefaultUnchanged` docstring says the goldens are "byte-identical to those of main before T-127".
- Why it matters: in this same release, report.md changes for any run with rolled-up workers (the two count lines above). Adviser-facing docs must not claim something that is not true. `golden/main_report.md` also has a misleading name.
- Fix: in FORMAT.md, say exceptions.csv is unchanged and report.md is unchanged apart from the T-127 count lines. Correct the docstring. Optionally rename the goldens (for example `default_*`) and add a comment saying `main_report.md` is main's output plus the two T-127 count lines.

## Suggestions (non-blocking)

1. **gc.collect() in `run()`** (`tests/test_t127.py:28`). This is acceptable as a stopgap. It frees the leaked sockets before stderr is captured, so `assertEqual(se, "")` cannot flake when GC happens to run during `cli.main`. The warnings still go to the runner's real stderr: 2 `unclosed <socket ...>` warnings show up in the verbose output, against 0 on main.
   - Root cause: `tests/test_mapper.py:885-886` calls `first.shutdown()` / `second.shutdown()` without `server_close()`. That is a two-line test-only fix (the file is in tests/, not mapper/).
   - Raise a follow-up task to fix it, then drop the gc.collect() call. Three pre-existing `unclosed file` warnings in `tests/test_t124.py:18` (`open(...).read()`) are also worth fixing.
2. `_MMDD` uses `^...$`, which also matches a trailing `\n` (`'01-01\n'` gives (1, 1)). This is harmless because cells are stripped. `re.fullmatch` or `\Z` would be stricter. `_DATE` has the same pattern.
3. `test_explicit_04_01_for_everyone_equals_default` compares only exceptions.csv. Also compare report.md against the golden.
4. `test_no_rolled_up_line_without_rolled_up_workers` does not assert the exit code or empty stderr. That is cheap to add.
5. The report has no place that states which `leave_year_start` each worker used, apart from the "leave year starting YYYY-MM-DD" lines. An adviser reviewing a 01-01 run might want one summary line such as "Leave years: 1 April unless set; W006: 1 January". This is optional.
6. The `audit.py` import line is now very long. Cosmetic.

## Docs check

- BRIEF.md: the Exception definition now covers `cannot_check` and holiday_pay rows. The note that data the engine rejects exits 2 has been added. The demo lines match the actual stdout. Accurate.
- README.md / FORMAT.md counts section: matches the observed stdout and report lines. Apart from C2, the leave_year_start rules match the code: 02-29 refused, start-date week goes to the new year, the 01-01 example, mid-history change not modelled.
- `rolled_up.py` module docstring updated. Accurate.

## Cleanup

Scratch worktrees (branch and main) removed. `git worktree list` shows only the main checkout. I made no product code edits.

## Re-review at f06e43e: PASS

Diff 5ba1570..f06e43e: `ingest/FORMAT.md` (1 line), `tests/test_t127.py`, `tests/test_mapper.py` (+2 lines), and this review file. `git diff main...f06e43e --stat` for `engine/`, `mapper/` and `benchmark/`: empty. No production code changed since the first review.

- **C1 fixed.** The new test is `FirstFourWeeks.test_unlisted_holiday_week_between_custom_start_and_april_is_flagged`: start 01-01, unlisted holiday_pay in week 2025-02-05, leave week 2025-03-12, flag asserted. In a scratch worktree at f06e43e I changed `report/builder.py:75` back to `_leave_year_start(d, 4, 1)` and ran the full suite: `FAILED (failures=1)`. The only failure is the new test. Reverted, the suite is green. Mutant M1 is now caught. Nit: it does not assert that the flag is absent under 04-01, but the existing test plus the mutant kill cover it.
- **C2 fixed.** FORMAT.md now says exceptions.csv is identical and report.md is identical apart from the two rolled-up count lines changed in T-127. The `DefaultUnchanged` docstring says which goldens are main's real output and that `main_report.md` is main's output plus the two count lines. Both statements are accurate: re-running the samples at f06e43e matches all goldens byte for byte, and the first review showed main vs branch differs only on report.md lines 18-19.
- **Socket leak fixed at the root.** `test_mapper.py` now calls `server_close()` after `shutdown()`, and gc.collect() is gone from `test_t127.py`. Verbose run: 0 `unclosed <socket` warnings. The 3 remaining ResourceWarnings are the pre-existing `unclosed file` ones in `tests/test_t124.py:18` (suggestion 1). They are not blocking.
- **Full suite** (scratch worktree, product dir, `python3 -I -m unittest discover -s tests -t . -v`): **Ran 269 tests, OK**. CLI on samples: `5 leave weeks checked, 4 exceptions.` / `13 rolled-up pay weeks checked, 8 exceptions.` with `--workers`, and `6 leave weeks checked, 4 exceptions.` without. Both exit 0.

Suggestions 2 to 6 from the first review are still open and non-blocking. Scratch worktree removed.
