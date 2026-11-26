# T-150 review: cap look-back sections in report.md (fix for T-149 security L-1)

Branch: `p/holiday-pay-payroll-lookback-audit/T-150` (commit 7fdd406), diff `git diff main...HEAD`.
Files: `report/builder.py` (+81/-7), `tests/test_t150.py` (new, 99 lines), `README.md`, `ingest/FORMAT.md`.
Reviewer: reviewer agent, 2026-11-26.

## Summary

The fix does what L-1 asked. Look-back detail sections are now capped at 20 per worker and 500 in total. Rows are picked by priority (largest underpayment, then cannot-check, then largest overpayment, then £0.00 guessed-rate), kept rows still print in file order, `and K more` lines cover the first 50 affected workers, and one combined line covers the rest. `exceptions.csv` is still complete. Escaping goes through `_md` for worker IDs and flag names. Week ranges are ISO dates only. The rolled-up caps and their path are not touched. Goldens and every existing test pass, so small inputs give the same report as before.

Two wording and placement bugs show up when the cap is hit. Both are in text an adviser reads as a factual statement about the payroll, so I am asking for them to be fixed before merge. Both are small.

### Evidence

- Full suite, run from the product folder: `python3 -I -m unittest discover -s tests -t .` gave `Ran 325 tests in 47.357s` and then `OK`.
- The T-149 L-1 repro shape (50 fixed_pay workers, no contract basic, 1,500 weeks each, every other week a leave week, 37,500 exceptions). On main this gave a 52,189,874-byte report (T-149). On this branch: `report.md` is **1,206,366 bytes** with 550 `###` headings (500 detailed sections plus 50 summaries). `exceptions.csv` is 5,828,051 bytes and complete. The run took 22.3 s. The longest line is 9,355 bytes: a summary's week-range list of 730 single weeks.
- Selection probe (1 worker, 30 guessed-rate leave weeks: 22 at -£100 and 8 at £0.00). The 20 kept sections are all -£100 overpaid weeks, printed in file order. The summary says `2 overpaid, £200.00 in total; 8 at £0.00 with a guessed weekly rate`, which matches `exceptions.csv` row for row.

### Size bound

The bound holds. Detailed sections are fixed at 500 look-back plus 500 rolled-up. What is left is the per-worker week-range list in at most 50 + 50 summary lines. Its length is limited by the accepted date range (2000-01-01 to 2100-12-31) and by the one-weekday-per-worker rule. In the worst case, alternate weeks across the whole range, that is about 2,635 single dates, or about 32 KB per line. So the whole report stays in the low single-digit MB at worst, against 52 MB before. That is acceptable, though capping the list would be neater (suggestion S-1).

## Critical issues (must fix)

1. **The bucket labels in the `and K more` line are wrong when `--include-flagged` is used.** `report/builder.py:419-432` (`_lookback_more_line`) puts every row that is not under, over or cannot-check into the bucket "at £0.00 with a guessed weekly rate". It also counts any `difference > 0` as "underpaid", even inside the threshold. With `--include-flagged`, an exception can be a £0.00 row whose only flag is, say, `leave_week_without_holiday_pay` (no guessed rate), or a +£0.004 row. Probe output:
   `1 underpaid, £0.00 in total; 1 at £0.00 with a guessed weekly rate. Flags: holiday_pay_week_not_in_leave_file: 1, leave_week_without_holiday_pay: 1.`
   Neither row had a guessed rate, and "1 underpaid, £0.00" contradicts the summary block, which counts underpaid only above the threshold (`builder.py` `write_outputs`, `under = ... > threshold`). This matters because report.md is the document the adviser signs off, and it states something about the data that is false.
   **Fix:** pass `threshold` into `_exception_sections` and then `_lookback_more_line`. Classify under and over with `> threshold` / `< -threshold`, as the summary does. Split the remaining rows into "£0.00 or within threshold with a guessed weekly rate" (`always_exception(r)`) and "within threshold, listed for a flag (--include-flagged)". Apply the same rule in `_lookback_priority` (`builder.py:393-401`) so that sub-threshold rows do not outrank cannot-check rows. Add a test that uses `include_flagged`.

2. **Look-back `and K more` lines print after the rolled-up detail sections.** `builder.py:449-473`: the loop writes the look-back details, then the rolled-up details (look-back rows come first in `exceptions`), and only then the look-back summaries (`lb_items`, line 464). In a mixed firm, the report reads `### F000, week ending ...` x20, `### R1, pay week ending ... (rolled-up holiday pay)` x3, `### F000: and 10 more look-back exception(s)`, followed by "Not written out above ...". The F000 summary sits under R1's sections, so it is easy to misread or miss. That was confirmed with a probe (1 fixed_pay worker with 30 exceptions plus 1 rolled-up worker with 3).
   **Fix:** write the look-back summary lines straight after the look-back loop, before any rolled-up section. For example, loop over `lb` first and then over the rolled-up rows, or build the two lists separately and join them in this order: look-back details, look-back summaries, rolled-up details, rolled-up summaries. Add a CLI test with both worker kinds that checks the order of the headings.

## Suggestions (non-blocking)

- **S-1** Cap the week-range list in both the look-back and rolled-up `and K more` lines (`builder.py:438` and `:480`), for example first 10 ranges then `and N more ranges`. In the probe, each of 50 lines was 9.3 KB of dates. That makes up 40% of the 1.2 MB report and is unreadable anyway. `exceptions.csv` already has every week.
- **S-2** The combined line for workers after the first 50 (`builder.py:469-473`) reports only the underpaid total. Add the underpaid count and the cannot-check count, so that uncheckable weeks are never invisible in report.md (see the playbook rule "never silently dropped").
- **S-3** The first 50 summary workers are chosen in worker-ID order, not by size of underpayment. When more than 50 workers overflow, the workers with the largest hidden underpayments can end up in the anonymous combined line. Consider ordering `lb_items` by hidden underpaid total, largest first.
- **S-4** Tests: `test_total_cap_and_size_bound` uses 30 leave weeks per worker. Add the L-1 repro shape at a reduced scale (for example 50 workers x 400 weeks) so the size test also covers long week-range lists. `test_small_input_not_capped` should also assert `code == 0`.
- **S-5** `_lookback_more_line` needs a docstring. The rolled-up summary text and the look-back summary text now repeat the "at most N per worker and M in the whole report" sentence. A small shared helper would stop them drifting apart.

## Docs

The README and FORMAT.md wording is accurate for the default run: the caps, the priority order and `exceptions.csv` staying complete. Once item 1 is fixed, change "£0.00 guessed-rate weeks" in the README to include the `--include-flagged` bucket as well.

## Security / performance

No new input reaches markdown without `_md`. No new I/O. Selection is one sort, O(E log E), over the look-back exceptions. There is no AI or network cost.

Verdict: CHANGES
1. Fix the `and K more` bucket classification (threshold-aware under/over; do not call non-guessed-rate rows "guessed weekly rate") and align `_lookback_priority`; add an `--include-flagged` test (`report/builder.py:393-432`).
2. Emit look-back `and K more` lines before the rolled-up detail sections; add a mixed-firm heading-order test (`report/builder.py:449-473`).

## Re-review (commit 730ae28, `git diff 7fdd406..HEAD`)

Tests: `python3 -I -m unittest discover -s tests -t .` gave `Ran 329 tests in 52.883s` and then `OK`. That is 4 new tests in `ReviewFixes`, and the existing goldens are unchanged.

1. **Item 1 is fixed.** `_lookback_bucket(r, threshold)` now drives both `_lookback_priority` and `_lookback_counts`. Underpaid and overpaid use `> threshold` / `< -threshold`, the same rule as the summary block and the `audit()` exception filter. Rows within the threshold are split into "guessed" (`always_exception`) and "flagged". I re-ran my earlier probe (a £0 row with `leave_week_without_holiday_pay`, a +£0.004 row and a £0 row with `no_basic_pay_found`, threshold 0.01). It now reads `1 within £0.01 with a guessed weekly rate; 2 within £0.01, listed for their flags`, with no false "underpaid". The `threshold` is passed from `write_outputs` into `_exception_sections`.
2. **Item 2 is fixed.** `_exception_sections` now returns `_lookback_sections(...) + _rolled_up_sections(...)`, so each kind's summaries follow its own details. This is covered by `test_lookback_more_line_before_rolled_up_sections`. `audit()` already put look-back exceptions before rolled-up ones, so reports with no capped rows are unchanged (the goldens pass).
3. **The suggestions are in.** S-1: `MAX_SUMMARY_RANGES=10` applies to both kinds. On the L-1 repro (37,500 exceptions) report.md is now **769,666 bytes** (it was 1,206,366 after the first fix and 52 MB on main), with 550 headings and the longest line 501 bytes. S-2: the combined line uses `_lookback_counts`, so cannot-check rows are counted. S-3: the summary workers are sorted by hidden underpaid total with a stable sort, so ties keep file order (tested). S-4: there is a long-history size test (55 workers x 400 weeks, under 1 MB, and it checks the range cap), and `code == 0` is asserted. S-5: docstrings and `_cap_text` are added.

Nits (non-blocking):
- The README sentence "each `and K more` line names at most 10 week ranges, and likewise at most 20 detailed rolled-up sections..." reads as if the range cap were part of the look-back list. Consider splitting it into two sentences.
- `ingest/FORMAT.md` (T-130 paragraph) does not mention the 10-range cap in `and K more` lines.

Verdict: PASS
