# Review: T-188 (S4 extraction and checklist API)

Branch `p/sme-council-tender-drafting/T-188` at 0a6198a, diff against origin/main. Reviewer: reviewer agent, 2026-11-27.

## Verdict: CHANGES

## Summary
Mostly solid work. Chunking (5 pages, 1 overlap) is correct. Tender text goes to the model only through `run_task` as
`{"chunk": ...}`, so it sits inside the nonce DATA block. Every query in the routes and the handler filters on tenant_id.
Cross-tenant ids return 404 and are tested. Migration 0015 is additive (a nullable JSONB column, plus a text[] with
server_default `{}`), so it is safe on existing rows. The budget refusal is tested, and nothing is sent.
Three things block merge. The R3 refusal path, which DESIGN says is the normal trial path, leaves the pack stuck. A re-run
deletes the user's edits. And the 409 and re-run behaviour has no tests.

Tests: full backend suite **939 passed, 1 skipped**, 0 failed (189.8 s). The new file `tests/test_tender_extract.py` has 10 tests.

## Critical issues

1. **A failed extraction leaves the pack in `extracting` forever.**
   - Where: `app/routes/tender.py` `queue_extract` sets `pack.status = "extracting"`. `app/tender/runner.py:103-107` marks only the task failed, and nothing resets the pack.
   - Why it matters: R3 says live extraction on the app path is always refused at the trial cap. So the default outcome is a task failed with `ai_daily_cap_reached`. After that, `POST /packs/{id}/confirm` returns 409 `not_ready`, because the status is not `review` or `drafting`. The user can add requirements by hand but can never confirm them, so the product dead-ends on its main path.
   - Fix: on any handler failure, set the pack's status back to its previous state (or `draft`/`review`), so manual entry plus confirm works. Use either a failure hook in `extract_handler` or the runner's `_finish`. Assert the pack status in `test_with_azure_settings_the_reservation_is_refused_not_sent`.

2. **A re-run deletes rows the user has edited.**
   - Where: `app/tender/extract.py` `extract_handler`, the `delete(Requirement)` statement.
   - Why it matters: the delete matches `origin == "model", status == "proposed"`. But PATCH keeps `origin=model` and only sets `edited_by` (`routes/tender.py` `edit_requirement`), so any edited row that was not yet confirmed is lost on re-extract. Rows the user marked `removed` survive, and the same item is re-inserted as a new proposed row, so removed items come back.
   - Fix: also require `Requirement.edited_by.is_(None)` in the delete. Before inserting, skip new items that match any surviving row (same ref, or similarity at or above 0.9) using `merge_items` logic, so edited, removed and confirmed rows are not duplicated.

3. **Re-extracting a confirmed pack moves it backwards and duplicates the confirmed items.**
   - Where: `routes/tender.py` `queue_extract`, which blocks only `signed` and `exported`.
   - Why it matters: in `drafting`, the pack goes back to `extracting` and then `review`, with `confirmed_by` still set. Fresh proposed copies of every confirmed item are added. Once S5 drafts exist, this corrupts the checklist they hang off.
   - Fix: return 409 for `drafting` too, or require an explicit `?replace=true` that runs the dedupe from issue 2. Add a test.

4. **The bar's 409 and re-run behaviour has no tests.**
   - Where: `tests/test_tender_extract.py`.
   - Why it matters: no test covers 409 on a signed or exported pack (extract, add, patch, confirm). No test covers a re-run replacing only proposed model rows. These are explicitly in the T-188 bar.
   - Fix: add both tests, including an edited row and a removed row surviving a re-run.

## Suggestions

5. **The limit cross-check can flag items that are fine.**
   - Where: `extract.py` `stated_word_limit`.
   - (a) The index from `norm(page_text).find(...)` is a position in the normalised text, but it slices the raw `page_text`. With collapsed PDF whitespace the window drifts.
   - (b) The window starts 200 characters before the quote, so `search` returns the *previous* question's "maximum 500 words" first.
   - (c) If the window has no match, it falls back to the first limit anywhere on the page. So a question with no limit, on a page where another question has one, gets `limit_mismatch`. Tenders often have several questions per page, so this will be noisy.
   - Fix: map offsets on the raw text, search from the quote start forward (to the next question ref), and drop the page-wide fallback when a quote was located.
   - DESIGN also names "no more than 2 sides of A4" (page limits), which is not covered yet.

6. **`merge_items` merges on the same ref anywhere in a document.**
   - Where: `extract.py` `merge_items`.
   - Refs like "1.1" or "Q1" often repeat across lots or sections. A ref of only whitespace is truthy, so it also merges with every empty-ref item.
   - Fix: use `it["ref"].strip()` for the truthiness test, and require the same ref to be on the same or an adjacent page, or to have similar text.

7. **`add_requirement` computes `seq` as max+1 with no lock or unique constraint**, so concurrent adds, or an add during an extraction write, can produce duplicate `seq` values. Take the same advisory lock, or add a unique (pack_id, seq) constraint.

8. **The ORM column `flags` has `default=list` but no `server_default`, while the migration has `'{}'`.** It is harmless, but keep them in step (`server_default=text("'{}'")`).

9. **The design asks for one extraction task per chunk (DESIGN 4.6); this is one task per pack.** NEXT.md already notes it, and the per-tenant cache makes a retry cheap. Log it in DECISIONS or fix it in S5, so `/status` can show progress.

10. **The model can cite a `source_page` outside the chunk, or a negative one.** It is stored as is. It is harmless (the item goes amber), but consider clamping it or flagging it as `page_out_of_range`.

---

## Re-review at e30c928 (diff 9cbc549..e30c928): PASS

Full backend suite: **947 passed, 1 skipped**, 0 failed (197.9 s). That is 8 more than before.

- **Issue 1 fixed.** `extract_handler` now wraps `_extract`. On any failure except `LeaseLost`, `_reset_pack_status` sets the pack to `review` if it has items, or to `uploaded` if it has none. The update only applies while the status is still `extracting`. Confirm now accepts `uploaded`, so a checklist written by hand works. The R3 refusal test now asserts that the pack is in `uploaded` and that adding an item by hand and confirming both succeed. A new test covers a failed run on a pack that has items going back to `review`.
- **Issue 2 fixed.**
  - The delete now also requires `edited_by IS NULL`.
  - New items are deduped against every row that survives (edited, confirmed, removed and user rows), document by document.
  - The re-run test checks that the edited, removed, confirmed and user rows all survive, that the edited text is kept, and that no duplicates are added (4 rows).
- **Issue 3 fixed.** Extract returns 409 unless the pack is `uploaded`, `extracting` or `review`. This is tested for drafting, checking, ready, signed and exported.
- **Issue 4 fixed.** The tests above cover it.
- **Issue 6 fixed.** `same_item` requires the same or an adjacent page and ignores blank refs, and it is unit-tested.
- **Issue 8 fixed.** The ORM `server_default` now matches the migration.

### Still open (non-blocking, recorded in NEXT.md)
- Issue 5: the limit regex window and its page-wide fallback can still raise false `limit_mismatch` flags.
- Issue 7: the `seq` race.
- Issue 9: one task per pack instead of one per chunk.
- Issue 10: `source_page` is not range-checked.
- A worker killed until `attempts_exhausted` leaves the pack in `extracting`. Recommend a follow-up board task: the runner's exhaustion path should call a per-kind failure hook.
- Minor: a user row (`source_page` 0) only dedupes against model items on page 1, and an edited row with no ref and rewritten text can be re-proposed as a near-duplicate. Both are acceptable; the user sees and removes it.
- Nit: `tender_models.py` imports `text` twice, once directly and once as `sa_text`.
