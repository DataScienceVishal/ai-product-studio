# T-134 review: test hygiene, fullmatch regexes, Leave years summary line

Branch: `p/holiday-pay-payroll-lookback-audit/T-134` at a622b05, diffed against main (7c556d4).
Reviewer: reviewer agent. Verdict: **PASS**

## Summary

The diff stays in scope: 10 files, +92/-17. Nothing under `mapper/` or `benchmark/` changed, and no golden file changed.

- **Test hygiene:** `open(...).read()` became `with` blocks in `tests/test_t124.py` and `tests/test_t130.py`. The only bare `open(` left in tests is `tests/test_mapper.py:409` (`open(...,"w").close()`), which closes the file at once and does not warn.
- **Regexes:** `_MMDD` and `_DATE` in `ingest/loader.py` dropped their `^...$` anchors and are now called with `.fullmatch`. They have no other callers.
- **Rename:** `_leave_year_start` became `leave_year_start_date`, and all four call sites were updated (engine/lookback.py, report/builder.py, report/rolled_up.py x2). No other reference to the old name remains.
- **New summary line:** `report/builder.py` `_leave_years_line` sits after "Workers with flags" in the report.md summary.
  - It lists only workers whose start is not (4, 1), sorted by worker_id, and shows the first 20 followed by `and K more`.
  - Each ID goes through `_md` (= `md_escape`).
  - The line returns None, so it is left out, when every worker uses the default or when `starts` is None or empty.
  - The new `write_outputs` keyword defaults to None, so existing callers are unaffected.
- **Test tightenings in test_t127.py:**
  - The explicit-04-01 test now also compares `report.md` with `main_report.md`. It passes, so the "line omitted when all default" claim is backed by a golden.
  - The Counts sample test now also asserts `(code, se) == (0, "")`.

## Test evidence (clean worktree at a622b05, run from the product dir)

| Command | Branch | main (7c556d4) |
|---|---|---|
| `python3 -I -m unittest discover -s tests -t .` | Ran 291 tests, OK | Ran 286 tests, OK |
| `python3 -I -X dev -W error::ResourceWarning -m unittest discover -s tests -t .` | Ran 291, OK, **0** ResourceWarning lines | Ran 286, OK, 12 ResourceWarning lines (unraisable, so not fatal) |

There are 5 new tests: TrailingNewline x1 and LeaveYearsSummary x4.

I also called `_leave_years_line` directly:
- `{'W10':(1,1),'W2':(10,1),'A_b-c.d':(12,31),'X':(4,1)}` gives `- Leave years: 1 April unless set; A\_b\-c.d: 31 December, W10: 1 January, W2: 1 October`. The default worker X is left out and the ID is escaped.
- 21 workers gives `..., W19: 1 January, and 1 more`.
- `{}` and `None` both give None.

## Cap, escaping, injection, ordering

- **Cap:** correct. It slices `odd[:20]`, and `more = len - 20` is appended only when it is above 0. The test checks that exactly 20 are shown, W020 is in and W021 is out, and the line ends with `, and 5 more`.
- **Markdown injection:** IDs are already limited by `_ID`, which only allows `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`, and `md_escape` also escapes `_` and `-`. A worker ID cannot carry HTML, links, pipes or newlines into report.md.
- **Formula injection:** not applicable. The line only goes into report.md, not exceptions.csv. In any case `_ID` forces an alphanumeric first character, so `= + - @` can never lead.
- **Ordering:** deterministic but lexical (`W10` sorts before `W2`). This matches how the rest of the report orders IDs. Fine (see S2).
- **Dates:** the month and day come from `_leave_year_start_value`, which already validated them as a real date, so `_MONTHS[s[0]-1]` cannot go out of range.

## Docs accuracy

- **README:** "Non-default start dates are named in a `Leave years:` line in the `report.md` summary (omitted when all are 1 April)". Accurate.
- **FORMAT.md:**
  - The example `Leave years: 1 April unless set; W006: 1 January` matches the real format; the report adds a leading `- ` bullet.
  - "first 20, then `and K more`" is accurate. The "first" 20 are by sorted worker_id.
  - "when every worker uses 1 April the line is left out" is accurate.
  - The earlier sentence still holds: with no column, report.md is identical apart from the two T-127 count lines. The new line is left out in that case, and the `main_nw_report.md` / `main_report.md` golden comparisons prove it.
  - There are no "byte-identical" style over-claims.

## `_MONEY` / `_ID` with `^...$` and `.match`

These don't matter in practice. `_rows` strips every cell (`c.strip() for c in rec`, loader.py:136) before any validator runs, so a cell can never end in `\n` and `$` accepting a trailing newline cannot be reached. The same applies to `_DATE_ID` (loader.py:29), and to `_MMDD` and `_DATE` before this change. Moving them to `fullmatch` is defence in depth, not a bug fix.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1:** For consistency, move `_MONEY`, `_ID` and `_DATE_ID` to `fullmatch` and drop their anchors, so no validator depends on the caller stripping first. Low priority, since cells are always stripped.
- **S2:** If firms use unpadded IDs (W2, W10), a natural sort would read better. It only matters cosmetically, and only beyond 9 workers.
- **S3:** `test_ids_are_escaped` uses `<b>x`, which `_ID` would reject at load. A realistic ID such as `W_1-a` asserting `W\_1\-a` would test the escaping that can actually happen.
- **S4:** No end-to-end test covers the 20 cap through the CLI; it is only unit-tested via `_leave_years_line`. That is acceptable because the wiring is covered by `test_lists_only_non_default_workers`.

## Verdict

**PASS.** In scope, tests are green (291/291 with and without `-X dev -W error::ResourceWarning`), there are no ResourceWarnings left (main had 12), the goldens are unchanged and still truthful, and the docs are accurate.
