# Review: p/_starter/T-74-billing-followups

Reviewer run, 2026-11-25. Diff: `git diff origin/main...origin/p/_starter/T-74-billing-followups` (T-73 merge, already PASS in
`T-73-review.md`, plus 0a9ffc5 with the T-73 review follow-ups S1, S2 and S3 and the pending-usage partial index).

## Verdict: PASS

## Evidence

- Full backend suite in a clean detached worktree of the branch with a fresh venv from `requirements-dev.txt`, local Postgres:
  **558 passed, 1 skipped** (`tests/test_spa.py:103: frontend not built`, the same skip as before) in 62 s.
- Mutation checks (each change made in the scratch worktree only, then reverted):
  | Mutation | Test that failed |
  |---|---|
  | past_due refusal back to unconditional (`if sub.status == "past_due":`) | `test_past_due_from_another_provider_does_not_block_checkout` |
  | portal dependency `verified_owner` replaced by `current` (any signed-in member) | `test_portal_is_owner_only` (200 != 403) |
  | return URL built from `request.base_url` (Host header) | `test_portal_route_builds_return_url_from_settings_not_headers` |
  | portal looks up any subscription that has a customer, not this tenant's | `test_portal_never_shows_another_tenants_customer` |
  | migration 0007 without `postgresql_where` | `test_pending_usage_partial_index_upgrades_and_downgrades` (no WHERE in indexdef) |
- `test_migrations.py` runs the whole chain on a scratch Postgres database: base to 0006 to head, `alembic check` (models and
  migrations agree), head to 0006, then to base. Upgrade and downgrade are both exercised.

## What was checked

- **S1 provider-aware past_due** (`app/routes/billing.py:45`): refusal now requires `provider_ref` and
  `sub.provider == billing.name`, mirroring the `already_subscribed` check. Right behaviour: a mock-era past_due row no longer
  blocks a Stripe checkout. The refusal happens before `create_checkout`, and a test asserts no provider session is created.
- **S2 portal** (`app/routes/billing.py:64-74`):
  - Auth: `verified_owner` (owner role and verified email). Member gets 403 and anonymous gets 401, both tested.
  - Tenant isolation: the subscription comes only from `me.tenant.id`, with no client-supplied customer id. Tested across tenants.
  - Open redirect and header trust: `return_url` is `settings.app_base_url + "/billing"`, never from the request. Tested with a
    hostile Host and Origin. The response URL comes from Stripe (or the mock's own base URL). `/billing` is a real SPA route.
  - Wrong provider or no customer gives 409 `no_billing_customer`. The rate limit (10 per tenant) runs after auth. The DB
    transaction is committed before the provider call. The route is sync `def`, so the blocking httpx call runs in the threadpool.
  - CSRF: it is a POST under the existing global CSRF middleware (tests use the CSRF-enabled client).
  - `StripeBilling.portal_session` sends the right form to `/v1/billing_portal/sessions`. An incomplete reply gives 502
    `billing_rejected`, and a 4xx raises. Both tested.
- **S3 tests**: no-session-on-refusal, Stripe `unpaid` maps to past_due and is refused, and recovery on the same ref moves the
  error to `already_subscribed`. They test behaviour, not implementation.
- **Partial index**: matches both pending queries in `app/ai.py` (`release_stale_reservations` at about line 464, and the
  in-flight count at about line 495). The migration chain is linear (0006 is head on main, and no other `_starter` branch adds a
  0007). Downgrade drops the index cleanly. SQLite is not a supported backend (`Database` rejects sqlite URLs, see
  `test_db_entra.py:87`), so there is no SQLite migration path to break.

## Critical issues

None.

## Suggestions (non-blocking; S4 is worth doing before the first product uses the portal)

1. **S1: the past_due message points at a UI that doesn't exist yet.** The 409 says "Update your card in the billing portal",
   but there is no "Manage billing" button until the frontend follow-up in NEXT.md lands. Make that the next `_starter` task
   so products copied from the starter don't ship a dead-end message.
2. **S2: a partial index may be skipped under generic plans.** SQLAlchemy binds `'pending'` as a parameter. Once psycopg
   prepares the statement (after 5 executions) and Postgres switches to a generic plan, the planner cannot prove
   `model = $1` implies `model = 'pending'`, so it falls back to `ix_ai_usage_tenant_created`. That is still correct and
   still fast, but the new index then does nothing. Option: use a literal (`AIUsage.model == literal_column("'pending'")`),
   or check with `EXPLAIN` under `plan_cache_mode = force_generic_plan` once ai_usage has real volume.
3. **S3: migration lock.** `CREATE INDEX` (not `CONCURRENTLY`) blocks inserts on `ai_usage` while it builds. That is fine
   at starter scale. Products with a large ai_usage table should use `op.create_index(..., postgresql_concurrently=True)`
   inside `op.get_context().autocommit_block()`. Add a one-line comment to the migration.
4. **S4: Stripe portal setup.** `POST /v1/billing_portal/sessions` returns 400 until a default Customer Portal configuration
   is saved in the Stripe dashboard (test and live mode are configured separately). Add that next to the dunning note in the
   README "Billing" section. Today it would show up as a 502 `billing_rejected` with no hint why.
5. **S5: `test_migrations.py` under `TEST_DATABASE_SHARED=1`.** It always runs `CREATE DATABASE`, so in the
   no-CREATE-right mode the conftest supports, it errors instead of skipping. Skip when `SHARED`. Also, the `mig_<hex>`
   name lacks the ephemeral marker and base-name prefix, so a killed run leaks it past the stale cleanup. Reuse
   `_create_run_db` or the marker.
6. **S6: `sqlite_where` in the `AIUsage` model is dead code**, because SQLite is rejected at startup. Drop it, or keep it
   with a comment, so the model and migration don't look inconsistent.
7. **S7: the per-call random idempotency key on `portal_session`** gives no idempotency; it only satisfies `_call`. That is
   harmless, but a comment saying so would stop someone "fixing" it into a shared key that returns a stale session URL.
