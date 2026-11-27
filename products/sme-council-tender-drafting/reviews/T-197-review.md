# Review: p/sme-council-tender-drafting/T-197 (head a3d599b)

Reviewer run, 2026-11-27. Scope: `git diff main...HEAD` (12 files, +185/-13), fixes for T-185-review F1, F2, F3, S4, S6, S7, S9, S10.

## Verdict: PASS

No critical issues. All T-185 findings this branch was meant to fix are fixed, and tests cover each one.

## Evidence (re-run by the reviewer)

- Backend: `TEST_DATABASE_URL=postgresql+psycopg://...:5432/rv197 python -m pytest -q -o addopts=""` (Python 3.12, Postgres 16):
  **857 passed, 1 skipped**, 183.8 s.
- Migrations on a fresh DB: `alembic upgrade head` -> `alembic check` "No new upgrade operations detected" ->
  `downgrade -1` (0014 -> 0013 runs clean) -> `upgrade head` -> `check` clean. After the upgrade, `pg_constraint.confdeltype`
  is `a` (NO ACTION) for `fk_requirements_document` and `c` (CASCADE) for `fk_requirements_pack`. Downgrade puts back the
  CASCADE and drops the index, so the migration can be reversed.
- Frontend: `npx tsc -b` clean; `npx vitest run` **203 passed (6 files)**.
- 0012 revision: only the docstring header changed (`4eba32d390f9` -> `0012`). The `revision` variable already said `'0012'`, and
  0013's `down_revision` is `'0012'`, so the chain is unchanged.

## Checks the caller asked for

1. **Does NO ACTION allow pack and tenant cascades but refuse a direct delete?** Yes, on Postgres 16. Evidence:
   `test_deleting_the_pack_still_cascades_through_documents_and_requirements` (the pack delete commits, and no source
   documents, requirements, drafts or claims are left for tenant A, while tenant B keeps its rows);
   `test_evidence_tsv_is_generated_and_deleting_the_tenant_cascades` (the `_chain` fixture has a requirement citing the document,
   and the tenant delete commits); `test_deleting_a_document_that_requirements_cite_is_refused` (IntegrityError names
   `fk_requirements_document`, the requirement and draft survive, and the delete works once the requirement is gone).
   `maintenance.py`'s bulk `delete(Tenant)` takes the same DB cascade path, so it is covered too.
2. **Is `has_access(billing_enabled=True)` as a default safe?** Yes, it fails closed. When the argument is left out, the
   old full check runs. A caller that forgets it can never let a billing-on user bypass the trial. The worst case is that a
   demo tenant with billing off gets a 402 after 14 days, which is visible and easy to fix. Today's callers:
   `tests/vehicle.py:133` (passes the flag) and `routes/billing.py:65,190` (leave it out, but those routes are only mounted
   when billing is on, so the default is correct there). No production tender AI route exists yet. With billing off, only
   `trialing` and `active` get through; `canceled`/`past_due` still fall through to the normal check (tested).
3. **Test strength:** good. Each isolated FK test builds a row whose only bad reference is the one under test, and asserts
   the constraint name. Before this change, a failure on the pack FK could hide a missing document FK. The billing-off
   test drives the real HTTP path: the trial expires, summarize returns 200, then AIUsage is seeded and the next call returns 429
   `ai_daily_cap_reached`. The frontend test checks the whole privacy page body for `plan` / `bill you` / `payment provider`,
   and checks the dashboard for no trial countdown.

## Suggestions (non-blocking; for the slices that add routes)

1. `migrations/versions/20261127_0014_requirements_document_fk.py:7-10` and `app/backend/app/tender_models.py:77-78`: the
   reason given against RESTRICT ("could fail on ordering") was not reproduced. A small Postgres 16 test
   (parent -> doc CASCADE, parent -> req CASCADE, req -> doc RESTRICT) deleted the parent without error. NO ACTION is
   still the right choice, because it does not depend on trigger order and can be deferred. Change the wording to "NO ACTION
   so the check does not depend on the order of cascade triggers" rather than saying RESTRICT fails.
2. Cross-pack citation: nothing in the schema forces `requirements.source_document_id` to belong to the same pack as
   `requirements.pack_id`. If a requirement in pack P2 cites a document in pack P1, deleting P1 will now be refused. Either
   tighten the FK to `(tenant_id, pack_id, source_document_id) -> source_documents(tenant_id, pack_id, id)` (needs a matching
   unique key) or check it in the S2 requirement-write path.
3. The S2+ document-delete and pack-delete routes must turn this `IntegrityError` into a 409 with a clear message
   ("remove the requirements that cite this document first"), not a 500. Add a route-level test when the routes land.
4. `app/backend/app/billing.py:460-461`: future tender AI routes need to pass `billing_enabled=settings.billing_enabled`, or
   billing-off demo tenants will lose AI after 14 days. To stop each route from having to remember it, add a helper
   (`ai_access(sub, settings)`) or make `billing_enabled` a required keyword with no default. Then one shared gate covers
   every AI route, the way the vehicle route does now.
5. `app/DATA.md` `source_documents` row: also list the `created_by` user id (SET NULL) in the "what" column, as the
   other rows do for `edited_by` / `confirmed_by`.
6. `ai_cache` 90-day purge is documented but not coded (known, logged in NEXT.md). Make sure the slice that first writes
   the cache adds it, with a test.
