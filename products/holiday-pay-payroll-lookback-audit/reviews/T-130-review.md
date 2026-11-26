# T-130 review: fixes for T-128 QA (F1-F3) and T-129 security (L-1, I-1, I-2)

Reviewer: reviewer agent, 2026-11-26. Branch `p/holiday-pay-payroll-lookback-audit/T-130` at `39fb05d`, diff `git diff main...origin/p/holiday-pay-payroll-lookback-audit/T-130` (8 files, +246/-29). Worktree `/tmp/claude-0/rev-t130` (now removed). Probes in the reviewer scratchpad. No product code was edited.

**Tests:** `python3 -m unittest discover -s tests -t .` gives **Ran 281 tests, OK** (269 at T-129, plus 12 in `tests/test_t130.py`).
**Untouched:** `git diff --stat main...HEAD -- mapper benchmark` is empty.

## Summary

| Finding | Fix | Result |
|---|---|---|
| F1 header-only leave.csv refused | `leave_empty` decided after workers.csv; accepted if any `irregular_rolled_up` worker | Works, but **the condition is too broad** (C-1) |
| F2 idle rolled-up worker / leave week missing from history invisible | `rolled_up_idle`, `rolled_up_leave_missing`, report notes, stdout `note:` lines | Works; idle note text is wrong in one case (S-1) |
| F3 BOM echoed in masked error | `_mask` strips 5 invisible code points, says so | Works for BOM/ZWSP/ZWNJ/ZWJ/WJ; other invisibles still echo (S-3) |
| L-1 uncapped rolled-up sections | at most 20 detailed sections per worker, then one `and K more` section with flag counts and week ranges | Math correct; cap is per worker, not global (S-4) |
| I-1 FORMAT.md masking list | lists all 8 columns | Correct |
| I-2 `explain_rolled_up` escapes nothing by default | `esc=md_escape` default; `_md` is now an alias of it | Correct, no double escaping |

Specific checks asked for:
- **stdout line 1** is still `len(lb_rows)` / `len(lb_exc)` from `split_rows`, so it counts look-back rows and exceptions only (T-127 contract holds). Line 2 now also prints when rolled-up workers exist but produced 0 rows (`0 rolled-up pay weeks checked, 0 exceptions.`), which is the right signal. New `note:` lines come after line 2.
- **Cap math** (`builder.py:364-384`): `shown[wid]` counts up to `MAX_ROLLED_UP_DETAILS` per worker; the rest go into `more[wid]`; the summary counts `len(rs)` exceptions and deduplicates weeks for the ranges (a week can carry both a `check_week` row and a `holiday_pay_row`). Look-back exceptions are never capped. `test_cap_is_per_worker` (25+25 -> 40 sections, `and 5 more` each) confirms. exceptions.csv stays complete (`test_report_capped_csv_complete`).
- **Escaping**: the only caller passes `_md`, which is `md_escape`, applied once. The new `and K more` heading escapes `wid` and flag names once each; idle and leave-missing notes escape IDs once. No double escaping found. `test_audit.py:126` still pins `_md`.
- **Loader paths**: 0-byte leave.csv still exits 2 (`file is empty`); a leave.csv with a broken header still exits 2 (issue on lname, so `leave_empty` is False); no workers.csv -> refused; invalid `worker_type` for the only rolled-up candidate -> refused (worker_type never set); rolled-up settings for a worker not in history -> refused; header plus blank lines behaves like header-only. Issue ordering changed (the `no data rows` line now prints after workers.csv errors): cosmetic only.

## Critical issues

### C-1 A header-only leave.csv is accepted for a mixed firm, and the look-back population is then silently clean
`ingest/loader.py:284-286` accepts an empty leave.csv when **any** worker is `irregular_rolled_up`. A firm with 1 rolled-up worker and 40 variable-hours workers whose leave export came out empty now gets exit 0 and `0 leave weeks checked, 0 exceptions.` with no warning. Before T-130 this was refused with `no data rows`.

It also hides holiday pay. `unlisted_holiday_pay` (`builder.py:34-45`) only looks at workers that have leave rows, so with an empty leave.csv no "holiday pay recorded but no leave row" warning can appear. Repro:
```
history: R1,2025-06-07,basic,400 / R1,2025-06-07,rolled_up_holiday_pay,48.28 /
         V1,2025-06-07,basic,400 / V1,2025-06-14,holiday_pay,400
leave.csv: header only;  workers.csv: R1,irregular_rolled_up
-> exit 0; "0 leave weeks checked, 0 exceptions." / "1 rolled-up pay weeks checked, 0 exceptions."
   report.md: no warning of any kind about V1's holiday_pay week.
```
This contradicts the README's "holiday pay not in leave.csv ... never silently dropped". F1 asked for the case where a firm has **only** rolled-up workers. The comment at line 284 ("when rolled-up workers have pay weeks to audit") also does not match the code, which only checks the type.

**Fix:** accept a header-only leave.csv only when every loaded worker is `irregular_rolled_up`. Otherwise keep exit 2 with the current message reworded ("... only when every worker in history is set as irregular_rolled_up in workers.csv"). Update FORMAT.md, README and the line-284 comment to match. Add a regression test with the mixed repro above (expects exit 2 and `no data rows`). A softer alternative is to stop exiting and instead add a stdout `note:` plus a report.md warning that lists the non-rolled-up workers that have `holiday_pay` rows. This review recommends the strict rule.

## Suggestions (non-blocking)

- **S-1 The idle note can be wrong.** `builder.py:353` says idle workers had "no pay that counts, no rolled_up_holiday_pay and no holiday_pay row in any week". But `check_week` also returns None for a week in a pre-2024 leave year that has pay that counts and no rolled-up row. Repro: R1 `irregular_rolled_up` with `basic 400` on 2023-06-03 and 2023-06-10 prints the note with "no pay that counts", which is false. Reword it to: "no week that the rolled-up check applies to (no pay that counts, or only leave years before 2024 with no rolled_up_holiday_pay)". Or give the pre-2024 case its own message.
- **S-2 Notes go to two different streams.** The new `note:` lines go to stdout (`audit.py:70-74`), while the existing `contract_weekly_basic ignored` note goes to stderr (`audit.py:57`). Pick one stream, document it in README, and say which lines a script should parse.
- **S-3 More invisible characters.** `_INVISIBLE` (`loader.py:18`) leaves out U+200E/U+200F (directional marks), U+00AD (soft hyphen), U+202A-U+202E and U+2066-U+2069 (bidi controls). Probe: an `amount` cell of `<U+200E>1` is echoed with the mark inside the 2 characters shown. Use `unicodedata.category(c) == "Cf"` instead of a fixed list.
- **S-4 The cap is per worker only.** 3,000 rolled-up workers each with 100 flagged weeks still produce 60,000 sections (about 20 MB by estimate, down from 214 MB). Rows are also still held in memory and `md` is still joined in one string (T-129 L-1 fix items 3 and the memory half). Consider a global cap, or a per-worker one-line range summary for workers whose exceptions are all rule flags (T-129 L-1 fix item 1). Track this as a follow-up and do not block on it.
- **S-5 Test tightening.** `test_no_note_when_nothing_to_say` does not assert `code == 0`. `assertIn("and ", rep)` in `test_report_capped_csv_complete` is trivially true. Add a test for the pre-2024 idle case (S-1). Add a test that the `and K more` summary's flag counts add up to K.
- **S-6** `md_escape` lives in `rolled_up.py` and `builder.py` aliases it. It would sit better in a small `report/markdown.py`. Cosmetic.

## Verdict: CHANGES

Blocking: C-1. A header-only leave.csv must be refused unless every worker is `irregular_rolled_up`, with a mixed-firm regression test. F2, F3, L-1, I-1 and I-2 are fixed correctly. Stdout line 1 still counts look-back exceptions only. The cap math is right and nothing is escaped twice. S-1 is a one-line wording fix and should go in the same change.
