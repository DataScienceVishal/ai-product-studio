# Review: p/_starter/T-101-model-price (d751086)

Reviewer, 2026-11-25. Scope: `git diff main...HEAD` (6 files, +209/-5). Goal: T-100 finding M1, where the AI cost guard
priced only the deployment *name*.

**Verdict: CHANGES** (one blocking finding)

## Summary

The approach is right. Each Azure reply's `model` is priced from the table, and a dearer model (or an unknown or missing
one with no explicit price) switches AI off for the process. The route refuses before it reserves anything, and the
call that tripped the guard is still settled with its real usage. The lookup handles case, whitespace, both date-suffix
forms and the `gpt-5.4` vs `gpt-5` trap. The logs carry the model name only (capped at 80 chars): no tenant data,
prompt text or secrets. The builder's four decisions are sound (see below).

The guard does have one hole. It only runs on replies that produced a usable answer. A dearer *reasoning* model is
the case most likely to burn its whole output budget and come back with `finish_reason: "length"` and no text, and
in that case the guard never fires.

## Blocking

### B1. Replies with no usable answer skip the model check (app/ai.py:384-388)

`_check_reported_model` is called at line 388, after the early `raise fail(...)` at line 386 for `why is not None or not
text`. Those replies are billed (`billed_in/out` include `used_in/out`) and settled as `note_summary:failed`, but the
reported model is never looked at. I reproduced it with a provider set to `checked_price=2.0` (deployment `gpt-5-mini`)
whose replies are `{"model": "gpt-5-pro-2025-10-06", "finish_reason": "length", content "", completion_tokens 1200}`:

```
fail billed 300 1200 disabled= False   (x3, every call)
```

M1's own threat model is "a cheap name on an expensive model". With gpt-5-pro or gpt-5.4-pro behind the name,
reasoning tokens eating the 1,200-token answer budget plus headroom is a likely result (Responses `incomplete` /
`max_output_tokens` too). Each such call is billed at 60-90x the checked price and none of them trips the guard, so
the burn that M1 described still happens. Content-filter and empty replies have the same gap.

**Fix:** call `self._check_reported_model(data.get("model"))` as soon as `data` is a parsed dict, before the
`_parse`/no-answer branches. At the latest it must come before line 384. A disable then still bills the current call,
because `fail()` carries `billed_in/out`. Add a test: dearer model + `finish_reason: "length"` -> first call 502/503 as
today, `disabled is True`, and the next call 503 `ai_budget_reached` with no Azure request.

## Suggestions (non-blocking)

1. **Prefix match prices unknown siblings as the family base (app/aicost.py:80).** Any `gpt-5-<anything>` not in
   the table is priced at gpt-5 ($10). Today that is safe for a gpt-5-mini/nano deployment (10 > 2 still trips the
   guard). It is not safe for a `gpt-5` deployment, or one with an explicit price of 10 or more: a future dearer
   `gpt-5-ultra-2027-01-01` would be accepted at $10 (verified: `reported_model_price("gpt-5-ultra-2027-01-01") == 10.0`).
   A stricter rule would be safer: accept only `key`, `key-<date>`, or a short allow-list of suffixes that keep the
   price (for example `-chat`, `-latest`), and treat anything else as unknown.
2. **Mid-flight disable path is untested.** A request that passes the route check (notes.py:113) and then reaches
   `complete()` after another request has disabled the provider gets the `AppError` from ai.py:316. That falls into
   `except Exception` (notes.py:127) and settles 0/0, so the reservation is released correctly. I traced this, but no
   test covers it. One unit test with two providers or a pre-set `disabled` after `reserve` would pin it.
3. **Concurrency.** `disabled` is a plain bool. Under the GIL the flip is atomic and the worst case is benign: calls
   already in flight finish and are billed, and two threads can each log the error once (the `or self.disabled` check
   at ai.py:299 is not atomic with the set at :310). That is acceptable. Note that each worker or replica trips on its
   own, which the docs correctly describe as "for the process".
4. **Responses API not covered by the new tests.** All new tests use the chat shape. Add one Responses-shaped reply
   (`api="responses"`) so a later refactor of `_parse` can't silently drop `model` there.
5. **User-facing message (ai.py:78)** says "resting until tomorrow", but this disable lasts until restart. Reusing the
   code is right because the frontend handles it, but the text is wrong for this case. A separate message with the
   same code would be more honest. Nit.
6. **`AIResult.model` fallback changed** from the deployment name to `"unknown"` when `model` is missing
   (ai.py:389-390). That is better (deployment names are free text and could be sensitive in usage rows), but it is a
   behaviour change worth one line in the commit or ADR. Nit.

## Builder decisions

- Unknown model + explicit price accepted: **agree**. The operator declared the cost and the startup check used it;
  refusing would make any model outside the table unusable.
- Known dearer model refused even with an explicit price: **agree**. The table is the floor, which matches
  `resolve_price`'s "explicit can only raise".
- Disabled until restart: **agree**. It fails closed, needs no state, and a config fix needs a restart anyway.
- Deploy-time `cost-guard.sh` stays name-based: **agree**. It cannot see the runtime model, and the ADR says so.

## Docs

README and ADR 0002 describe the behaviour correctly ("the call that revealed it is kept", 503 `ai_budget_reached`,
"until restart", "unknown with explicit price accepted"). After B1 is fixed they should say the check applies to
every reply Azure answered, including ones with no usable text.

## Test evidence

- Temporary Postgres 16 cluster on port 5433, Python 3.12.3, `TEST_DATABASE_URL=...localhost:5433/starter_test`,
  `python -m pytest` in `products/_starter/backend`: **686 collected, 685 passed, 1 skipped**
  (`test_spa.py:152`, frontend not built), 0 failures, 67.9 s (junit summary).
- The 13 new T-101 tests pass on their own. They test behaviour: HTTP status codes, the `ai_usage` rows left behind,
  exactly one error log containing the model name, and no Azure call after disable. They would catch regressions in
  the success path but not B1.
- Ad-hoc check (no code changed): the no-answer reproduction above, plus `reported_model_price` on `gpt-5-chat-latest`
  -> 10, `gpt-5.4-mini` -> None, `" gpt-5-mini "` -> 2, `gpt-5-mini-2025-08-07-ft-abc` -> 2.
