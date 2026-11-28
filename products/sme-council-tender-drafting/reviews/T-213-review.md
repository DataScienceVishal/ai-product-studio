# T-213 review: invented limits in A2, report-only deadline

Branch `p/sme-council-tender-drafting/T-213`, commit ce08093, against `main`. Reviewer run, 2026-11-28.

**Verdict: CHANGES** (two small fixes, both in `eval/score.py`; the A2 part is correct and can merge as is once these are done)

1. Dotted times are parsed wrongly, so `time_match` can report True when the time is wrong (see Critical 1).
2. The module docstring names a `deadline_match` that does not exist (see Critical 2).

## Summary

- **A2 invented limits.** Correct and matches the run 0297 (T-213) decision. A null key `word_limit`/`page_limit` with a non-null extracted value adds 1 to `stated` and 0 to `correct`, with `invented: True` on the `wrong` row. A null key `marks`/`weight_pct` with an extracted value goes to `invented_unscored` only. Null against null is ignored. This applies to both question pairs and mandatory pairs.
- **A2 can only go down: checked.** I ran a property check of 3,000 random packs with mixed kinds, nulls and values, comparing `main`'s `score.py` with the branch. In every case `correct` was unchanged, `stated` never fell, the score never rose, `pass` never went from False to True, and A1 and A3 were identical. The only other change is None to 0.0 when every stated field is invented, and that still fails. Script: the scratchpad `prop.py` (not committed).
- **Extractor shape.** `ExtractItem.word_limit/page_limit/marks/weight_pct/deadline` are `Optional` (`app/tender/extract.py` 42-47), and E1 builds `got` from `model_dump()` (`eval/run.py` `_extract`). So a missing limit arrives as `None`, not `0`. The `is not None` test is correct, and an explicit `0` would rightly count as invented.
- **Deadline.** It is report-only: it is not in `BARS` and not used by any `pass` (a test asserts this). All 9 held-out key texts parse to exactly one date and one time (checked: S01, S02, S03, S05, S06, S07, S09, S10, S11). A time is never read as a day ("14:00 on Friday 23 April 2027" gives 23 April, and there is a test for it). Ordinals work ("30th of April", "1st May", "April 30th, 2027"). Numeric dates are day-first as documented; US "04/30/2027" gives month 30, which never matches, so it is a miss, not a wrong hit.
- **Tests.** `pytest tests/test_tender_eval.py -q -p no:warnings`: **132 passed** in 13.7s (fresh venv from `requirements-dev.txt`). The 12 new T-213 tests check behaviour, not internals: exact `stated`/`correct`/`wrong` rows, the mandatory path, the no-flag case for a non-null key, the null/null case, the parser formats including the time-not-day case, and deadline found/not-found/time-mismatch/no-item. `tests/test_tender_pack_keys.py` also passes.
- **Docs.** The EVAL.md A2 and Deadline rows, the dated amendment, and keys README rules 7, 8, 11 and 14 match the code, apart from Critical 2. Rule 9 (page-only questions) is consistent: a word limit converted from pages counts as invented, as rule 1 intends.

## Critical issues

### 1. Dotted times: "5.00pm" reads as 12:00, "17.00" reads as no time (`eval/score.py` 200-201, `_T_HM` and `_T_AMPM`)

`_T_HM` only accepts a colon. `_T_AMPM`'s lookbehind `(?<![\d:])` does not exclude `.`. So in "5.00pm" the regex skips the "5", matches "00pm" with hour 0, and `(0 % 12) + 12` gives **12:00**. Results:

```
parse_deadline_text("5.00pm on 30 April 2027")  -> times {(12, 0)}     # should be (17, 0)
parse_deadline_text("17.00 on 30 April 2027")   -> times set()         # should be (17, 0)
```

**Why it matters.** "17.00" and "5.00pm" are normal UK council style, and EVAL.md says real packs may replace the synthetic ones later. Six of the nine keys have a 12:00 deadline. So an extractor that returns "5.00pm" against a "12:00 noon" key would be reported `time_match: True`. That is a false pass in the one figure this report exists to give. It is report-only and never gates, but a report that is wrong is worse than no report.

**Fix.** Accept `.` as the separator in `_T_HM`, for example `(?<![\d.])(\d{1,2})[:.](\d{2})(?![\d.])`. The guards stop "30.04.2027" from being read as a time; check that against `_D_NUM`. Add `.` to the `_T_AMPM` lookbehind (`(?<![\d:.])`) and let it take an optional `[:.]\d{2}` part, so "5.00pm" gives (17, 0). Add parser tests for "17.00", "5.00pm" and "5.30 p.m.", plus one `score_deadline` case where "5.00pm" against the S01 key gives `time_match is False`.

### 2. Docstring names a non-existent `deadline_match` (`eval/score.py` 22)

The module docstring says the per-pack date check is "(`deadline_match`)". The code has no function or field by that name: the function is `score_deadline` and the field is `found`. EVAL.md readers are pointed at this docstring, so fix the name.

## Suggestions (not blocking)

1. **Tie the date and time to one deadline.** `score_deadline` takes any candidate text that holds the key date. It then checks the time against every time in that whole text, not the time printed next to the date. So "Tenders by 30 April 2027 17:00, clarifications 12:00" reports `time_match: True` against a 12:00 key (reproduced). Equally, a candidate that holds a whole timetable counts as `found`. This is fine for a report, but either record `got` texts with more than one date as "ambiguous", or say in EVAL.md that the match is per candidate text, not per date-time pair.
2. **Small parser gaps** (misses, never false hits): "30-Apr-2027", "the 30th day of April 2027", "midnight", 2-digit years. Add them if real packs use them. The "+01:00" in an ISO offset is read as a time 01:00. This is harmless because extra times in `got` never hurt, but it would matter if a key ever held an offset.
3. **`time_match` when the date is missed** is `False`, not `None`. EVAL.md says `time_match` "records separately" whether the time appears, which suggests it is checked without the date. Either check the time independently, or change the EVAL.md row to "time_match is evaluated only on candidates holding the key date (False when the date is not found; null when the key has no time)".
4. **`invented_unscored` is pooled only.** `per_pack` has no A2 figures, so the reader cannot see which pack is driving the new `invented` misses without filtering `wrong`. Consider per-pack `a2_stated`/`a2_correct`/`invented` counts.
5. The decision's part (c), shared limits in E2, has no code. That is correct and documented. Note for L2: with this change, an extractor that copies S09's "800 words in total" onto each of 2.1-2.3 now loses three A2 fields. That is the intended strictness, and it should appear in the L2 miss list by type.

## Security and performance

No new input surface. The scorer reads local key and result JSON. The regexes are linear (no nested quantifiers), and `score_deadline` is O(candidates) per pack. There is no AI cost.
