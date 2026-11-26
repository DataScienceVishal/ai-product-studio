# T-131 review: global report.md cap (T-130 S-4), S-1 wording, retention wording (T-120 L-5)

Reviewer: reviewer agent, 2026-11-26. Branch `p/holiday-pay-payroll-lookback-audit/T-131` at `dfad741`, diff `git diff main...FETCH_HEAD` (4 files, +45/-6: README.md, ingest/FORMAT.md, report/builder.py, tests/test_t130.py). Fresh worktree `/tmp/claude-0/rev-t131` (now removed). No product code was edited.

**Tests:** `python3 -m unittest discover -s tests -t .` gives **Ran 286 tests, OK** (284 + 2 new). `mapper/`, `benchmark/` and `engine/` are untouched.

## Summary

| Item | Result |
|---|---|
| Global cap of 500 rolled-up sections (`builder.py:366-391`) | **Math correct** |
| 50 per-worker summaries, then one combined line | **Math correct** |
| S-1 wording: "leave years starting before 1 April 2024" (`builder.py:356`) | **Correct, not off by a day.** It is the exact complement of `accrual_applies` (`engine/accrual.py:7,13`: starting on or after 2024-04-01). It matches `FLAG_TEXT[BEFORE_2024]`, the `rolled_up.py` docstring and FORMAT.md:30 ("before 2024-04-01"). I grepped every "2024" in README, FORMAT, report/ and engine/accrual.py: none says "after 1 April" or "from 31 March". |
| Retention wording (DRAFT) | Accurate about the tool. One README overstatement (S-1 below). |
| Docs for the new cap | **Not updated** (C-1) |

**Cap math, checked independently.** I ran a probe that copies `test_total_cap_across_workers`: 80 workers x 30 flagged weeks, 2,400 exceptions.
- report.md has exactly 500 detailed sections. The first 25 workers get 20 each, and `total` stops the rest.
- There are 50 per-worker summaries covering 1,000 exceptions: R000-R024 have 10 more each, and R025-R049 have 30 each (0 shown).
- One combined line reads `and 900 more ... for 30 further worker(s)`.
- 500 + 1,000 + 900 = 2,400 = the number of rows in exceptions.csv.
- report.md is 216 KB, and only `exceptions.csv` and `report.md` are left in `out/` (no `.tmp` or `.bak` files).

Look-back exceptions are still never capped, which is correct. The size is now bounded: 500 sections, plus 50 summary lines whose week ranges are bounded by the 2000-2100 date range, plus 1 combined line.

**Retention claims checked against the code:**
- "Keeps nothing beyond the two output files": `_atomic_write_pair` uses `mkstemp` in `out/` and removes its temp and backup files. The probe left no leftovers.
- "No network calls": stdlib only, and nothing in the code imports a network module.
- "No logs of values": stderr messages are masked.

## Critical issues

### C-1 The user-facing docs still describe the old per-worker-only cap
- `ingest/FORMAT.md:38` still says report.md shows "at most 20 detailed sections per rolled-up worker, then one line `and K more` with the flag counts and week ranges". That is now false in two ways:
  - after 500 sections in total, later workers get **0** detailed sections;
  - from the 51st worker that has a remainder, there is no per-worker line at all, only one combined line with no flag counts or week ranges.
- `README.md:25` ("at most 20 detailed rolled-up sections per worker") has the same problem.
- The `_exception_sections` docstring (`builder.py:367`) has the same problem.

The task was to make the wording accurate, and FORMAT.md is the document a customer's payroll person reads.

**Fix:** change FORMAT.md:38 and README.md:25 to say: "at most 20 detailed sections per rolled-up worker and 500 in the whole report; then an `and K more` line (flag counts and week ranges) for each of the first 50 workers with more, and one combined line for any further workers; exceptions.csv always lists every exception." Update the docstring to match.

## Suggestions (non-blocking)
- **S-1** `README.md:14` says "any hosted version **deletes** inputs within 30 days". That states a commitment for a product that does not exist yet as if it were fact. FORMAT.md says "**must** delete". Use "must" in README too, so the DRAFT reads as a requirement.
- **S-2** A worker cut off by the global cap gets a heading `### R030: and 30 more rolled-up pay exception(s)` with no detailed section above it. "R030: 30 rolled-up pay exception(s) not written out" would read better when the worker has 0 shown.
- **S-3** `test_total_cap_across_workers` checks the 500 count and that the combined line exists, but not the numbers. Asserting `and 900 more ... for 30 further worker(s)` and 50 per-worker headings would pin the math (the probe above shows the values).
- **S-4** `RetentionDocs` only checks that the strings appear. That is fine for a docs guard.

## Verdict: CHANGES

Blocking: C-1. Update FORMAT.md:38, README.md:25 and the `_exception_sections` docstring to describe the 500-section global cap and the 50-summary limit. This is a documentation-only change. The code, the cap math, the "before 1 April 2024" wording and the retention claims about the tool are correct, and 286 tests pass. S-1 (README "must delete") should go in the same change.

## Re-review at f84e408 (delta dfad741..f84e408)

The delta is docs and a docstring only: README.md, ingest/FORMAT.md, and the `report/builder.py` docstring. No code logic changed. Fresh worktree `/tmp/claude-0/rev-t131b` (now removed). **Tests: Ran 286 tests, OK.**

- **C-1: fixed.** FORMAT.md:38, README.md:25 and the `_exception_sections` docstring now all describe the same behaviour:
  - at most 20 detailed sections per worker and 500 in total;
  - an `and K more` line for each of the first 50 affected workers;
  - one combined line for the rest;
  - exceptions.csv is never capped.

  This matches the code and the probe above (500 / 1,000 / 900 = 2,400).
- **S-1: fixed.** README now says hosted versions "must delete uploaded inputs within 30 days", which matches FORMAT.md.
- S-2 and S-3 were not taken. They are minor and do not block: the heading reads oddly for a worker with 0 sections shown, and the cap test does not assert the exact numbers.

## Re-review verdict: PASS
