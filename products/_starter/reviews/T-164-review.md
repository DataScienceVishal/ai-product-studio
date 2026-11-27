# T-164 review: T-163 round-2 suggestions S1-S4, stale comment, finish_reason sanitising

Branch `p/_starter/T-164`, head 1ee1385, scope `git diff main...p/_starter/T-164` (3 files: `backend/app/ai.py`,
`backend/tests/test_ai.py`, `reviews/T-164-build.md`). Reviewer: reviewer agent, 2026-11-27.

## Verdict: PASS

All six items are done. Each new test kills the mutant it is there for, and I re-ran those mutants myself. The full suite is
green on the exact head tree. I found no blocking issues.

## Evidence

- **Full backend suite**: I ran it in a clean detached worktree at 1ee1385 against local Postgres 16, with
  `python -m pytest -o addopts="" -q -p no:cacheprovider`. Result: **723 passed, 1 skipped, 0 failed** (87.1 s). That is the
  T-163 round-2 count of 720 plus the 3 new tests.
- **Mutants**: each was applied to the scratch worktree, run, then reverted with `git checkout app/`.

  | Mutant | Test | Result |
  |---|---|---|
  | S1: `db.commit()` before the read in `TripStore.tripped(fp, db)` | `test_persisted_trip_read_never_commits_the_callers_session` | **killed** (`assert 1 == 0`, the pending Tenant was persisted) |
  | S2: read-error message reverted to "switched off ..." | `test_trip_check_failing_refuses_the_call_and_does_not_latch` | **killed** |
  | S3: route calls `ensure_ai_enabled(provider)` without `db` | `test_fresh_process_on_a_tiny_pool_reads_the_persisted_trip` | **killed** (pool starvation, 20.5 s run) |
  | finish_reason logged raw (`extra={"finish_reason": why}`) | `test_finish_reason_with_newlines_cannot_forge_a_log_line` | **killed** (it asserts that no `\n\r\x1b` remains) |
  | `_clean_reason` without the 40-character cap | same | **killed** |
  | `_clean_reason` maps None to "unknown" instead of "none" | whole suite | survived (see suggestion 1) |

- **S3 is real**: app B is a new `_store_app` with nothing in memory. The test asserts `disabled is False` before the call,
  so the 503 can only come from the persisted row read on the request session. Before the change it could have come from the
  in-memory latch. Zero model calls, and `disabled` is True afterwards.
- **S4**: the docstring is fixed, `_summaries_again_two` is gone (`_summaries_again(app, count)` is used at both call sites),
  and `first.status_code == 200` is asserted.
- **Stale comment** at `tests/test_ai.py:1183` now describes the exact-name, one-date-suffix rule.
- **`_clean_reason` spot checks**: None gives `none`; 5 and `['x']` give `unknown`; `''` and `'  '` give `unknown`; `stop`
  is unchanged. U+202E and a lone surrogate are stripped (both are non-printable). 50 characters are cut to 40.

## Behaviour change: None logs as "none" instead of null

I accept this change. It is only a structured log field on a warning line, and no code or document reads it. Grep finds no
KQL, alert or infra file that references `finish_reason`. `"none"` (the provider sent nothing) is still different from
`"unknown"` (junk, or an empty string), so nothing is lost. Anyone who writes an App Insights query later should match the
string `none`, not null. The user-facing message lookup (`_NO_ANSWER.get(why, ...)`) still uses the raw `why`, which is
correct because `_reason` has already normalised it to `str | None`.

## Critical issues

None.

## Suggestions (non-blocking)

1. Nothing pins the `None -> "none"` mapping. A mutant that collapses it to `"unknown"` survives the whole suite. If the
   distinction matters for log queries, add a one-line unit test, e.g. `assert _clean_reason(None) == "none"` and
   `_clean_reason("") == "unknown"`.
2. `_clean_reason` does `.strip()[:40]` but no second strip, so a 40-character cut can end in a space. `_clean_model` does
   `[:80].strip()`. This is cosmetic only, but matching the two would keep them consistent.
3. `_clean_reason`'s non-string branch is unreachable today, because `_reason` already maps non-strings to `"unknown"`. It
   is fine as defence in depth, but a short comment would stop someone deleting `_reason` and relying on it.

## Security and privacy

The log-forging gap from T-162 is closed for `finish_reason`. No new inputs, secrets or logged text. The S1 test uses a
throwaway `Tenant` and rolls it back, then confirms from a fresh session that it is gone.

## Performance

No change on the request path. `_clean_reason` runs only on the failure path and touches at most the provider string.
