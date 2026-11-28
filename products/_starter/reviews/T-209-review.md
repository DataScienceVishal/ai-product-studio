# Review: p/_starter/T-209 (test for the orphan-close IntegrityError branch)

- Branch head: `dc1848c`, diff against `origin/main` (2 files, +27). It adds one test and one README line. There is no
  product code change.
- Reviewer: reviewer agent, 2026-11-28
- **Verdict: PASS**

## Evidence
- `tests/test_billing_customers.py` ran three times in a row, with **26 passed** each time (about 6 s per run).
- I disabled the `IntegrityError` handler in `routes/billing.py` (plain `db.commit()`). **Only the new test fails** (1 failed,
  25 passed). I then restored the file, and the worktree is clean. This confirms the builder's claim.
- Full backend suite (fresh worktree, fresh `.venv`, local Postgres 16): **855 passed, 1 skipped**, 1 warning, 131 s.

## Is the test sound and not flaky?
- **Separate session.** The twin delivery commits `e_dup` through its own `database.sessions()` session, inside the
  patched `close`. That is a separate connection, so the webhook's own commit then really hits the primary key in Postgres.
  The test exercises the real constraint, not a mock.
- **Deterministic.** There are no threads and no sleeps. The interleaving is forced inside the patched `close`, so the
  outcome cannot depend on timing.
- **Cleanup.** The autouse `_clean` fixture truncates every table after each test, and `app` (with its `MockBilling`) is
  created per test. The patched `billing.close` is restored at the end, but not in a `finally` block. That is harmless
  because the app is discarded after the test.
- **It checks behaviour.** It asserts that the call returns True with no exception, that the provider close happened once,
  that exactly one `e_dup` row exists, and that a later redelivery is skipped (`False`) with no second close.

## README line
- It accurately describes S4 from the T-208 review: the stale `subscriptions.provider_customer` after a checkout retry
  without the customer, until a webhook for the new customer overwrites it.

## Suggestions (not blocking)
- Optionally wrap the `billing.close` restore in `try/finally`, for consistency with tests that share fixtures.
