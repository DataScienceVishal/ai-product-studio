# T-163 re-review (round 2): nested pool checkout fix and review nits

Branch `p/_starter/T-163`, head 53b9498, diff `2e2a48a..53b9498` (fix commit), whole branch re-checked against `main`.
Reviewer: reviewer agent, 2026-11-27. Previous review: `T-163-review.md` (CHANGES, Blocking 1).

## Verdict: PASS

Blocking 1 is fixed. N1, N2, N4 and N5 are done. I found no regressions. The suite is green on the exact head tree.

## Evidence

- **Full backend suite** in a clean detached worktree at 53b9498, local Postgres 16:
  `python -m pytest -o addopts="" -q -p no:cacheprovider` -> **720 passed, 1 skipped, 0 failed** (89.8 s). That is the
  previous 719 plus the one new regression test. `test_migrations` (upgrade, `alembic check`, downgrade) is included.
- **Blocking 1 (nested checkout).** The route now calls `ensure_ai_enabled(request.app.state.ai, db)` (`backend/app/routes/notes.py:113`).
  That passes the session to `check_persisted_trip(db)` and then to `TripStore.tripped(fp, db)` (`backend/app/ai.py:107-112`), which runs
  `db.get(AIGuardTrip, fp)` on the caller's session. It does no commit, opens no new session and checks out no second
  connection. `complete()` still makes its own check without a session (`ai.py:400`). That check runs after `reserve()` committed,
  and the commit released the request connection, so it does not nest.
  - Repro with `db_pool_size=1, db_max_overflow=0` (scratch test, not committed):
    - healthy `gpt-5-mini`: **200 in 0.19 s** (round 1: 503 after 10.2 s);
    - a trip persisted by an earlier process, then a **fresh** app on the same 1-connection pool: **503 `ai_budget_reached` in
      0.14 s**, zero Azure calls, `disabled` latched, and no "could not be read" log line. This shows the route's DB read on the request session
      really finds the row. It is not just the in-memory latch.
    - a read error on the request session (trip table renamed) on the 1-connection pool: 503 with the new neutral message,
      zero Azure calls, log line has the exception type only (`ProgrammingError`), and the request ends cleanly with no 500.
  - The in-tree test `test_route_trip_check_uses_the_request_session_not_a_second_connection` covers healthy -> 200 under 8 s
    and tripped -> 503 on the tiny pool.
- **Mutation check** (scratch copy, `tests/test_ai.py -k "trip or explicit_price"` plus my scratch tests):

  | Mutant | Result |
  |---|---|
  | route calls `ensure_ai_enabled` without `db` (round-1 code) | killed (new in-tree test + repro) |
  | `ensure_ai_enabled` drops `db` | killed |
  | `check_persisted_trip` drops `db` | killed |
  | `TripStore.tripped` ignores `db` and opens its own session | killed |
  | deployment removed from fingerprint (round-1 survivor) | **killed** (`test_changing_the_ai_config_clears_the_trip`) |
  | `tripped(db)` also calls `db.commit()` | survived (S1) |
  | N2 message reverted to "switched off until..." | survived (S2) |

- **N1**: the config-change test now trips `chat` at an explicit price of 2.0 and clears with `chat2` at 2.0. It asserts `checked_price is not None` for
  every change. The deployment mutant is now killed.
- **N2**: on a read error the message is "The AI is unavailable right now. Everything else still works.". The code is still
  `ai_budget_reached`. I confirmed this end to end above.
- **N4**: `BRIEF.md:165` now says 0001 to 0008.
- **N5**: `models.AIGuardTrip.tripped_at` now has `server_default=func.now()`, which matches migration 0008. `alembic check` is clean.
- N3 and N6 are unchanged, as accepted in round 1. There are still two PK reads per request until the process latches. They are cheap.
- **Security and privacy**: no new inputs, logging or secrets. The fingerprint and row contents are unchanged from round 1.

## Critical issues

None.

## Suggestions (non-blocking)

- S1. No test pins down "no commit on the caller's session". A `db.commit()` added inside `tripped(fp, db)` survives every
  test. It is harmless today, because nothing is pending at that point in the route. But a future route that writes before the
  check would get a surprise partial commit. Option: a test that adds a pending object to the session, calls
  `check_persisted_trip(db)`, rolls back, and asserts the object was not persisted.
- S2. Assert the neutral read-error message in `test_trip_check_failing_refuses_the_call_and_does_not_latch`. The N2 text
  is not pinned by any test.
- S3. The tripped half of the new tiny-pool test passes through the in-memory latch, because the first call in the same
  process trips it. Add a fresh-process case: trip in app A, then a new app B on the tiny pool gets 503 and makes zero calls. My scratch repro
  above does this. It would pin the route's persisted read on the request session directly.
- S4. The docstring of `test_trip_check_failing_refuses_the_call_and_does_not_latch` still says "reserve needs the DB
  anyway", the reasoning that round 1 rejected. `_summaries_again_two` duplicates `_summaries_again`. A `count`
  parameter would remove the duplication. The new test also ignores `first`, which should assert 200.
