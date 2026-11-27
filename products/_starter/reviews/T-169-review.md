# Review: p/_starter/T-169 (bd053ae vs main)

Reviewer run, 2026-11-27. Scope: test-only change implementing S1-S3 from `T-168-review.md`
(`backend/tests/test_ai.py`, +40/-3) and README test count 733 -> 734.

## Verdict: PASS

## Evidence

- Full backend suite on the branch (worktree, real Postgres `starter_test`): **734 passed, 1 skipped in 95.43s**, rc=0.
  Matches the README update.
- No product code changed (`git diff --stat main...origin/p/_starter/T-169`: README.md and tests/test_ai.py only).

### Mutants, re-run independently

Each mutant was applied to the branch's app code, run against the branch's test and against main's `test_ai.py`
for contrast, then reverted (`git checkout app`).

| # | Mutant | Branch test | Main tests |
|---|---|---|---|
| S1 | raw `db.execute(text("UPDATE notes SET title = title WHERE id = :i"))` just before `ensure_ai_enabled` in `routes/notes.py::summarize` | `test_notes_route_calls_ensure_ai_enabled_on_a_session_with_no_writes` FAILS (`assert True is False` on `sql_wrote`) | same test passes (mutant survived before T-169) |
| S2 | `if db is not None:` -> `if True:` before `db.rollback()` in `AzureOpenAI._save_trip` | `test_failed_retry_without_a_caller_session_does_not_need_rollback` FAILS (rollback log present) | passes (survived) |
| S3a | `ensure_ai_enabled` moved after `reserve()` | `test_request_refused_by_the_trip_writes_no_budget_reservation` FAILS (`3 == 2` usage rows) | already caught (7 failures in main's test_ai) |
| S3b | `TripStore.tripped(db=...)` returns `False` | new test FAILS (`2 == 1` usage rows on the fresh app) | **all 186 pass** (survived before T-169) |

All four builder claims hold; three of them close real gaps.

### Listener leakage

- `before_flush` on `OrmSession` (global) is removed in `finally` (unchanged from main).
- `before_cursor_execute` is attached to `app.state.db.engine`, which is created per `Database` instance
  (`app/db.py:41`) by `create_app` for this test only, and disposed in `finally`. It is never attached to the
  shared `database` fixture's engine or a module-level engine, so it cannot fire in other tests. Full suite green
  confirms no cross-test effect.

## Critical issues

None.

## Suggestions (non-blocking)

1. `tests/test_ai.py` notes-route spy: the engine listener is not `event.remove`d in `finally`, unlike the
   `before_flush` one. Harmless today because the engine is throwaway, but removing it keeps the pattern
   symmetrical and safe if someone later points the test at a shared engine.
2. Same spy: `db.connection()` inside the spy begins a session transaction if none is open. That is harmless here
   (the real `ensure_ai_enabled` reads on the session right after), but `db.in_transaction() and db.connection()`
   would make the probe side-effect free.
3. The write detector matches only statements starting with INSERT/UPDATE/DELETE. A CTE write (`WITH ... UPDATE`)
   or `MERGE` would slip through. Fine for this route; add a comment if the spy gets reused.
4. S3 test: `assert baseline >= 1` is loose. Fine as a sanity check, since the later equality asserts carry the
   behaviour.
