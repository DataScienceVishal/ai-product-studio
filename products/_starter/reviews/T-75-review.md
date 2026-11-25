# Review: p/_starter/T-75-billing-followups (commit 81d0c9b)

Reviewer run on the exact branch tree (HEAD 81d0c9b), diff `main...p/_starter/T-75-billing-followups`.
Scope: the T-74 review follow-ups S1 to S7 (`reviews/T-74-review.md`).

**Verdict: PASS**

## Summary

Every T-74 suggestion is addressed, and each change does what it says:

| T-74 item | Change | Checked |
|---|---|---|
| S1 past_due dead end | Owner-only "Manage billing" button in `Billing` (`frontend/src/pages/app.tsx:183-207`); past_due alert for owners and members; 409 text points at the button | 5 new vitest cases; build clean |
| S2 generic plans | `_PENDING = AIUsage.model == literal_column("'pending'")` used in the sweep and the in-flight count (`backend/app/ai.py:460`, `:468`, `:500`) | unit test on compiled SQL, plus a manual EXPLAIN (below) |
| S3 index lock | comment pointing to `CREATE INDEX CONCURRENTLY` in an autocommit block (migration 0007) | read |
| S4 Stripe portal setup | README note: save a default Customer Portal config, in test and live mode | read |
| S5 migrations test | `scratch_url` skips under `TEST_DATABASE_SHARED=1`; uses the conftest name shape and `_create_run_db` (marker comment) | ran in both modes; marker test asserts the comment |
| S6 dead `sqlite_where` | removed from the model | `alembic check` in `test_migrations.py` still clean |
| S7 portal idempotency key | comment explains it is random on purpose | read |

### Tests (exact tree 81d0c9b)

- Backend: **561 passed, 0 failed, 0 skipped** (`pytest`, junit: tests=561 errors=0 failures=0 skipped=0, 72 s, local Postgres 16).
  README's "561 passed" matches.
- Backend with `TEST_DATABASE_SHARED=1`, `tests/test_migrations.py`: both tests **skipped** with the new reason (was an error before).
- Frontend: `npx vitest run` **119 passed (119)**; `npm run build` OK (249.73 kB JS, 76.97 kB gzip).

### S2 evidence (generic plan)

Scratch DB, 200k `ai_usage` rows (0.1% pending), both indexes, `plan_cache_mode = force_generic_plan`:

- `model = $2` (old bound parameter): Bitmap Index Scan on `ix_ai_usage_tenant_created`, `Filter: (model = $2)`, cost 2302.
- `model = 'pending'` (new literal): Bitmap Index Scan on `ix_ai_usage_pending`, cost 31.

So the literal is what makes the partial index usable once psycopg switches to a prepared generic plan. The unit test
(`test_pending_is_a_sql_literal_so_the_partial_index_survives_generic_plans`) pins the SQL text, which is the right level:
it fails if someone swaps the literal back to `== "pending"`.

## Security

- **Owner-only on the server:** `POST /api/billing/portal` already depends on `verified_owner` (`routes/billing.py:65`),
  covered by `test_portal_is_owner_only`. Hiding the button for members is cosmetic only, as it should be.
- **CSRF:** the button calls the shared `api` helper, which sends `X-Requested-With: fetch`; the ASGI middleware in
  `app/main.py:40-52` refuses cookie-authenticated writes without it. The first vitest case asserts the header is sent.
- **Open redirect:** the frontend does trust whatever `url` the server returns (`window.location.assign(portal.url)`), the
  same pattern as the existing checkout redirect. The URL is not attacker-controlled: it is either Stripe's
  `billing_portal/sessions` reply (server-to-server over TLS with the secret key) or, for the mock, built from
  `settings.base_url`. The return URL comes from `APP_BASE_URL`, not headers (`test_portal_route_builds_return_url_from_settings_not_headers`).
  Not exploitable today; see suggestion 2 for defence in depth.
- **Tenant isolation:** unchanged; `test_portal_never_shows_another_tenants_customer` still passes.

## Critical issues

None.

## Suggestions (non-blocking)

1. **Mock provider: "Manage billing" lands on the dashboard silently.** `MockBilling.portal_session` returns
   `{base_url}/billing/mock-portal?customer=...` (`backend/app/billing.py:163`), but the SPA has no `/billing/mock-portal`
   route (`frontend/src/App.tsx:62-68` falls through to `<Dashboard>`). Before this branch nothing in the UI reached that
   URL; now an owner in dev, e2e or a mock-mode private demo clicks the button and is dropped on the dashboard with no
   explanation. Fix: add a tiny `MockPortal` page (like `MockCheckout`: "This is where Stripe's portal would open" plus a
   Back to billing link), or point the mock at `/billing?portal=mock` with a notice. Worth doing before any G4 demo that
   runs on the mock provider.
2. **Defence in depth on redirects.** Both `checkout.url` and `portal.url` are passed straight to `location.assign`. A
   two-line guard (`new URL(url).protocol === "https:"`, or `https:` / same-origin for the mock) would stop a
   `javascript:` URL if a provider reply or config were ever wrong. Low priority; the server is the trust boundary.
3. **Unverified owners see the button** and get a 403 `email_not_verified` alert when they click it. The message is
   clear, so this is fine; optionally hide or annotate the button when `email_verified_at` is null, as checkout does.
4. `test_migrations.py` imports private conftest names (`_BASE_NAME`, `_create_run_db`). Acceptable inside the test
   package; if more tests need scratch databases, move them into a small `tests/dbutil.py`.

## Maintainability

Naming and comments are clear (`_PENDING` carries the reason; the idempotency-key and CONCURRENTLY comments say why, not
what). Frontend tests check behaviour (request made, header sent, navigation target, error shown, button re-enabled,
disabled while pending, role-specific past_due copy), not implementation details. `vi.stubGlobal` is reset by
`unstubGlobals: true` in `vitest.config.ts`.
