# Review: p/_starter/T-208 (T-181 follow-ups S1-S4 and nits)

- Branch head reviewed: `4b27901`, diff against `origin/main` (7 files, +318 / -21)
- Reviewer: reviewer agent, 2026-11-28
- **Verdict: CHANGES** (one must-fix item, money safety)

## Summary

The branch covers each T-181 follow-up:

- **S1, race during deletion.** `routes/account.py` now loops. Each round closes what is listed with no lock held, then takes
  `SELECT ... FOR UPDATE` on the subscription row (`populate_existing`) and reads `billing_customers` again. A round that
  finds nothing new deletes the tenant under that same lock. If customers are still appearing after 5 rounds, the request
  answers 503.
- **S1, payment after deletion.** `routes/billing.py` `_close_orphan` runs when an event's tenant has no subscription row. It
  closes the customer and subscription at the provider, unless a live tenant has recorded that customer. If the close fails,
  it deletes the event id and answers 503, so Stripe redelivers.
- **S2.** There is now a migration test for 0012: backfill, `check`, downgrade.
- **S3.** `close` uses a 6 s timeout and 2 tries.
- **S4.** When Stripe answers `resource_missing` with `param=customer`, checkout tries once more without `customer`.
- **Nits.** `_record_customer` now inserts inside a savepoint, and DATA.md and README wording is updated.

The deletion loop is correct. The orphan close has one dangerous gap: it closes the customer of any tenant id it does not
recognise, and that includes tenants that never existed in this app.

## Evidence

- Full backend suite (fresh worktree, fresh `.venv` per README, local Postgres 16, `studio` role):
  `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider -q` gave **849 passed, 1 skipped**, 1 warning (Starlette
  deprecation), 126 s. Before this branch main had 838 + 1. The 11 new tests all pass.
- Do the tests fail without the fix? I reverted each part on its own and ran `tests/test_billing_customers.py` (20 tests):

  | Part reverted | Tests that fail |
  |---|---|
  | `routes/account.py` restored from main | 2 (both "recorded during deletion" tests) |
  | `_close_orphan` call removed | 3 (late payment closes, failing close 503 + redelivery, webhook route 503) |
  | live-owner guard in `_close_orphan` removed | 1 (`never_closes_a_customer_a_live_tenant_owns`) |
  | event id kept on orphan close failure | 1 (`failing_close_..._redelivery_closes_it`) |
  | savepoint in `_record_customer` removed | 1 (`refused_at_the_insert`) |
  | `MAX_CLOSE_ROUNDS = 1` (no re-read) | 5 |

  Every fix has a test that fails without it.
- Real concurrency probe (a temporary test, deleted afterwards): a webhook thread fired while `DELETE /api/account` was
  running. The result was 204 with `closed = [(cus_A, sub_1), (cus_LATE, None)]`. No deadlock, no hang, and no
  `billing_customers` rows were left.
- Unknown-tenant probe (a temporary test, deleted afterwards): a signed paid checkout event with a random tenant UUID that
  this app never had led to `billing.close("cus_FOREIGN", "sub_foreign")`. This is the must-fix below.

## Critical issues

### C1 (money, data integrity): `_close_orphan` deletes customers that may belong to another app on the same Stripe account
- Where: `backend/app/routes/billing.py:147-150` (the `sub is None` branch) and `:263-283` (`_close_orphan`).
- What happens: `sub is None` means two different things. Either this tenant was deleted, or this app has **never had** this
  tenant. The new code treats both the same way, and the only guard is "no live tenant here recorded this customer". A Stripe
  account sends every event to every webhook endpoint, and each endpoint signs with its own secret, so the signature check
  passes. Suppose a second studio product, or any other integration, uses the same Stripe account and puts a `tenant_id`
  (or `client_reference_id`) UUID in its checkout metadata. Its events reach this app with a valid signature and a tenant
  this app doesn't know, and this app then **DELETEs that product's paying customer** (customer, cards and subscriptions).
  `playbooks/definition-of-done.md` says the keys come from the business owner's single Stripe account, and every product is
  cloned from `_starter`, so a shared account is the expected setup. Before this branch the branch was a harmless no-op. It
  is now destructive, irreversible and silent: each one is logged only as a WARNING with a tenant id.
- Fix: only close when we know the tenant **was ours and was deleted**. Two options:
  1. In the deletion transaction (`routes/account.py`, just before `db.delete(Tenant)`), write a tombstone, for example
     `BillingEvent(id=f"deleted-tenant:{tenant_id}")`. This reuses the events table with no migration, it is purged after
     400 days, and a checkout session only lives 24 h. Then in `_close_orphan` return early unless
     `db.get(BillingEvent, f"deleted-tenant:{update.tenant_id}")` exists. Add a line to DATA.md: a random tenant UUID only,
     no personal data.
  2. Alternatively, or as well, add `metadata[app]=<slug>` to the session and subscription, and ignore events whose `app`
     doesn't match.

  Add a test: a paid checkout event for a tenant UUID that never existed closes nothing, and the event is still recorded.

## Suggestions (not blocking)

- **S1, crash window in `_close_orphan`.** The event id is committed (`billing.py:148`) **before** the provider call. If the
  process dies between that commit and `billing.close`, the redelivery is deduplicated and the orphan bills for ever. This is
  the same pattern as the T-173 duplicate cancel, so it is consistent, but here nothing else would ever notice it. No lock is
  held when `sub is None`, so the order could be: close first, then commit the event id, and roll back on failure.
- **S2, redundant provider calls.** Every later event for a deleted tenant calls `close` again. That includes the
  `customer.subscription.deleted` events that our own close produces, and renewals. Each call is a DELETE that gets a 404, so
  it is harmless. During a Stripe outage, though, each of these events answers 503 and queues for redelivery. With C1's
  tombstone, the close could run only for `starts_subscription` events, or the tombstone could note that the customer was
  already closed.
- **S3, concurrency test.** The race tests run the webhook inside the patched `close`, in one thread. That proves the re-read
  but not the lock. A threaded test, with the webhook blocked on the subscription row while deletion holds it and then
  seeing `sub is None` and closing the orphan, would pin the lock contract. My probe above shows the setup works.
- **S4, stale `provider_customer` after the checkout retry.** After the retry without `customer`, `subscriptions.provider_customer`
  still names the missing customer until the new checkout's webhook arrives. If the user abandons that checkout, every later
  checkout makes the extra failed call again. That is harmless, at one extra request each. Optionally clear it, or leave it
  documented as is.

## Lock and failure analysis (no issues found)

- **Lock order.** Deletion takes the subscription row (FOR UPDATE) and then deletes the tenant row, which needs FOR UPDATE on
  the tenant and on cascaded child rows. The webhook inserts `billing_events` (no foreign key), locks the subscription row,
  and only then takes the KEY SHARE locks on the tenant (inserting `billing_customers` or `pending_cancels`). A webhook
  waiting on the subscription row holds no tenant lock, so the two can't deadlock. `team.invite`'s FOR NO KEY UPDATE on the
  tenant never waits on the subscription, so deletion just queues behind it. `_fill_period_end` and the pending-cancel sweep
  lock either the subscription alone or `pending_cancels` alone.
- **The webhook after the deletion commits.** Under READ COMMITTED, a FOR UPDATE that was waiting on a row that then gets
  deleted returns nothing, so the webhook takes the orphan path. The deleted tenant's `billing_customers` rows are gone, so
  the live-owner guard doesn't stop the close.
- **Idle in transaction.** `db.commit()` runs before every round of provider calls. The lock is held only across the
  re-read and the cascade delete, with no network call inside it.
- **Partial failure.** A close that fails answers 503 with no transaction open. `closed` is local to the request, and closes
  are idempotent (a 404 counts as done), so a retry finishes the job. After 5 busy rounds the code rolls back and answers 503.
  Worst-case latency is bounded by 13 s per customer per round.
- **Tenant isolation.** The deletion queries filter on `tenant_id` and `provider`. The live-owner guard in the orphan path
  is tested. C1 is the gap.
- **Security and logging.** The new logs carry only `tenant_id`, with no provider text or customer ids. Path segments are
  now `quote`d in `close`. ORM queries only.
