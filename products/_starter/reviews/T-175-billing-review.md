# Review: p/_starter/T-175-billing (dafc629, main merged in)

Reviewer: reviewer agent, 2026-11-27. Diff: `origin/main...HEAD` (routes/billing.py, maintenance.py, models.py,
migration 0010, tests/test_pending_cancels.py, tests/test_migrations.py, README, NEXT.md).

## Verdict: CHANGES

One blocking money bug (B1): a durable pending cancel can cancel the tenant's current, live subscription. Everything
else is sound or a suggestion.

## Tests

Full backend suite on real Postgres 16 and Redis: **800 passed, 1 skipped** (`tests/test_spa.py:152`, frontend not
built), 102 s. That is the builder's 796 plus the tests that came in when main was merged.

Mutation checks (each change made to `app/routes/billing.py`, then put back with `git checkout`. The tree was clean
afterwards):

| Mutation | Result |
|---|---|
| M1: drop `_record_pending_cancel` in the takeover | 11 fail (8 in test_pending_cancels, 3 S6/B5 in test_billing) |
| M2: put back the T-174 `db.flush()` / `db.rollback()` dead-marker code | `test_dead_marker_collision_keeps_the_second_events_id` fails |
| M3: drop the retry call in `apply_update` | 8 fail |
| M4: remove the `try/except` around the retry in `apply_update` | **nothing fails** (S3) |
| M5: remove the savepoint and keep only the `db.get` check | **nothing fails** (S4; the concurrent-insert path is not tested) |

## Summary

- **Durable to-do (item 1).** The row is written in the same transaction as the takeover (billing.py:219-223), so a
  crash after the commit cannot lose it. `test_todo_survives_a_crash_between_commit_and_cancel` proves this with a
  `SystemExit`. Only one row is kept per (provider, ref): there is a check first and a unique constraint behind it. The
  insert runs under the tenant's subscription row lock, so two inserts cannot race for one tenant. The wrapper's retry
  runs only after `_apply_update` has committed on every path. I checked every return: each commits or rolls back
  first. The 503 duplicate path raises before the retry. So a retry failure cannot undo the event or change its answer.
  `attempt_pending_cancel` catches every `Exception` from the provider, and the wrapper catches database errors. The
  wrapper's `rollback()` only drops the retry's own unflushed change, because every attempt commits by itself.
- **Already cancelled counts as success.** `StripeBilling.cancel_subscription` turns 404 and rejected-then-GET
  `canceled` into success. Both cases are tested through the sweep.
- **Dead-marker fix (item 2).** `db.get` plus `begin_nested()` keeps the event's own dedup row. M2 shows the test
  catches the old bug.
- **Migration 0010.** Upgrade and downgrade are tested (0009 to head to 0009) and `alembic check` is clean. The columns
  match the model. `created_at` has no server default, like the other tables. The downgrade drops the index and then
  the table, which is correct.
- **Personal data.** The table holds a tenant id, a provider ref, a count and an error string. The error strings come
  from fixed `AppError` messages in `_call`, so no provider text is stored. The logs carry the tenant id and the
  subscription ref, as before. No personal data.
- **Nullable `tenant_id` with ON DELETE SET NULL** is right. The old subscription can still bill after the account is
  deleted (for example when `close()` was given only a subscription ref). Rows without a tenant are reached only by the
  sweep, which is one more reason the sweep job (S1) is needed.

## Critical issues

### B1. A pending cancel can cancel the tenant's current, live subscription (new in T-175)

`routes/billing.py:203-223` (takeover) and `:244-270` (`attempt_pending_cancel`, `retry_pending_cancels`), plus
`maintenance.py:67-80`.

The to-do row is never checked against the subscription the tenant has now. A takeover can make a ref current while
that ref still has a pending row. The next retry then cancels the live subscription the customer just paid for. Before
T-175 the cancel ran once, inline, so a stale to-do could not exist.

I reproduced it with a temporary test, now deleted. It uses Stripe-shaped events through `_stripe_apply`, with cancels
failing until the last event:

```
p1 checkout.session.completed            sub_1   (t-300)
p2 customer.subscription.updated past_due sub_1  (t-250)
p3 checkout.session.completed            sub_2   (t-200)  takeover, pending: sub_1 (cancel fails)
p4 customer.subscription.updated past_due sub_2  (t-150)
p5 checkout.session.async_payment_succeeded sub_1 (t-100) takeover back, current = sub_1, pending: sub_1, sub_2
p6 customer.subscription.updated active  sub_1   (t-50)   provider back up
-> cancelled ['sub_1', 'sub_2'], current ('active', 'starter', 'sub_1'), pending []
```

The customer paid for sub_1, and the studio cancelled it at the provider. Stripe's `customer.subscription.deleted`
for sub_1 then sets the tenant to canceled, so a paying customer loses access. That means a refund or support case. A
start event for a ref that is already in `pending_cancels` is unusual at Stripe (the likeliest case is a delayed
BACS or SEPA `async_payment_succeeded`). It is easy with any provider that follows the `BillingUpdate` contract, and
the code does nothing to prevent it. The sweep has the same problem, plus a race: it loads rows with no lock, so a
takeover that commits between the sweep's SELECT and its cancel call is not seen.

Fix (small):
1. In the takeover branch, delete any `PendingCancel` for `(provider, update.provider_ref)` in the same transaction.
   A ref that becomes current is no longer a to-do.
2. In `attempt_pending_cancel`, re-read the row `FOR UPDATE SKIP LOCKED` (skip it if it is gone or locked). Then skip
   and delete it if the tenant's `Subscription.provider_ref == row.ref` with the same provider. Keep the row lock until
   the commit after the cancel, so step 1's delete waits for an in-flight cancel. The table is tiny and one cancel
   takes at most about 17 s, so holding the lock is acceptable. This also fixes S2.
3. Add a test with the sequence above: only sub_2 is cancelled and sub_1 stays active.

### B2. DATA.md has no row for `pending_cancels` (builder caveat)

The README sends readers to `DATA.md` for "what is stored and for how long", and every other table has a row there. Add
one: tenant id (cleared on account deletion), provider and subscription ref, attempt count, last error; purpose:
cancelling a replaced subscription; kept until the cancel succeeds; removed by the webhook retry or `maintenance
cancels`. This is a one-line documentation fix, but the definition of done needs the data inventory to be accurate.

## Suggestions (non-blocking)

- **S1. No scheduled sweep yet (builder caveat).** Without the Container Apps job, a to-do is retried only when the
  same tenant gets another billing event. A tenant with no more events, or a deleted tenant, keeps paying for the old
  subscription and the only sign is one ERROR line. Add a board task for the `infra/main.bicep` job (the purge job is
  the model) before G4. Until then this follow-up is only half done.
- **S2. Sweep against the webhook retry.** Two workers can both cancel one row. That does no harm: the cancel is
  idempotent and the second `DELETE` matches 0 rows, which SQLAlchemy only warns about (I checked). But when the second
  worker's cancel fails, `row.attempts += 1` on a row that is gone raises `StaleDataError` (I checked). In the webhook
  the wrapper catches it. In the sweep nothing does, so the run stops and the remaining rows wait until the next run.
  The `SKIP LOCKED` in B1 fixes this. Also wrap each row in the sweep in its own try/except with `db.rollback()`.
- **S3. No test for the wrapper's except.** M4 survives. Add a test where `retry_pending_cancels` raises (for example
  a patched `db.commit` or a `StaleDataError`). It should check the webhook still answers 200 with `applied: true`
  and the event row is committed.
- **S4. No test for the dead-marker savepoint.** M5 survives. A test with a second connection that inserts the marker
  and holds it uncommitted would cover the `IntegrityError` branch (the same pattern as the T-173 race tests).
- **S5. Retry cost on every event.** During a Stripe outage, each event and each redelivery for the tenant now runs up
  to about 17 s of cancel attempts per pending row before it answers. That can push the webhook past Stripe's timeout
  and cause more redeliveries. Nothing is corrupted because dedup holds. Consider retrying in the webhook only rows
  with `attempts < 3` (or created in this event) and leaving the rest to the sweep.
- **S6. No backoff and no alert.** A cancel that fails for good (the provider rejects it and the subscription is still
  live) is retried and logged at ERROR on every sweep and every event, forever. Add a `last_attempt_at` column, or
  escalate once `attempts` passes N, so the operator sees one clear alert and not constant ERROR lines.
- **S7.** The table has no `updated_at` or `last_attempt_at` column, so an operator cannot tell how long a to-do has
  been failing.
