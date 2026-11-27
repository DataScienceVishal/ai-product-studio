# T-163 build: persist the model-guard trip, explicit price no longer covers unknown models

Branch p/_starter/T-163 (on T-162). Fixes T-161 M1 (medium) and L1 (low).

## What changed
- `backend/migrations/versions/20261126_0008_ai_guard_trips.py` and `models.AIGuardTrip`: table `ai_guard_trips`
  (`fingerprint` PK, `tripped_at`, `model`). No tenant, prompt, answer or secret data.
- `ai.py`: `TripStore` (one short transaction per read or write); `AzureOpenAI.attach_trip_store` builds the fingerprint
  (SHA-256 of normalised URL, lower-case deployment, checked price); `check_persisted_trip`; `_check_reported_model`
  saves the trip. `ensure_ai_enabled` asks the store when the in-memory `disabled` flag is not yet set (fast path kept;
  once the DB says tripped, `disabled` latches). `complete()` already calls `ensure_ai_enabled`, so route and direct callers are covered.
- `main.py`: `create_app` attaches the store to any provider that supports it (FakeAI does not).
- L1: `AzureOpenAI.__init__` sets `price_explicit = price_explicit and not deployment_in_table(deployment)` (new
  `aicost.deployment_in_table`). So gpt-5-mini + price 2.0 + reported o1-pro now trips; unknown deployment ("chat") +
  explicit price still accepts unknown models, and a known dearer model still trips. Consistent with T-162's exact-name lookup.
- README and ADR 0002 wording updated (guard text, how to clear).

## Decisions for the reviewer
1. Fail closed on a trip-check read error: 503 `ai_budget_reached`, does NOT latch `disabled` (next call retries). Reason:
   `reserve()` needs the same DB, so no AI call works with the DB down anyway; failing open would add no availability.
   Log line has the exception type only.
2. Fail open on a trip WRITE error (the process is off regardless; error logged, other replicas will not see it). Writing
   cannot be made safer than the DB being up.
3. Fingerprint uses checked price (resolved, max of table and explicit), not the raw setting, so an explicit price lower
   than the table (no effect) does not clear a trip. Changing the explicit price above the table does.
4. A fixed Azure-side model with unchanged config is NOT cleared automatically: delete the row (`DELETE FROM ai_guard_trips`)
   and restart (running replicas stay latched in memory). Documented in README.
5. One extra primary-key read per AI request (route check) and one in `complete()`, until the process latches or trips. Only AI calls.
6. Not changed: a replica already running when another trips keeps serving until its next `ensure_ai_enabled` (i.e. the next request), calls in flight finish.

## Tests (written first, seen failing: 7 failures before the code)
`tests/test_ai.py`: restart/second replica stays off with zero Azure calls; config change (deployment, endpoint, explicit
price) clears it; trip row holds no secret; unreadable store refuses, no latch, no leak; unwritable store still trips the
process; L1 probe (gpt-5-mini, 2.0, reported o1-pro-2025-03-19 trips); `build_provider` explicit-price scoping.
Migration test (`command.check`, up/down) covers 0008.

Full backend suite: `cd backend && /tmp/claude-0/venv/bin/python -m pytest tests` -> 719 passed, 1 skipped (was 712 + 1 skipped). No infra file touched.
