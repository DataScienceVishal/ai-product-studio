# STATUS (T-193, slice S9: eval harness and demo seed) - reviewer CHANGES addressed, awaiting re-review

Branch `p/sme-council-tender-drafting/T-193`. Not merged. No migrations, no edits under `app/tender/`. No live model calls: the only
provider the harness builds is `ScriptedFakeAI`, and `--live` is refused (exit 3).

## Done (under `products/sme-council-tender-drafting/eval/`, plus `EVAL.md`)
- Original slice: `budget.json` (Q-19 A), `ledger.py`, `score.py`, `sample.py`, `seed.py`, `run.py`, `EVAL.md` template, tests.
- Review fixes M1-M7: preflight covers only the unfinished scored phases (M1); results committed, only `results/dry/` ignored, live phase
  with ledger rows and no results file refused (M2); A4 uses the app's `split_sentences`, gap-only sentences excluded, defined in EVAL.md (M3);
  A7 uses the app's `count_words` (M4); A6a word-token overlap rule pre-registered, with mutants (M5); durable `hold` rows under
  `fcntl.flock`, unsettled holds counted at worst (M6); E2/E3/E4/T3 raise `PhaseNotReady` before the first item without a claimcheck (M7).
- Should-fix 1-10, 12, 13: claimcheck cap from `app.tender.draft.CHECK_CAP` (the T-190 claimcheck spec uses the same constant); budget pinned
  in code and prices/caps checked finite and above 0; `ceil` on the worst-case charge; fake rows dropped only on dry ledgers; failed items
  recorded with their error code, infrastructure errors stop the phase; provider headroom asserted; `drafting_heldout` in manifest;
  `ai_cache` cleared before every item of T2, T3, R2 with a cacheable provider; seed refuses empty/escaping manifests, checks login, skips
  existing packs; A3 ref matching skips question items; A6a false-flag rate reported; unreadable test split.
- Security: path containment in `seed.py`; `run.py` refuses a non-local `DATABASE_URL` unless `--allow-remote-db`.

## Left
- Should-fix 11 (minimum text similarity on ref-only A1 matches): skipped, optional; ref-first matching is pre-registered in EVAL.md.
- Claim check: `run.py` takes a `claimcheck(budget, text, hits)` callable; wire T-190's `app/tender/claimcheck` when it merges.
- Inputs not yet present (qa, D3 and Q-20): `eval/keys/<pack>.json`, `trap_set.json`, `dev_trap_set.json`, `fixture_drafts.json`,
  `demo-data/packs/` + `manifest.json` {"demo", "heldout", "drafting_heldout"}.
- A scorer wrapper that prints the bar table; the live provider path (L1); R1/R2/T2 drafting steps (plans cover extraction only).

## Verify
`cd app/backend && TEST_DATABASE_URL=... python -m pytest -q -o addopts="" tests/test_tender_eval.py`; `python -m eval.run config` from the product dir.

# STATUS (T-198, S4 review leftovers)

**Done**
- Runner `FAILURE_HOOKS` (kind -> hook), run when a task is failed as `attempts_exhausted`. Extract: pack back to `review`/`uploaded`. Draft: a pack stuck in `checking` goes back to `drafting`. A crashing hook is logged, never breaks the runner.
- F7: migration 0017 adds UNIQUE (tenant_id, pack_id, seq) (renumbers existing duplicates first); `add_requirement` and the extract write both lock the pack row, so max+1 cannot race.
- F10: out-of-range or negative `source_page` is clamped to the document and flagged `page_out_of_range`.
- F5: limit check finds the quote on the raw text (whitespace tolerant), searches from the quote forward to the next numbered question, no page-wide fallback once the quote is located; `stated_page_limit` adds "N sides of A4"/"N pages".
- Duplicate `text` import removed from `tender_models.py`.
- F9 decision: keep ONE extract task per pack for the demo (per-tenant cache makes a retry cheap; per-chunk tasks only buy a progress bar). Revisit if `/status` needs chunk progress.

**Left**
- Per-chunk tasks (F9) and chunk progress in `/status`.
- Migration 0017 duplicate-renumber SQL was not exercised on a table that actually holds duplicates.

**Verify**
- `pytest tests/test_tender_extract.py` (27 tests); alembic upgrade, check, downgrade -1, upgrade, check was clean.

# STATUS (T-189, slice S5: drafting) - code done, awaiting reviewer PASS

Branch `p/sme-council-tender-drafting/T-189`. Not merged. Migration 0016 (drafts.outside_ids int[], drafts.flags text[]); alembic
upgrade, check, downgrade -1, upgrade, check clean. No live model calls (ScriptedFakeAI / fakes only).

## Done
- `app/tender/draft.py`: `DraftOutput`, `DRAFT_SPEC` (low effort, 4000 cap), `draft_answer()` (pure of DB sessions; the harness can
  call it with wider `Limits`), `draft_handler` registered in `runner.HANDLERS["draft"]`, `save_version`, `fit_to_limit`.
  Empty retrieval (or below `RETRIEVAL_FLOOR`) -> gap marker draft, flag `no_evidence`, model never called, no budget hold.
  Citations: `[E-n]` in the text split into `cited_ids` (in the retrieved set) and `outside_ids` (flag `citation_outside_set`, marker
  kept in the text for S6 to mark unsupported). Over the word limit: one "shorten" retry (flag `shortened`), then trailing sentences
  dropped (flag `trimmed`); a refused retry falls through to the drop. Word count excludes `[E-n]`, includes gap markers.
- Routes (routes/tender.py): `POST /packs/{id}/draft` (202, idempotent, 409 until confirmed / when nothing is left to draft),
  `POST /requirements/{id}/redraft` (202, 5 AI drafts per requirement per 24 h -> 429 `redraft_limit`), `PUT /requirements/{id}/draft`
  (user edit = new version, author=user, optional `base_version` -> 409 `stale_version`), `GET /requirements/{id}/draft[?version=]`,
  `GET /requirements/{id}/evidence`. Cross-tenant ids are 404. Signed or exported packs are 409.
- App-path sizing (R3): passages capped at 5 x 1000 chars, question 1500 chars. `draft_reservation` + `check_reservation` for a typical
  pair is under 30k (test); the largest draft alone reserves under 21.5k.
- Tests: `tests/test_tender_draft.py` (16).

## Design decisions
- One task per pack drafts every confirmed `question` without a draft; each draft commits as made, so a daily-cap refusal part-way keeps
  the finished ones and a re-run continues (cache makes repeats free).
- Draft status stays `drafted` on edit; the check (S6) sets `checked_ok` / `blocked`. Edits to a `ready` pack do not yet reset it (S6/S8).
- The claimcheck sizing constants (`CHECK_CAP`, `CHECK_SYSTEM_BYTES`) live in draft.py until S6 defines the real spec.

## Left
- Claim check, pack status `checking`/`ready` transitions and sign-off voiding on edit (S6, S8). No frontend. `RETRIEVAL_FLOOR` is 0 until L1 tuning.
- Redraft limit counts drafts, so a pack-wide draft also uses one of a requirement's 5.

## Verify
`cd app/backend && TEST_DATABASE_URL=... python -m pytest -q -o addopts="" tests/test_tender_draft.py` then the full suite.
Full suite NOT completed in the T-189 session (time limit; it ran about 10 tests a minute here): first 30% had no failure; S5 (16) and
S4 extract (18) files green. Reviewer must run the full suite (expect 947 + 16).

## Review fixes (T-189, after reviewer CHANGES)
- F1: the shorten retry now uses `SHORTEN_SPEC` (instruction in the system prompt); only `word_limit` and `previous_answer` are data. Test added.
- F2: `/evidence` and the draft handler both call `search_evidence(limit=APP_PASSAGES)`, so the user sees exactly what drafting used. Test added. DESIGN line (8 passages) and DECISIONS.md still to update by the Lead.
- F3: retry re-sends no passages and caps output at 1,500 tokens (reservation about 6.2k vs 14.9k). Sizing test checks draft + retry + re-check against 30k with settled use.
- F4: the save session reads the pack `FOR SHARE` and stops (no version) unless the pack is in `DRAFT_PACK_STATES`. Test added.
- Nits 5-10 not done. Full suite: 967 passed, 1 skipped.

# STATUS (T-188, slice S4: extraction and checklist API) - code done, awaiting reviewer PASS

Branch `p/sme-council-tender-drafting/T-188`. Not merged. Migration 0015 (requirements.model_json JSONB, flags text[]); alembic
upgrade, check, downgrade -1, upgrade, check clean. No live model calls.

## Done
- `app/tender/extract.py`: `ExtractItem` / `ExtractOutput`, `EXTRACT_SPEC` (low effort, 6000 cap), `make_chunks` (5 pages, 1 overlap),
  quote-on-page check (normalised substring, amber = `quote_verified=false`), word-limit regex cross-check (flag `limit_mismatch`),
  `merge_items` (same ref, or trigram similarity >= 0.9 on the same or adjacent page), `extract_handler(sessions, task, heartbeat,
  provider)` registered in `runner.HANDLERS["extract"]`. One task per pack runs all chunks through `run_task` with `AppBudget`.
  Re-running replaces only the model-origin, still-proposed rows.
- Routes (routes/tender.py): `POST /packs/{id}/extract` (202, idempotent), `GET /packs/{id}/status`, `GET /packs/{id}/requirements`,
  `POST /packs/{id}/requirements` (origin=user), `PATCH /requirements/{id}` (keeps `model_json`, sets `edited_by`, origin stays model),
  `POST /packs/{id}/confirm`. Cross-tenant ids are 404. Signed or exported packs are 409.
- App-path cost (R3): no special code; a real chunk reserves more than the trial daily cap, so `AppBudget.hold` refuses before the
  provider is called, and the task ends `failed` with `ai_daily_cap_reached`. Tested with an azure-named provider and large pages.
- Tests: `tests/test_tender_extract.py` (10). Full backend: 947 passed, 1 skipped (18 extract tests).

## Review fixes (reviewer CHANGES, 1-4, 6, 8)
A failed or refused extraction resets the pack (`review` if it has live items, else `uploaded`); confirm now also accepts `uploaded`
(hand-written list). A re-run deletes only origin=model, proposed, unedited rows and dedupes new items against every surviving row
(edited, confirmed, removed, user). `POST /extract` is 409 unless the pack is uploaded, extracting or review. Same-ref merge needs a
non-blank ref on the same or an adjacent page. ORM `flags` has `server_default '{}'`.
Reviewer items left: 5 limit cross-check can flag fine items; 7 `seq` max+1 without a lock or unique constraint; 9 one task per pack;
10 `source_page` out of range is stored as is. A worker killed without a clean failure (attempts_exhausted) still leaves `extracting`.

## Left
- Deployment must set `AI_WORKER_THREADS=2` for the runner to start (default 0); without it extraction tasks stay queued.
- Extraction is one task per pack, not one per chunk (DESIGN 4.6 fan-out): a crash retries the whole pack once. Per-chunk tasks
  would also make progress visible in `/status`.
- Requirements are not yet checked against deleted documents beyond the existing FK; `ensure_requirement_document` is not used by
  the model rows (they come from the pack's own documents).
- No frontend. No e2e. Merge across multiple tender documents only dedupes inside one document.

## Verify
`cd app/backend && TEST_DATABASE_URL=... python -m pytest -q -o addopts="" tests/test_tender_extract.py` then the full suite.

# STATUS (T-187, slice S3: AI layer and job runner) - code done, awaiting reviewer PASS

Branch `p/sme-council-tender-drafting/T-187`. Not merged. No migration. No live model calls.

## Done
- `ai.py`: `complete(..., *, json_schema=None, effort=None)` on the protocol, FakeAI and AzureOpenAI (Responses: `text.format`
  strict json_schema; chat: `response_format`; per-call `effort` validated against REASONING_EFFORTS, None keeps the instance value);
  `AIUnavailable.reason` / `.truncated`; `build_provider(settings, timeout=, deadline=)` and `build_worker_provider(settings)`
  (settings `worker_ai_timeout_seconds` / `worker_ai_deadline_seconds`, default 180, max 600; request path keeps 20 / 25).
- `app/tender/llm.py`: `run_task(spec, payload, tenant_id, budget, *, provider, sessions, allow_double_cap, before_call)`; key =
  sha256 of the canonical request computed before the nonce (R1); per-tenant `ai_cache`; `AppBudget` (reserve/settle; the harness's
  `LedgerBudget` is S9); one repair retry on invalid JSON; truncation = `TaskFailed("ai_truncated")` in the app, one retry at 2x cap
  only with `allow_double_cap=True` (harness); `strict_schema()` makes a Pydantic schema Azure-strict.
- `app/tender/scripted_ai.py`: `ScriptedFakeAI` recorded (`fixtures/recorded/<task>/<key>.json`, `{"output": {...}}`) and heuristic
  (by schema title ExtractOutput / DraftOutput / ClaimcheckOutput; other schemas get a schema-valid skeleton). Refuses an
  `eval` directory. Its answers are not written to `ai_cache` (`cacheable = False`).
- `app/tender/runner.py`: `claim_next` (FOR UPDATE SKIP LOCKED, queued or expired lease), `extend_lease` (handlers call
  `heartbeat()`), `run_one`, `Runner` threads; max 2 attempts then `attempts_exhausted`. `HANDLERS` registry is empty: S4 to S6 register.
- `ai_access(sub, settings)` in billing.py; the test vehicle uses it. 90-day `ai_cache` purge in maintenance.py; DATA.md row updated.
- Tests: `tests/test_tender_ai.py` (23). Full backend: 928 passed, 1 skipped (after review fixes; 898 + 30).

## Design decisions
- ScriptedFakeAI recordings are looked up by `run_task` through `provider.recorded_answer(task, key)` because `complete()` only sees
  nonce-wrapped text. Recorded answers cost 0 and hold no budget.
- Runner threads default OFF (`AI_WORKER_THREADS=0`); set 2 in the deployment once S4 registers the extract handler. Lease
  `AI_TASK_LEASE_SECONDS` 600.
- Handlers must build their provider with `build_worker_provider(settings)`.

## Review fixes (reviewer CHANGES at 2c107cc)
C1 runner fenced on (attempts, status=running); `extend_lease` raises `LeaseLost`, `_finish` drops a stale result; C2 `before_call` runs
before `budget.hold`; injection rule is in the cache key; repair text echoes only `[A-Za-z0-9_]` locations; `Runner` builds the worker
provider and passes it as the 4th handler argument (handler signature is now `(sessions, task, heartbeat, provider)`); corrupt fixture
-> `TaskFailed("ai_invalid_output")`.
Reviewer suggestions left: 1 real SKIP LOCKED test with a held row lock; 2 failed tasks record 0 tokens on `ai_tasks`;
5 `reserve()` in-flight window is 2 min but worker calls may take 180 s (note for S4).

## Left
- No HTTP route enqueues tasks yet (S4). Billing routes still call `has_access` directly (they only act on paid subscriptions).

# T-186 review fixes (reviewer CHANGES at 1cceaba)

Tests after fixes: backend 898 passed, 1 skipped.
Fixed: F1 process-wide `BoundedSemaphore` (`parse_workers`, default 1, max 2) around the worker, non-blocking, 503 `busy`; the read
transaction is rolled back before parsing (no connection idle in transaction); F2 every zip entry is scanned for DOCTYPE/ENTITY
in UTF-8, UTF-16 and UTF-32 (any case, any name); F3 macro refusal also by `[Content_Types].xml` (macroEnabled, vbaProject); F4 caps
(pack size, pages per day, duplicate sha) are rechecked after a per-tenant advisory lock; F5 RLIMIT_FSIZE, NPROC, NOFILE; F11 bidi and
zero-width characters stripped from filenames.
Left: F6 (image-only page rule is DESIGN 4.1; Lead decision), F7 candidate cap 100 (tuning slice), F8 (harmless), F9 DESIGN section 5
delete path wording and member-may-delete decision (Lead), F10 soft vs hard evidence delete (decide before S6). Deleting a document still
refunds its pages for the day (rolling window counts live rows only).

# STATUS (T-186, slice S2: ingest and retrieval) - code done, awaiting reviewer PASS

Branch `p/sme-council-tender-drafting/T-186`. Not merged.

## Done
- Tests: backend 892 passed, 1 skipped (857 before + 35 in test_tender_ingest.py); alembic up, check, down -1, up, check clean (no new migration).
- Per-route 15 MB limit: `BodyLimit` takes a path table (`UPLOAD_PATHS` in main.py); other routes keep 1 MB. Settings `upload_*`.
- `app/tender/ingest.py`: magic-byte sniffing (PDF, ZIP/DOCX, OLE = encrypted, evidence-only strict UTF-8 text), fixed refusal codes
  with 415/422 messages, worker runner (`python -I parse_worker.py`, empty env, 45 s wall, temp file removed).
- `app/tender/parse_worker.py`: standalone (stdlib, pypdf, python-docx only); RLIMIT_AS 512 MiB / CPU 30 s set before the parsers load;
  refusals: encrypted, macro (.docm), zip bomb (entries, 50 MB total, ratio 100), XML DOCTYPE/ENTITY (XXE), too many pages (60),
  image-only (tender: any page under 30 chars; any file under 30 chars total). DOCX pages: `docx_break` or `docx_block`; text: `text_block`.
- `app/tender/chunking.py` (120 to 400 words, headings, pages), `app/tender/evidence.py` (E-n counter under an advisory lock, never
  reused; FTS OR query; must-have token boost; top 8, at most 3 per document; tenant_id in SQL).
- Routes `app/routes/tender.py`: packs create/list/delete, pack documents upload/list, evidence upload/list, `DELETE /api/documents/{id}`,
  `GET /api/evidence/search`. Upload caps: 10/hour and 300 pages/day per tenant, 40 MB per pack, duplicate sha256 is 409.
- T-197 leftovers: delete routes map fk_requirements_document to 409 `document_in_use`; `ensure_requirement_document` (422
  `document_not_in_pack`, for the S4 requirement write path); DATA.md `created_by`; migration 0014 and model comment wording.
- requirements.txt / requirements-dev.txt regenerated with `uv pip compile --generate-hashes` (adds pypdf, python-docx, python-multipart,
  lxml; dev adds reportlab for PDF fixtures).

## Left (next slices)
- Rejected files are not stored (no `status=rejected` rows); S7 UI should show the refusal message from the 4xx.
- No retrieval floor yet (`min_score` param exists, default 0), to be tuned with the demo packs (DESIGN 4.2).
- `ai_cache` purge still not coded. Frontend untouched. Docker image and e2e not run here.

## Verify
`cd app/backend && TEST_DATABASE_URL=... python -m pytest -q -o addopts=""` (Postgres 16). New tests: `tests/test_tender_ingest.py`.

# STATUS (T-197, review fixes for T-185): all items done, tests green

F1 DATA.md rows, F3 isolated FK tests, S4 cross-tenant sha256, F2 migration 0014 (FK NO ACTION + index; not RESTRICT,
which can fail pack/tenant cascades on ordering), S6/S7/S9 billing-off trial and legal copy and cap test, S10 docstring.
Backend 857 passed 1 skipped; alembic up/check/down -1/up/check clean; frontend tsc clean, vitest 203 passed.
The ai_cache 90-day purge step is documented but not yet coded (lands with the slice that writes the cache).

# NEXT (T-185, slice S1) - checkpoint

Branch `p/sme-council-tender-drafting/T-185`. Not merged; reviewer PASS needed.

## Done
- Starter copied to `app/` (backend, frontend, infra, scripts, tests; no starter ADR/reviews).
- `backend/app/tender_models.py`: the 12 DESIGN section 3 tables (tender_packs, source_documents, document_pages,
  requirements, evidence_counters, evidence_items with generated `tsv` + GIN, drafts, claims, signoffs, exports,
  ai_tasks, ai_cache). Child tables use composite FKs `(tenant_id, parent_id) -> parent(tenant_id, id)`; parents have
  `UNIQUE (tenant_id, id)`. Registered from the end of `models.py`.
- Migration `0012_tender_tables` (autogenerated, up/down tested, `alembic check` clean).
- `backend/app/scoped.py`: `scoped(model, tenant_id)` and `get_scoped(...)` (404 for other-tenant and missing alike), usable by workers.
- R7: `/api/account/export` now returns the tender tables (`app/tender_export.py`; ai_tasks and ai_cache left out, tsv skipped); `notes` key removed from the account export.
- `app_name` default is `tender`.
- Tests `tests/test_tender_model.py` (25): cross-tenant 404 for all 10 row objects, composite FK refuses a cross-tenant or missing parent (10 cases), same-tenant child accepted, duplicate sha256 per tenant, tsv generated, tenant delete cascades, export covers new tables with only own rows.

## S1 finished (T-185)
- Note removed: model, `routes/notes.py`, SPA dashboard (now a "Tender packs" placeholder), `NoteBody` (renamed `FreeText`,
  still used by the test vehicle and later tender text fields), `notes_written` in `/me/export`, migration `0013`
  (drops `notes`; downgrade recreates it with its index). `alembic upgrade head && alembic check` clean; 0013 down/up and
  full downgrade to base tested.
- Test vehicle: `backend/tests/vehicle.py` is a tenant-owned item with CRUD and one AI action (`/api/vehicle`, summarize) that
  runs the same reserve/settle, plan cap, tenant scoping and `textsafe` path the Note route did. It is mounted only
  through `create_app(extra_routers=(vehicle.router,))` (the `app` fixture and the three AI-test app factories), its table
  `vehicle_items` is created and truncated by `tests/conftest.py`, and it is in no model or migration.
- Ported to the vehicle (guarantees kept, only names changed): test_ai, test_hardening (AI cap, in-flight, global/trial budget,
  prompt-injection wrapping, deleted-while-summarising, edited-while-summarising), test_tenancy, test_text_input,
  test_t87_leftovers, test_platform (CORS, tenant delete), test_team, test_verification, test_spa, test_billing,
  test_cookies_and_limits, test_async_hash_capacity.
- Deleted: frontend `dashboard.test.tsx` (9 tests; Note list paging/retry/summary UI only). In test_hardening the
  member export test now asserts `notes_written` is gone. No backend test was deleted.
- Prices off: setting `billing_enabled` (default False). Off: `/api/billing/*` is not mounted (404), `/api/config`
  reports `billing_enabled`, the SPA hides the Billing link, billing pages (Page not found), plan/price text and the
  "Choose a plan" link; the legal/help copy no longer mentions paid plans. The trial clock and AI caps still apply.
  Starter billing tests keep running with the flag on (`conftest.settings` sets `billing_enabled=True`; frontend billing
  tests call `setBillingEnabledForTest(true)`). Flag-off tests: `backend/tests/test_billing_flag.py` (8), App.test.tsx (5),
  api.test.ts (1).
- E2E `tests/e2e/core_flow.cjs` rewritten for the new flow (sign up, no prices/billing, sign out/in, delete). Playwright was NOT run.

## Left
1. Per-object HTTP routes (S2+); the 404 tests run on `get_scoped`.
2. Docs under app/ (README sizing text, SECURITY.md, infra/README.md) still use "note" as the example payload in prose.
3. `infra/test-deploy-workflow.sh` needs the starter's `_starter-deploy.yml`, which is not in the product copy (exit 2 here); the
   `_starter-ci.yml` bicep/docker/playwright jobs were not run (no az, docker or browsers here).

## Test results (final tree)
- Backend: `cd products/sme-council-tender-drafting/app/backend && TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python -m pytest -q` (Python 3.12 venv from requirements-dev.txt, local Postgres 16, per-run DB). Exit 0, 852 passed, 0 failed (counted from the progress dots; the starter's addopts hide the summary line).
- Migrations: `alembic upgrade head && alembic check` ("No new upgrade operations detected"); `downgrade 0012` then `upgrade head`; `downgrade base` then `upgrade head`: all OK.
- Frontend: `cd app/frontend && npm ci && npx tsc -b && npx vitest run` 202 passed (6 files); `npm run build` OK; `python3 scripts/check_built_html.py frontend/dist/index.html` OK.
- Infra: `bash infra/test-db-setup.sh` (REQUIRE_PG=1) 33 passed; `bash infra/test-deploy-role.sh` 67 passed. Not run: see Left item 3.

## Run
See `app/README.md`; backend needs `DATABASE_URL`, then `alembic upgrade head`.
