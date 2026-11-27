# Review: T-185 (S1, starter copy and data model)

Branch `p/sme-council-tender-drafting/T-185`, head 3efc3ba, against `origin/main`. Reviewer: `reviewer` (opus), 2026-11-27.

## Verdict: PASS

The S1 bar in DESIGN section 9 is met, and so is R7 (sections 3 and 13). None of the findings below blocks the merge.
Findings 1 to 3 should be fixed in S2 at the latest. The rest are suggestions.

## What I checked and how

- I diffed `products/_starter` against `app/`, leaving out node_modules, .venv, dist and caches. Only the files below
  differ from the starter, and I read each of them: `tender_models.py`, `scoped.py`, `tender_export.py`, migrations 0012
  and 0013, `main.py`, `config.py`, `routes/account.py`, `routes/health.py`, `textsafe.py`, `tests/vehicle.py`,
  `tests/conftest.py`, `test_tender_model.py`, `test_billing_flag.py`, the frontend `App.tsx`, `api.ts`, `pages/app.tsx`
  and `pages/legal.tsx`, `DATA.md` and `README.md`. The other changes are comment and copy renames.
- **Backend suite, my own run:** a fresh database `rv185_test` on local Postgres 16, using the venv at `/tmp/v185`.
  Command: `TEST_DATABASE_URL=... python -m pytest -q -o addopts=""`. Result: **852 passed, 0 failed, 1 warning** (a
  starlette deprecation) in 182.6 s. This matches NEXT.md.
- **Migrations, my own run:** on a fresh database `rv185_mig`, `alembic upgrade head` then `alembic check` reported "No
  new upgrade operations detected". `downgrade 0011`, `upgrade head` and `check` were clean again. In `\d requirements`
  both composite foreign keys are present with ON DELETE CASCADE.
- **Frontend, my own run:** `npx tsc -b && npx vitest run`: **202 passed (6 files)**.
- **Ported tests:** I compared the number of `assert` lines and `test_` functions in each of the 12 ported files against
  the starter, and they are identical in every file. I also read a rename-normalised diff of test_ai and test_hardening.
  The only changes are names, the `billing_enabled` key in the `/api/config` equality check, and the member-export
  assertion. That assertion now checks that `notes_written` is absent, which is correct now that the field has been
  removed.

## The checks you asked for

| Area | Result |
|---|---|
| 12 tables and composite FKs | All 11 DESIGN tables plus `evidence_counters` are there, with the DESIGN columns. Every child links to its parent with `(tenant_id, parent_id) -> parent(tenant_id, id)`, and every parent has `UNIQUE (tenant_id, id)`. No child also has a single-column FK to its parent that would bypass the check. Nullable `pack_id` and `source_document_id` use MATCH SIMPLE, so a null skips the check, which is right for evidence documents. The `tsv` column is generated with a GIN index. `ai_cache` has the primary key `(tenant_id, key)`, so it is per tenant. |
| `scoped.py` | It is correct and needs no request object, so workers can use it. Another tenant's row and a missing row both raise the same `AppError(404)`. |
| Account export (R7) | It covers all 9 customer-content tables, scoped to the tenant. `ai_tasks`, `ai_cache` and `evidence_counters` are left out, and `tsv` is skipped. The `notes` key is gone. It is still owner-only (`Depends(owner)`). Test: `test_account_export_covers_the_new_tables_and_only_own_rows`. |
| Note removal | No trace of `Note`, `/api/notes` or `notes` is left in `app/` or `frontend/src` code. Migration 0013 drops the table, and its downgrade recreates the table with its index. The dashboard test file was deleted: it only tested the Note UI. |
| `billing_enabled` | When the flag is off, `billing.router` is not mounted. The webhook path is still listed in `CSRF_EXEMPT` (main.py:36), but that is harmless: an exempt path that does not exist returns 404 (tested). `app.state.billing` is still built, so account deletion and the maintenance cancel sweep still work. The trial clock comes from `auth.py` and does not depend on billing. `/api/config` reports the flag. The SPA fails closed (`billingEnabled = false` until a successful config) and hides the Billing nav link, the billing pages, the "Choose a plan" link and every price. The Help and Terms copy no longer mentions paid plans. |
| `create_app(extra_routers=...)` | The default is `()`. The production entry point `__getattr__("app")` calls `create_app()` with no arguments, and nothing reads the parameter from settings or the environment. Production config cannot reach it. |
| Test vehicle | `tests/vehicle.py` is the Note route line for line: the same rate limit, `has_access`, email-verification gate, `LIMITED_PROVIDERS` plan choice, `ensure_ai_enabled`, `reserve` with every cap argument, slots, settle on both failure paths, re-read after the call, and the 409 on edit. It uses its own `DeclarativeBase`, so it is in no model and no migration, and `alembic check` stays clean. It adds real foreign keys to `tenants` and `users`, so the cascade tests still prove something. The AI cap, cost guard and tenancy guarantees are still tested to the same strength. |

## Findings

1. **`app/DATA.md:14`: the retention table no longer lists any customer content.** The `notes` row was removed, but none
   of the 12 new tables was added. As written, DATA.md says the product stores nothing a customer typed. DESIGN section
   3 says "Retention (to add to the product's DATA.md): all of these tables are customer content ...", including the
   90-day `ai_cache` purge and `signoffs.reviewer_name` as the only new personal data. *Fix:* add one row per table, or
   one grouped row, with what each holds, why, when it is deleted (pack or document deletion, cascade, the 90-day cache
   purge) and who can delete it.
2. **`backend/app/tender_models.py:77` and `:90`: deleting a source document also deletes its requirements, their drafts
   and their claims.** `fk_requirements_document` is ON DELETE CASCADE. A user who removes one tender PDF, for example to
   replace it with a corrected version, loses every requirement extracted from it and all the drafting work built on
   them. That is a data-integrity trap that S2 (document delete) will expose. *Fix (S2):* decide on purpose. Either
   refuse to delete a tender document that has requirements, or use `ON DELETE SET NULL (source_document_id)` (Postgres
   15 and later) and mark the quote unverified. Add an index on `requirements (tenant_id, source_document_id)`: there is
   none, so the cascade or set-null runs a sequential scan.
3. **`backend/tests/test_tender_model.py:71-78`: two of the composite foreign keys are never tested on their own.**
   `fk_requirements_document` is never exercised, because the Requirement cases fail on `pack_id` first.
   `fk_exports_signoff` is not tested alone either, because the ExportRecord case also uses tenant A's pack. If either
   FK were dropped, every test would still pass. *Fix:* add one case per FK where only that column points at another
   tenant's parent, and assert the constraint name (`"fk_requirements_document" in str(err.value)`).

## Suggestions

4. The test name `test_duplicate_document_hash_is_refused_per_tenant_only` (`test_tender_model.py:97`) says "only", but
   the test never shows that tenant B can store the same hash. Add the positive half.
5. `tender_export.py:34` has no ORDER BY and no size bound. Sort each table (`created_at`, or `seq` / `page_no`) so
   exports are deterministic. `document_pages.text` across every pack will grow large. Stream the export, or write it to
   a file, before real tender volumes arrive (a later slice).
6. The trial clock with billing off: after `trial_days` (14), `has_access` fails and the AI routes return the message
   "Choose a plan to keep using AI features" (vehicle.py:134, copied from the starter; also deps.py:62). With billing
   off there is no plan to choose. The S3 to S5 AI routes need different wording, and the demo seed tenant needs a
   trial end date (or an exemption) that will not lapse in the middle of the handover.
7. `pages/legal.tsx:18` still says "to bill you", and line 17 says "your plan". This is minor billing copy left over
   with prices off.
8. Nothing in the schema enforces the status and kind values, or the rule that a `kind='evidence'` row has a null
   `pack_id` and a `kind='tender'` row has a non-null one. CHECK constraints would make the database refuse bad states,
   in the same spirit as the composite FKs.
9. `test_billing_flag.py` covers routes, config and the trial with billing off, but every AI cap test runs with
   `billing_enabled=True`. One vehicle summarise test under the off settings would cover the production configuration.
10. The docstring of migration 0012 says `Revision ID: 4eba32d390f9`, but the revision is `'0012'`. This is cosmetic.
11. `/api/account/me/export` now returns only the profile. Once S7 sign-off exists, a member's typed `reviewer_name` and
    `reviewer_user_id` rows are personal data about that member. Consider including their sign-offs (UK GDPR access).

## Not verified

- I did not run Playwright (`tests/e2e/core_flow.cjs`), the `infra/test-deploy-workflow.sh` script or the CI
  bicep/docker jobs. NEXT.md says the same.
- No CI workflow covers this product folder yet (`.github/workflows` has only `_starter-ci.yml`). So "CI green" in the
  S1 Done line rests on local runs: mine and the builder's.
