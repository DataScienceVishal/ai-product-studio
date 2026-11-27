# T-180 build note: T-179 M2 (cancel inside the row lock vs the idle-in-transaction timeout)

## What changed
- `backend/app/billing.py`: a cancel budget. Per-request timeout 4 s (was 8 s); DELETE keeps 2 tries (1 s backoff);
  the "already canceled?" GET after a rejected DELETE gets 1 try (was 2). `CANCEL_WORST_CASE_SECONDS` = 9 s, with a
  module-level `assert <= 10`. This also shortens the webhook's duplicate-cancel call; its semantics (503 and redelivery on
  failure, 404/canceled counts as done) are unchanged, and the T-174 S2 tests (2 DELETE tries, one GET) still pass.
- `backend/app/routes/billing.py`: `_record_failed_attempt`. If the failure commit fails (25P03 or a dropped
  connection), roll back, open a fresh transaction, re-read the row FOR UPDATE and still increment `attempts` and
  `last_attempt_at`, so backoff and the CRITICAL line at `ESCALATE_AT` keep working.
- `backend/tests/test_cancel_budget.py` (new, written first; the probe test failed with 25P03 before the fix).

## Design choice
Preferred option from the review: a short budget (9 s worst case, 6 s under the 15 s timeout) rather than a lease column or
a larger sweep timeout. Simplest, keeps the lock held across the call (T-175 takeover race stays closed). The fresh-transaction
fallback covers any remaining overrun. A cancel that overruns loses the lock, which the fallback accepts.

## Tests
- New: budget <= 10 s and <= 2/3 of both idle defaults; fake-clock worst case on both long paths; the reviewer's probe
  (idle timeout 300 ms, cancel sleeping 600 ms) across 10 sweeps: attempts 1..10, distinct `last_attempt_at`, one CRITICAL.
- Full backend suite (`cd backend && python -m pytest`, real Postgres): 828 passed, 1 skipped (tests/test_spa.py:152, frontend not built).
