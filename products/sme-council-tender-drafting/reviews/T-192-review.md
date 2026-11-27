# Review: T-192 (S8 part 1: Word export, reopen)

Branch `p/sme-council-tender-drafting/T-192`, commit ba8c499 against `main`. Reviewer: `reviewer` (opus), 2026-11-27.

**Verdict: CHANGES.** There are two must-fix items, both places where the export does not match SPEC step 7 and DESIGN 4.5: the appendix and the header text. The gate, locking, tenant isolation, voiding, migration and docx safety all pass.

## Evidence (run on the branch tree)
- Backend: `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""` gave **1192 passed in 265.09s** (0 failed). This includes `test_migrations.py`: the full chain upgrades and downgrades and matches the models.
- Frontend: `npx vitest run` gave **7 files, 232 tests passed**. `npx tsc -b` is clean.
- Alembic: only one revision has `down_revision = '0018'`, and that is the new `0019`. There is one head. `downgrade()` drops the column, so it is reversible.
- docx safety probe: `clean('a\x00b\x1f￾\ud800<w:t>&"x</w:t>\x0b')` returns `'ab<w:t>&"x</w:t>'`. That saves and re-opens with python-docx, with the markup kept as literal text (lxml escapes it). `safe_filename('é"\r\n;../x')` returns `x-draft.docx`, and a title with no usable characters gives `tender-pack-draft.docx`.

## Summary of what is right
- **Same rows into gate and render.** `export.build` loads once (`load_rows`), builds the gate values from those objects (`gate_inputs`), runs `gate.export_allowed`, then renders from the same `Rows`. It also adds an explicit `not_signed` status check and refuses when there is no sign-off.
- **The T-201 "re-run export_check server-side" requirement is met. It is not a must-fix.** `claimcheck.export_check` is just `gate.export_allowed(*load_gate_inputs(...))`. `export.load_rows` has the same filters as `load_gate_inputs`: tenant-scoped pack, requirements, all draft versions, claims, the latest non-voided sign-off, and live evidence (both item and document not soft-deleted, same join). It differs only in ordering, which the gate ignores. Calling `export_check` as well would mean a second read, so rendered rows could differ from checked rows. The builder's approach is stricter. The risk is that the two loaders drift apart (see suggestion S1).
- **Refusals are covered by tests:** no sign-off, evidence soft-deleted after sign-off (`evidence_removed`), drafts tampered under the digest, and after reopen. Each test also asserts that no `exports` row was written.
- **Every sign-off reader ignores voided rows:** coverage (`routes/tender.py:557`), `claimcheck.load_gate_inputs` (`claimcheck.py:416`) and `export.load_rows` (`export.py:62`). The sign-off route never reads an existing sign-off. It relies on pack status, which reopen resets to `ready`. The account export (`tender_export.py`) picks up `voided_at` through `column_attrs`, so the audit trail is in the R7 export too.
- **Locking: no deadlock path.** Export takes the pack row FOR SHARE (`read=True`, `populate_existing`) and never writes the pack row. Its `exports` insert takes FK KEY SHARE on the pack (compatible) and on the sign-off row. Reopen takes the pack FOR UPDATE first via `_lock_pack`, then does a non-key UPDATE on `signoffs`, which is compatible with KEY SHARE. Both lock the pack row first, so they cannot form a cycle. Two concurrent exports share without trying to upgrade. This matches the reasoning in T-191: FOR SHARE is safe only for transactions that never upgrade.
- **Tenant isolation:** `get_scoped` gives a 404 cross-tenant for both routes (tested), and every query in `load_rows` filters on `tenant_id`. 401 without a session is tested.
- **Frontend:** the blob download sends same-origin credentials and has a timeout, and a refusal shows the server's JSON message (tested). Reopen sits behind `window.confirm` (tested: the first confirm is declined and nothing is sent). No price text (tested).

## Must-fix
1. **The appendix lists cited passages, not claims.** See `app/backend/app/tender/export.py:124-136`.
   - **Required:** DESIGN 4.5 says "a table of every claim with its `E-n`, document, page and the supporting quote". SPEC step 7 and SPEC 120 say "an evidence appendix listing every claim and its source".
   - **What it does now:** one paragraph per cited E-n, holding the whole passage text. `Rows.claims` is loaded but not used in the render.
   - **Why it matters:** the appendix is how a reviewer, and the A5/A6c human sample, traces each claim to its quote. A full 120-400-word passage per citation does not show which sentence supports which claim.
   - **Fix:** render a table, one row per claim of each exported question's latest draft, in question order then `Claim.seq`. Columns: claim (`span`), `E-n` (from `cited_ids`), document, page, and `evidence_quote`. Pass each through `clean()`. A claim with no `cited_ids` should still appear, with "no citation".
   - **Test:** extend `test_export_docx_matches_the_database` to check every claim's span and evidence quote in `doc.tables[...]`.
2. **The header wording does not match SPEC/DESIGN.** See `export.py:102`.
   - **Required:** SPEC step 7 and DESIGN 4.5 fix the text as "Draft prepared with AI assistance; reviewed by {name} on {date}". It was chosen to line up with the PPN 017 disclosure.
   - **What it does now:** "Draft produced with AI assistance; reviewed and signed off by ...".
   - **Fix:** use the exact SPEC text, and assert the full header string in the test. If the wording should change, that is a SPEC change logged in DECISIONS, not a code-level drift.

## Suggestions (not blocking)
- S1. **Two loaders for the same gate inputs.** `export.load_rows`/`gate_inputs` and `claimcheck.load_gate_inputs` are duplicates. Make `load_gate_inputs` return `gate_inputs(load_rows(...))` (or the reverse), so coverage, sign-off and export cannot drift.
- S2. **Unbounded evidence load.** `export.py:64` loads every live `EvidenceItem` entity in the tenant, including `text` and the `tsv` column, on every export. It needs only the live `display_no` set (as `load_gate_inputs` does) plus the cited items. Load the ids, then fetch `display_no IN cited`. A large evidence library makes this tens of MB per click.
- S3. **The comment at `export.py:128` is wrong.** It says a `KeyError` "is a refusal". It would be an uncaught 500. In practice the gate makes it unreachable, because cited text markers must be live. Either change the comment, or convert the error into `ExportRefused`.
- S4. **The pack never moves to `exported`.** DESIGN lists it as a state, and reopen and the frontend accept it. Either set it on export, or drop it from the docs. If export starts writing the pack row, switch its lock to FOR UPDATE (or two concurrent exports deadlock on the upgrade).
- S5. **The GET export has a side effect** (an `exports` audit row). A cross-site `<img>` could add audit rows, though it cannot read the file. Consider requiring the `X-Requested-With` header the frontend already sends, or rely on SameSite=Lax and note it.
- S6. **Download timing in the frontend.** `URL.revokeObjectURL` runs synchronously after `a.click()` (`tender.tsx:717`). Some browsers can cancel the download. Defer it with `setTimeout(..., 0)` or a short delay.
- S7. **DESIGN's S8 row says "sign-off voided by an edit".** The branch voids it with an explicit reopen instead, which is a reasonable design. Record it in `state/DECISIONS.md` and update DESIGN 4.5 to describe the `/reopen` route and `voided_at`.
- S8. **Reopen does not check claim/evidence liveness.** It always sets `ready`. That is safe, because sign-off re-runs the gate and coverage shows the blockers. But a pack can show `ready` while blocked, and that ties into open T-190 item 5.

## Re-review scope
Items 1 and 2, plus their tests. Nothing else needs re-reviewing if S1 to S8 are left alone.

---

## Re-review (fixes at 3c9ccf2)

**Verdict: PASS.** Scope was M1, M2, S3 and S6 only, as the coordinator asked. No other code changed between afb5afc and 3c9ccf2: the 4 changed files are `export.py`, `test_tender_export.py`, `tender.tsx` and `tender.test.tsx`.

### Evidence (on tree 3c9ccf2)
- Backend full suite: **1192 passed in 270.92s**, 0 failed.
- Frontend: `npx vitest run` gave **7 files, 232 tests passed**. `npx tsc -b` is clean. `npm run build` built OK (`dist/assets/index-*.js` 279.99 kB). The working tree is clean afterwards.

### Items
- **M1, fixed.** `export.py:122-143` now renders "Appendix: claims and their sources" as a 5-column table (Claim, Evidence, Document, Page, Supporting quote).
  - **Rows:** one per claim of each question's latest draft, in question `seq` then claim `seq`. `by_draft` is keyed on `str(c.draft_id)`, which matches `GateDraft.id`, a string.
  - **Content:** a claim with no citation shows "no citation". The ref plus span, the document names and the quote all go through `clean()`. The E-n and page cells are built from integers.
  - **Live evidence:** the gate already includes every claim's `cited_ids` in its live-evidence check, so `rows.evidence[n]` cannot miss.
  - **Test:** checks the header row, the row count against the claims, and each row's span, E-n list, document, page and exact quote.
- **M2, fixed.** `export.py:102` now reads "Draft prepared with AI assistance; reviewed by {name} on {date}". The test asserts the whole header string.
- **S3, fixed.** The wrong comment is gone. The new comment says a miss would be a bug, which is accurate (an uncaught 500, unreachable behind the gate).
- **S6, fixed.** `tender.tsx:717` now calls `setTimeout(() => URL.revokeObjectURL(url), 1000)`. The test waits for the revoke with `waitFor`.

### Still open (non-blocking, from the first review)
S1 (one loader for the gate inputs), S2 (unbounded evidence load per export), S4 (the `exported` status), S5 (side effect on GET), S7 (record reopen in DECISIONS/DESIGN), S8. Minor: the test's `len(table.rows) == 1 + len(claims)` counts claims across all draft versions. That holds for this fixture, which has one version, but would break if older versions carried claims. Filtering on the latest draft id would make the test sturdier.
