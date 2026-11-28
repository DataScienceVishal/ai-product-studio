# Review: p/sme-council-tender-drafting/T-199 (T-199 + T-201 leftovers)

Reviewer run, 2026-11-28. Commit reviewed: 71efe5d. Diff: `git diff main...p/sme-council-tender-drafting/T-199` (11 files, +232/-18).

## Verdict: CHANGES

One must-fix: the evidence purge can delete evidence that an exported pack's answer text cites. Everything else is sound or non-blocking.

## Tests run

- Tender files: `pytest tests/test_tender_*.py` -> **355 passed** in 98.9s.
- Full backend: `pytest -x` -> **1209 passed, 1 skipped** in 281s (Postgres studio/studio, db starter_test).
- Reviewer repro (temporary test file, deleted after the run, not committed): exported pack, then the
  latest draft has the citation in `outside_ids` instead of `cited_ids`, then the evidence doc is soft-deleted 200 days ago, then
  `purge()` -> `soft_deleted_evidence == 1`. The evidence was deleted even though the exported text cites it.

## Must-fix

### M1. The purge only protects `Draft.cited_ids`, but an exported answer can cite evidence through `outside_ids` too
`app/backend/app/maintenance.py:55` (`EvidenceItem.display_no == any_(Draft.cited_ids)`).

- `Draft.cited_ids` is not "every [E-n] in the text". `draft.analyse()` splits text citations into `cited_ids` (in the
  retrieved set) and `outside_ids` (not retrieved). A user edit (`routes/tender.py` `edit_draft`) that types `[E-7]` for a
  passage not retrieved for that question stores 7 in `outside_ids` only.
- The export does not block every outside citation. `claimcheck.apply_rules` blocks one only when a model claim cites it
  with `supported` (rule 4), or when the sentence has fact triggers (rule 6). An opinion-only sentence such as "We take
  quality seriously [E-7]." that the model returns no claim for, and that has no digits or capitalised run, gets through.
  `export.load_rows` then puts E-7 in the appendix, because the appendix uses `_CITE.findall(d.text)` plus `Claim.cited_ids`.
- Result: E-7 is printed in a delivered tender pack, the evidence document is soft-deleted later, and 90 days after that the
  purge removes it. That breaks the T-201 item 10 rule ("unless a pack with an exports row has a draft citing one of their
  passages") and the audit trail DATA.md promises. The reviewer repro above shows it.
- **Fix:** protect on the same set the export prints. The smallest change is
  `or_(EvidenceItem.display_no == any_(Draft.cited_ids), EvidenceItem.display_no == any_(Draft.outside_ids))`.
  For extra safety, also add an EXISTS over `Claim.cited_ids` for the pack's drafts, because the appendix unions claim citations
  too. Add a test where the exported draft cites the passage only through `outside_ids`; it is the reviewer repro made into an
  assertion.

## Checked and correct

- **Purge, tenant isolation:** every correlation has a tenant equality: doc to item, item to draft, draft to requirement,
  requirement to export. `display_no` is unique per tenant (`uq_evidence_items_tenant_display_no`) and comes from a
  monotonic per-tenant counter (`evidence.py` `evidence_counters`), so numbers are never reused after a purge, and another
  tenant's E-1 cannot protect or expose this tenant's E-1. Only `kind == 'evidence'` rows that have `deleted_at` set are
  touched. Pages and items cascade through `_child(... CASCADE)`. Evidence documents are never the target of
  `requirements.source_document_id` (NO ACTION), so the delete cannot fail on that FK. Protection checks any draft version of
  any requirement in an exported pack, which over-protects. That is the safe direction.
- **Purge, exported-pack test:** `test_purge_keeps_evidence_cited_by_an_exported_pack` runs a real export, so it really
  exercises the exports row. The never-exported case and the 89/91-day boundary are also covered.
- **`AppError.task_tokens` / `runner.run_one`:** `draft.py:268` attaches `(tin, tout)` of the questions already finished;
  `runner.py:118` reads it with a `(0, 0)` default, so other handlers are unaffected. The test patches the module global
  `draft_answer`, which the handler looks up at call time, so the test is real: (100, 50) is kept after a failure on
  question 2.
- **Redraft lock:** `redraft` takes `draft:{pack}:{req}` before counting, and `_queue_draft` takes the same key again. Postgres
  transaction-level advisory locks are re-entrant in one session, so this cannot deadlock. A second concurrent redraft waits,
  then sees the queued task and returns it. Fine.
- **`hashtextextended`:** no `hashtext(` is left in `app/`.
- **GET draft light columns:** the version list selects 4 columns with a tenant filter. The chosen row is loaded through
  `scoped()` by version. A 404 for an unknown version is kept. Test checks that `text` is absent from the list.
- **"Already done" claims:** every cited test exists in the named file
  (`test_upload_extract_draft_and_check_fit_the_30k_trial_day`, `test_signoff_takes_the_pack_row_lock`,
  `test_an_edit_racing_a_sign_off_waits_for_it_and_is_refused`, `test_an_edit_makes_the_draft_unchecked_...`,
  `test_adding_or_editing_a_requirement_reopens_a_ready_pack`, `test_queue_check_still_works_with_the_pack_row_locked`,
  `test_signoff_reruns_the_gate_on_the_server_...`, `test_export_refused_without_sign_off`,
  `test_a_draft_task_does_not_write_to_a_pack_signed_meanwhile`). `RETRIEVAL_FLOOR = 0.0` is confirmed. The 30k test
  really walks the reservation and settlement for each step against the trial cap.

## Non-blocking suggestions

1. **`extract._is_heading` drops real headings that start with How/What/Who/Why/State/Detail** (`extract.py:101`).
   Checked: `"How we deliver social value (max 300 words)\n\nDescribe the social value you will deliver."` now gives
   `None`; main gives 300. A missed limit removes the over-limit check for that question. Narrow the rule: treat the line as a
   question only if it starts with a lead verb AND reads as a request, for example it contains `you`/`your` or ends in `?`. The
   T-201 case "Describe your approach ..." still matches. Add the How-heading case to the test.
2. **`split_sentences`: the second `No.` rule is dead code** (`draft.py` after line 91). `No` is already in `_ABBREV`, and a
   digit passes `isalnum() and not isupper()`, so the first rule always merges first. Drop it or fold the comment into the
   first rule. Also `re.I` lets "the answer is no. we ..." merge; this is harmless and rare.
3. **`task_tokens` is undeclared on `AppError`** (`errors.py:12`). Declare `task_tokens: tuple[int, int] = (0, 0)` on the class
   so the contract is visible and typed, and so `getattr` is not needed.
4. **Token reporting gap:** tokens spent inside a `draft_answer` that then raises (for example the first call succeeds, then
   `ai_invalid_output`) are still lost. This is reporting only (`ai_usage` holds the real spend). Note it in DESIGN, or carry
   partial tokens on the error from `run_task`.
5. **Purge tenant-isolation test:** the correlation is right by reading, but there is no test with two tenants that share a
   `display_no` (tenant B's exported pack cites its own E-1, tenant A's soft-deleted E-1 must still go). Cheap to add, and it
   guards against a future refactor dropping a tenant equality.
6. **Purge cost:** the correlated EXISTS scans the tenant's drafts for each aged deleted doc. It is fine at current scale, and it
   only runs on aged soft-deleted docs. If drafts grow, a GIN index on `drafts.cited_ids` (and `outside_ids`) would serve it,
   and would also serve the `&&` query in `delete_document`.
7. T-189 nit 6 is deferred with a stated reason. Agreed: it needs a product decision, not a code change.
