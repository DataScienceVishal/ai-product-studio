# Review: p/sme-council-tender-drafting/T-204 (head 9547c53)

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff origin/main...9547c53` (5 files, +91/-31).

## Verdict: CHANGES

One blocking issue. The S5 decision rests on a claim about CSRF that is false for this app. The code fix is about three lines.

## Tests (run in a separate worktree)

- Backend: `pytest -q -o addopts=""` against starter_test: **1195 passed, 1 skipped** (326 s).
- Frontend: `npx vitest run`: **7 files, 232 tests passed**. `npx tsc -b`: clean.

## What is right

- **S1:** `claimcheck.load_gate_inputs` is now `export.gate_inputs(export.load_rows(...))`. Sign-off, `pack_checked`/`export_check` and export all go through one loader. The old copy in claimcheck had the same semantics (all drafts of all requirements, the latest non-voided sign-off, live = item and document both not soft-deleted), so nothing changes in behaviour.
- **S2 gate safety:** the gate still gets the full `live` set (`Rows.live`, export.py:69), not the cited subset. So `evidence_removed` still fires for any cited number that is soft-deleted, whether it comes from a claim's `cited_ids` or an `[E-n]` in the text (gate.py `cited - live`). `Rows.evidence` is only used for rendering. A cited passage that is not live cannot get through.
- **S4:** export takes `_lock_pack` FOR UPDATE before it reads. Every other writer locks the pack row first, with nothing taken earlier: sign-off (FOR UPDATE), reopen and draft save (`_lock_pack`), and the claimcheck store step (FOR SHARE on the pack, then draft and claim writes). So there is no lock-order cycle. Under the old FOR SHARE these already conflicted with each other, so FOR UPDATE adds no new blocking. The document-delete `UPDATE ... WHERE status='ready'` does not match signed or exported rows. The backend reads `exported` everywhere it reads `signed`: tender.py:299, 317, 442, 574, 624; export.py:159; gate `PACK_STATES_EXPORTABLE`. The claimcheck and draft workers use allow-lists (`CHECK_PACK_STATES`, `DRAFT_PACK_STATES`) that leave out both. The frontend locks editing on both (tender.tsx:258, 379, 571, 695).
- **S8:** reopen flushes the void and then uses `pack_checked`. Its reason filter ignores `no_signoff`, `digest_mismatch` and `pack_not_ready`, so a clean pack goes back to `ready` and a pack with removed evidence goes back to `drafting`. Tested.
- **Appendix test:** it now compares only claims of the latest draft version.

## Critical issues

### C1. The state-changing GET export can be triggered cross-site, and the docstring's reasoning is wrong
`app/backend/app/routes/tender.py:594-600` (and main.py:37, 53-55)

The docstring says that "a cross-site request carries no session" because of SameSite=Lax, and that "the frontend also sends X-Requested-With". Both points fail in practice:

1. SameSite=Lax **does** send the cookie on a top-level cross-site GET navigation: a link, `window.location`, or a form with `method=GET`. Lax only removes the cookie from sub-resource requests and cross-site POSTs.
2. `CsrfGuard` checks only `UNSAFE_METHODS = {POST, PUT, PATCH, DELETE}` (main.py:37). The header the frontend sends is never required on GET, so it protects nothing.

So a page on another site that knows a pack id can send a signed-in victim to `/api/packs/<id>/export`. That moves the pack `signed -> exported` and writes an `ExportRecord` attributed to the victim. That is a forged audit row. Since T-204 it is also a status change. The pack UUID is hard to guess, which limits the damage, but the main justification for S5 is false.

The other premise is also wrong. "A plain browser download, no frontend change" is not how the app downloads: the frontend uses `apiDownload` (frontend/src/api.ts:99), a `fetch` that already sends `X-Requested-With: fetch`.

**Fix (either one):**
- (a) At the top of `export_docx`, take `request: Request` and do `if not request.headers.get("x-requested-with"): raise AppError(403, "csrf_check_failed", ...)`. The frontend and the e2e flow keep working unchanged. Add a test: GET with no header gives 403 and the pack stays `signed`.
- (b) Make it `POST /packs/{id}/export`. This is one line in tender.tsx:712 (`apiDownload` gains a method), and the global guard then covers it.

Whichever you pick, rewrite the docstring so it describes the real protection.

## Suggestions (non-blocking)

- **S-a. New race between the two evidence queries** (export.py:69 and :71). `live` and `ev` are now two statements under READ COMMITTED. If an evidence delete commits between them, the gate passes on the older `live`, and `render` then raises `KeyError` at export.py:143 (`rows.evidence[n]`). The result is a 500 rather than a 409. It fails closed (no record, no file), but it is a regression from the single query. Fix: after building `ev`, set `live -= (cited & live) - set(ev)` so the gate sees the same snapshot. Or catch the miss in `build` and raise `ExportRefused`.
- **S-b. Pre-existing:** a document delete does not lock signed or exported packs. An export that is running can still write a passage that is deleted a moment later. If that matters, take the pack locks in the delete route (in a stable order).
- **S-c.** tender.tsx:182: the pack-list badge is green for `ready`/`signed` but grey for `exported`. Add `exported` to the green set.
- **S-d.** `test_one_loader_feeds_export_signoff_and_claimcheck` asserts on `inspect.getsource(...)` text. That is a brittle source-text check. The equality assertion is the behavioural part, so drop the getsource line.
- **S-e. Missing tests:** an `exported` pack refuses a draft save and a requirement edit (409). Deleting cited evidence on an `exported` pack makes re-download fail with `evidence_removed`. Re-download keeps status `exported` (it does today, but no test pins it).
- **S-f.** `Rows.live` still loads every display number for the tenant on each gate run, as before. That is fine at current sizes. Bound it to cited numbers later if evidence libraries grow large.
