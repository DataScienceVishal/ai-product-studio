# Review: p/_starter/T-181 (T-179 M1, one Stripe customer per tenant)

- Branch head: `cb717930ead8f67692e4471f7bd846773f094108`, diff against `origin/main` (8 files, +301 / -13)
- Reviewer: reviewer agent, 2026-11-28
- **Verdict: PASS** (no must-fix items; four follow-ups below, S1 recommended as a new board task)

## Summary

The change does what T-179 M1 asked for:

1. **Reuse the customer.** `checkout` passes `customer_ref=sub.provider_customer`, but only when `sub.provider == billing.name`.
   `StripeBilling.create_checkout` sends `customer=` and no `customer_email`. Now a second checkout attaches to the existing customer and does not create a new one.
2. **Remember every customer.** In `_apply_update`, `_record_customer` inserts `(tenant, provider, customer_ref)` into the new
   `billing_customers` table. Unique `(provider, customer_ref)`, FK to `tenants` with cascade. The insert happens after the subscription row lock
   and before every early return, so takeovers, duplicates, stale events, never-activated events and unconfirmed actives are all
   recorded.
3. **Delete them all, fail closed.** `delete_account` closes the stored customer together with its subscription, then every other recorded customer at the
   current provider. If any call raises `AppError`, it answers 503 `billing_unavailable` and deletes nothing. The list stays, so a retry
   works: `_call` treats a 404 on DELETE as done, so customers already deleted on the first try do not block the retry.
4. **Cross-tenant guard.** A customer already recorded for another tenant is never stored for this one. `update.customer_ref` is
   cleared, so `subscriptions.provider_customer` cannot point at it either, and this tenant's deletion cannot delete the other
   tenant's customer.
5. **Migration 0012** creates the table and backfills it from `subscriptions.provider_customer`.
   `DATA.md` and `README.md` describe the behaviour.

## Evidence

- Full backend suite (branch worktree, Postgres 16, fresh `.venv` per README):
  `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider`: **838 passed, 1 skipped**, 1 warning (Starlette deprecation), 117 s.
- Migrations, on a scratch database `t181_review`:
  - I ran `alembic upgrade 0011`, seeded 4 tenants (stripe `cus_A`; mock with no customer; two tenants sharing `cus_SHARED`),
    then ran `alembic upgrade head`. Backfill result: `(t1, stripe, cus_A)` and `(t3, stripe, cus_SHARED)`. The NULL customer was skipped, and the
    `ON CONFLICT DO NOTHING` kept the shared customer on the first tenant only, so the migration did not fail.
  - `alembic check`: "No new upgrade operations detected." `downgrade 0011`, then `upgrade head`, then `check`: clean.
  - `gen_random_uuid()` is built in from PG13, and CI and local both use postgres:16, so the backfill is fine.
- Do the tests fail without the fix? I reverted each part on its own and ran `tests/test_billing_customers.py`:

  | Part reverted | Tests that fail |
  |---|---|
  | `routes/account.py` restored from main (old single-customer deletion) | 2 / 10 (`deletes_every_customer`, `failing_customer_delete_keeps...`) |
  | `_record_customer` call disabled | 5 / 10 |
  | checkout reuse removed (route and Stripe form) | 2 / 10 (`sends_the_existing_customer`, `route_reuses_the_stored_customer`) |
  | cross-tenant guard removed (`_record_customer` always True) | 1 / 10 (`never_touches_another_tenants_customer`) |

  Every behaviour in the change has at least one test that fails without it. The tests check outcomes (which customers
  were closed at the provider, which rows survive), not implementation details.

## Critical issues

None.

## Suggestions (should-fix as follow-ups; none blocks the merge)

### S1 (money and privacy, existing before this branch, narrow window): customers created around or after deletion still survive
- `backend/app/routes/billing.py:147-149` (`sub is None` branch) and `backend/app/routes/account.py:68-83`.
- Scenario A: the owner opens a first checkout (no stored customer, so Stripe creates a new one), deletes the account, and the open
  session (live 24 h) is then paid. The event finds `sub is None`, keeps the event id and changes nothing. The new
  customer, with an active subscription and a saved card, is kept for ever and is billed monthly with no tenant.
- Scenario B (race): deletion reads the list and commits, the provider calls run for several seconds, a webhook records a new
  customer row in that window, and then `db.delete(Tenant)` removes the row by cascade. That customer is never deleted.
- With this branch's reuse, later checkouts name the stored customer. Stripe should refuse to complete them once that customer is deleted, so the
  gap is mainly the first checkout.
- Fix: in the `sub is None` branch, when the event names a customer that no other tenant has recorded (or a
  `starts_subscription` ref), call `billing.close(customer, subscription)`. Answer 503 on failure so that Stripe redelivers. Add
  a test for "checkout completes after the account was deleted". This fits naturally with T-179 M3's "expire other open
  sessions" work.

### S2 (test gap): no migration test for 0012
- Earlier migrations have upgrade and downgrade tests in `tests/test_migrations.py:80-97`; 0012 has none. I checked the backfill by hand
  (above). Add `test_billing_customers_migration_backfills_upgrades_and_downgrades` that seeds a subscription with a customer
  at 0011, upgrades, asserts the row exists, and downgrades.

### S3 (availability): deletion time grows with the number of customers
- `close` uses `_call`'s defaults, 3 tries with a 20 s client timeout (`app/billing.py:260,266`). That is about 63 s worst case per customer,
  and the loop runs them one after another. With 3 customers and a slow Stripe, the request can pass 3 minutes, and a proxy
  may cut it off first. No DB transaction is open, and a retry is idempotent (404 counts as done), so nothing is corrupted. Consider a
  shorter timeout or fewer attempts for `close`, as T-174/T-180 did for `cancel_subscription`.

### S4 (minor): a stored customer that is gone at Stripe blocks checkout
- `backend/app/routes/billing.py:85`. If an operator deletes the customer in the Stripe dashboard, every later checkout sends a
  missing `customer` and gets 502 `billing_rejected` every time. Consider retrying once without `customer` on `resource_missing`, or
  at least note it in README's operator notes.

### Nits
- `_record_customer` adds the row without flushing. A concurrent insert by another tenant of the same `(provider, ref)` then raises
  `IntegrityError` at whichever later flush comes first. That is usually the final commit, which gives a 500 and a clean redelivery. But
  it can also happen inside the `begin_nested()` tombstone savepoint (`routes/billing.py` around line 175), where
  `except IntegrityError: pass` would silently drop the customer row. This is very unlikely. Flushing inside a savepoint in
  `_record_customer` would make the failure happen in a predictable place.
- `DATA.md`'s `billing_customers` row says "every provider customer id the tenant has had". In practice it holds the ones a
  processed event revealed. A bank-debit checkout that is still `incomplete` sends no recordable event until it resolves. Say
  "every customer a billing event named".
- `DATA.md`'s `subscriptions` row still says "the provider customer is deleted first". T-179 asked for that row to say exactly
  which customers are deleted. The new row covers it, so a cross-reference ("all customers in `billing_customers`") would
  be enough.
- Customers recorded under a different provider name than the current one are dropped by cascade without a call. This is fine for
  `mock`. Worth a one-line comment in case the studio ever changes provider.

## Security checklist
- Authorisation: unchanged. Checkout needs `verified_owner`, and deletion needs the owner and the password.
- Tenant isolation: the deletion query filters on `tenant_id` and `provider`. The cross-tenant guard is tested. Customer refs come only from
  signed webhooks or the tenant's own stored row, so a tenant cannot make the app send another tenant's customer id to checkout.
- Injection: ORM queries only. The migration SQL is static.
- Secrets and logging: the new ERROR logs carry only `tenant_id`, with no provider text and no customer ids.
- Idempotency: event dedup is unchanged. Recording is once per `(provider, ref)`. Deletion retries are idempotent.
