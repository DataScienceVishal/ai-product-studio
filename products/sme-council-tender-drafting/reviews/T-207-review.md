# Review: p/sme-council-tender-drafting/T-207

Reviewer, 2026-11-28. Diff: `git diff -w origin/main...origin/p/sme-council-tender-drafting/T-207` (commits 48d0076, d00b8e8; 48d0076's "decisions:" message is known to hold builder code, no rewrite asked).

## Verdict: CHANGES

One must-fix: the new heading rule `_is_bracketed_limit_heading` makes the previous unnumbered question's bracketed limit override the next question's own limit. Items 2 (token reporting) and 3 (DESIGN.md note) are correct and could merge as they are.

## Tests

Full backend suite on the branch's exact tree (worktree at d00b8e8, clean):

```
TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""
1215 passed, 1 skipped in 234.56s
```

The suite passes, but it has no case for the regression below.

## Critical issues

### C1. The bracketed-limit heading rule takes the previous question's limit, overriding the next question's own (app/tender/extract.py:116-120, used at :136)

`_is_bracketed_limit_heading` accepts **any** line of 150 characters or fewer that ends in "(... N words)". Imperative earlier questions are included. T-201 item 7 added the `_QUESTION_LEAD` + you/your check in `_is_heading` to reject exactly these lines, and the new rule skips that check. Unnumbered questions that end with "(max N words)" are a common council-tender layout. `_stated` then returns the **first** limit in the window, which is now the heading's. So the requirement's real limit gets replaced, not just a missing one filled in.

I probed `stated_word_limit(page, quote)` on the branch, then with `_is_bracketed_limit_heading` patched to `False` (the main behaviour):

| page (quote = second paragraph) | branch | main |
|---|---|---|
| `Describe your approach to social value (max 300 words)\n\nDescribe your staffing plan.` | 300 | None |
| `Describe your approach to social value (max 300 words)\n\nDescribe your staffing plan (max 500 words)` | **300** | 500 |
| `Explain how you will mobilise (maximum 250 words)\n\nWhat is your approach to TUPE? Answers should not exceed 600 words.` | **250** | 600 |
| `1. Describe your approach (max 300 words)\n\n2. Describe your staffing plan.` | None | None (numbered: safe) |

Why it matters: the stated limit drives the draft's word budget and the shorten/trim step. With a wrong, smaller limit, a compliant answer gets trimmed to the previous question's count. The wrong-limit flag only helps if the model's limit happens to disagree. EVAL.md "Known limits" calls the impersonal-wording case (KL-3) the only false positive. This new one is broader, and the rule brings it in.

Fix (both parts recommended):
1. Narrow the rule. Do not accept a line that opens with an imperative request verb (describe, explain, provide, set out, outline, state, detail, give, tell us, demonstrate, confirm, list, identify, please ...). Keep accepting interrogative-word noun phrases with no inversion ("How you will deliver ...", "What we need from you ..."). Also refuse a line ending in "?" before the bracket.
2. Give the question's own limit precedence. In `_stated`, search from the quote start forward first, and use the heading part of the window only when the quote's own text has no limit. Then even a wrongly accepted heading can never override a stated limit.
3. Add the three rows above as regression tests: the first as None (or as a new open known-limit case if you choose to accept it), the second as 500, the third as 600. Add them to `eval/extraction_known_limits.json` where they belong.

## Checked and correct

- **Token reporting, no double count.** `run_task` (llm.py:204-240) wraps only the model-call loop. `total_in/total_out` are added once per settled call: the `AIUnavailable` path at :213, the success path at :225. `except AppError` sets `task_tokens` to that sum and re-raises. Cache hits and recorded answers return before the `try`, so they report 0, as before. `draft_answer` (draft.py:202) adds `task_tokens` only on the failed-shorten branch, where `again` was never assigned, so the retry is not counted twice. `AIUnavailable` subclasses `AppError` (ai.py:84), so `error.task_tokens` exists on both caught types (class default `(0, 0)`). `draft_handler` (draft.py:266) adds earlier drafts to the failing call's own. Those are disjoint sets: `tin/tout` are updated only after a successful `draft_answer`. The runner (runner.py:118) reads the value once.
- **ai_usage unaffected.** Budget settlement (`budget.settle`) is unchanged and still runs once per call. `task_tokens` only feeds `ai_tasks.input_tokens/output_tokens` through `_finish`.
- **Side effect on other handlers (fine):** extract and check tasks that fail inside `run_task` now report the failing call's tokens instead of 0. That is more accurate, never higher than what was billed.
- **Tests are meaningful.** `test_tokens_spent_inside_a_draft_call_that_then_fails_are_kept_on_the_task` would read 0/0 on main, so it fails without the change. It asserts 2 calls and 200/100. `test_a_failed_shorten_retry_keeps_the_draft_and_counts_its_tokens` asserts 114/56, the shorten call plus its repair. `test_known_limit_cases_hold` ties the JSON cases to the code, so the doc cannot drift.
- **DESIGN.md identical-redraft note:** clear, and it matches the current behaviour.

## Suggestions (non-blocking)

- S1. The new test functions in test_tender_t199.py have an unused `import json` (first test). The `calls` class attribute on `Bad` is shared across instances. It is fine here, but a module-level counter or an instance attribute is clearer.
- S2. EVAL.md "Known limits" item 2: once C1 is fixed, say that the bracketed rule refuses imperative leads. Otherwise, list the C1 pattern as a third known limit.
- S3. `_BRACKET_LIMIT_END` accepts "(300 words)" with no max/limit word, but `_LIMIT` would not then find a limit in that heading. The rule widens the window without finding anything, which is harmless, but worth a comment.

## Re-review (004739f, 2026-11-28)

Reviewed `git diff 2d4de0d..004739f` (extract.py, tests, eval JSON, EVAL.md, NEXT.md). Detached checkout of 004739f, clean tree.

### Verdict: CHANGES (one small must-fix)

### Tests

```
TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""
1217 passed, 1 skipped in 217.89s
```

The two added tests pass.

### C1: fixed for the probed cases

I ran the probes on 004739f and on origin/main:

| case | 004739f | main |
|---|---|---|
| instruction + bracket, next question has no limit | None | None |
| same, next question states 500 | 500 | 500 |
| "Explain how you will mobilise (maximum 250 words)" then TUPE question with 600 | 600 | 600 |
| numbered | None | None |
| KL-1a "How you will deliver social value (max 300 words)" heading | 300 | None (the intended gain) |

### No heading limit is lost

`_stated` searches `own` (from the quote to the end of its block) first, then falls back to `pattern.search(window)` over the whole window. That window is the same as before, heading included, so it can never find less than main did. Probes where the question states no limit all still return the heading's 300 on both trees: a plain heading with a blank line, a plain heading in the same block, "How we deliver ...", and a heading with a multi-paragraph question. The page-limit path behaves the same as main. `qoff` is always >= 0 because the window starts at or before the match.

### Must-fix R1: "How will you ... (max N words)" with no "?" is a new borrowed-limit false positive (extract.py:119-121)

`_IMPERATIVE_OR_INVERTED` lists `will we` among the inverted forms but not `will` / `will you`. So an earlier question phrased "How will you ensure quality (max 300 words)" or "What will you do in the first 90 days (max 300 words)" is accepted as a heading. The next question, if it states no limit, borrows 300. On main both return None, because `_is_heading` refuses a question lead followed by "you". This is the C1 class again, in the borrow-only form: the question's own limit still wins when it states one. Councils often phrase questions as "How will you ...". Fix: replace `will we` with `will` in the inverted group, so it reads `...|should|will|have|has)\b`. Add both lines as KL cases with expected None.

### Suggestions (non-blocking)

- R2. "Own limit wins" covers only the quote's own block. A heading "(max 300 words)" followed by the question, then a blank line, then "Your answer must be no more than 400 words." still returns 300. Main does the same, so this is not a regression. Record it as an open KL case, or extend `own` to the end of the window when the heading is the only other limit.
- R3. Imperatives not in either list ("Summarise", "Specify", "Evidence", "Show", "Include") still pass `_is_heading`, the same as main. This is the existing KL-3 family. Worth adding to the EVAL.md note.
