# STATUS (T-206 part B) - keys for all 9 held-out packs written; awaiting independent checker

Branch `p/sme-council-tender-drafting/T-206`. Part A is committed (1c2f77e); part B is not. No model calls; keys hand-derived from `demo-data/pack-sources/*.md`.
- Done: README rules 15-19 added (synthetic refs `<section>-<n>` for unnumbered items, "Question" label dropped, Studio Lead decision that general-rule limits stay copied and a missed rule is an extraction miss, SQ/briefing items not keyed, marks packs). Keys S02 (9 q, 10 mandatory), S03 (9 q, 11), S06 (8 q, 11, marks 60), S07 (10 q, 10), S10 (8 q, 9 incl. Q0 plus 8 bullets), S11 (13 q, 10); items incl. deadline 20/21/20/21/18/24. Earlier: S01 18 q, S05 16 q, S09 20 q. `tests/test_tender_pack_keys.py`: 10 passed (QUALITY_TOTAL/MARKS_TOTAL with line pointers).
- Left: demo-pack retrieval labels for S04/S08/S12; independent checker of all 9 keys against the packs (check limits, general-rule copies, mandatory sets); the pre-registration commit in EVAL.md.
- New ambiguities: (1) S03 4.3 "one side per case study": page_limit 1 plus case_studies 2; S10 Q7 "one A4 page for both examples": page_limit 1 (no per-item count). (2) S06 PF11 keyed mandatory from the free-text paragraph (validator item 4 asked for a pack fix; the md still has it as a paragraph). (3) S06 Q5 (a)/(b) one item. (4) S07/S02 numeric refs ("1", "9") are bare numbers, so ref matching is weak for them. (5) S11 briefing "mandatory" in key dates vs conditional in 1.3: not keyed. (6) S10 1.4 EL-exemption and SSIP "or plan" bullets keyed verbatim. (7) S02 Q1/Q4 750 words, general rule 500 copied to the other 6. (8) S06 Q4 to Q6 shared 1,200 words: word_limit null.

# STATUS (T-206 part A) - keys for S01, S05, S09 written; awaiting part B

Branch `p/sme-council-tender-drafting/T-206`. Not committed. No model calls; keys written by hand from `demo-data/pack-sources/*.md`, `demo-data/evidence/` not read.
- Done: "Key conventions (pre-registered)" in `eval/keys/README.md` (14 rules, covers every item in T-194-validator item 7 a-g except the S10 unnumbered-bullet ref rule). Keys `eval/keys/S01-...json` (18 questions, 11 mandatory, 1 deadline), `S05-...json` (16 questions, 16 mandatory incl. Q11, 1 deadline), `S09-...json` (20 questions, 11 mandatory, 1 deadline). Test `app/backend/tests/test_tender_pack_keys.py`: 4 passed (quality totals S01 70, S05 60, S09 70).
- Left: keys for S02, S03, S06, S07, S10, S11 (add each pack's quality total to `QUALITY_TOTAL` in the test); demo-pack retrieval labels for S04/S08/S12; independent checker of all keys against the packs; then the pre-registration commit in EVAL.md.
- Ambiguities hit: (1) General-rule limits (S05 2.4 gives Q12 400 words, no heading limit) are copied to the question; an extractor that misses 2.4 will lose A2 on Q12 (rule 5; flip to null if the checker prefers). (2) S05 Q16 "2 sides of A4" gives page_limit 2, word_limit null. (3) S01 2.4 "no more than 100 words of supporting statement" keyed as word_limit 100 on the mandatory item; S05 Q11 150. (4) S09 SQ Section D parts say "pass/fail except where noted" but list information requests; none keyed (only Section A M1-M11). (5) S05 Q15 (a)/(b) is one item, so refs "15(a)" in the pack are not separate. (6) Deadline ref is "" because packs print none; matching falls back to text. (7) S05 asterisk list and S01 asterisks ignored. (8) Not-yet-decided for S10 1.4 unnumbered bullets (ref rule e): use bullet text, ref "" is not allowed by the test for non-deadline items, so give such items a synthetic ref like `1.4-1` and record it in the README.

# STATUS (T-207 - FINAL: bracketed-heading rule removed after re-review 3; see reviews/T-207-review.md. Kept: `_stated` own-limit-wins, partial-token reporting, DESIGN nit-6 note, KL cases) (T-207, T-199 review non-blocking leftovers) - code done, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-207` (off main). Not merged. No migrations, no frontend change, no live model calls.
- 1. Heading rule: documented both known edges in EVAL.md "Known limits"; cases in new `eval/extraction_known_limits.json` (no case file existed; read by `test_known_limit_cases_hold`). Narrow fix for the false negative only: a short line ending in a bracketed word limit and followed by a blank line and a body paragraph is a heading (`extract._is_bracketed_limit_heading`, used only where the quote opens its own block). All existing extract tests pass. Still open: same heading directly above the question with no blank line (KL-2), and the impersonal-earlier-question false positive (KL-3).
- C1 fix (review): the bracketed-heading rule refuses instruction/question lines, and `_stated` searches from the quote forward first so the question's own limit wins. Reviewer probes are regression tests (`test_an_instruction_ending_in_a_bracketed_limit...`, `test_the_questions_own_limit_wins...`, KL-4 to KL-6).
- 2. Token reporting: `run_task` attaches the tokens of the calls that returned to any `AppError` it raises (`task_tokens`); `draft_answer` adds a failed shorten retry's tokens; `draft_handler` adds earlier drafts to the failing call's own. Tests `test_tokens_spent_inside_a_draft_call_that_then_fails_are_kept_on_the_task` (ai_invalid_output after one billed call: 200/100) and `test_a_failed_shorten_retry_keeps_the_draft_and_counts_its_tokens`.
- 3. T-189 nit 6: KEEP (identical redraft still makes a version and counts toward 5 a day); documented in DESIGN.md section 4.3. No code change.
Verify: see the command in the T-199 block below.

# STATUS (T-199 + T-201 review leftovers) - code done, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-199` (off main). Not merged. No migrations (no `alembic check` needed), no frontend change, no live model calls.

## Per item
T-199
- a. already done, evidence: `tests/test_tender_claimcheck.py::test_upload_extract_draft_and_check_fit_the_30k_trial_day` (every call fits, a 2+ question pack fits one trial day). DESIGN.md section 4.3 now carries the calculation and the refusal behaviour.
- b. already done, evidence: sign-off and edit lock the pack FOR UPDATE (`routes/tender.py` `_lock_pack`; `tests/test_tender_export.py::test_signoff_takes_the_pack_row_lock`, `tests/test_tender_review.py::test_an_edit_racing_a_sign_off_waits_for_it_and_is_refused`); draft save reads the pack FOR SHARE (`tender/draft.py` `draft_handler`, `test_tender_draft.py` signed-between-queue-and-run test).
- c. done: DESIGN.md "8 passages" -> 5 (`APP_PASSAGES`) in the flow diagram, the sizing bullet (reservation about 11.3k) and the `draft` task table.
- d. already done, decision confirmed: an edit after ready moves the pack to `drafting` (`reopen_pack`) and the draft is unchecked, so `pack_checked` is false. Test `test_tender_claimcheck.py::test_an_edit_makes_the_draft_unchecked_and_does_not_leave_a_ready_pack_ready`, and `test_adding_or_editing_a_requirement_reopens_a_ready_pack`.
- e. already done: `RETRIEVAL_FLOOR = 0.0` in `tender/draft.py` (tuned in L1).
- f. nits 5-10 of reviews/T-189-review.md:
  - 5 done: `redraft` takes the queue advisory lock before counting the daily redrafts.
  - 6 DEFERRED: skipping a duplicate version would change the redraft limit semantics (an identical redraft would never count, the 5-a-day test relies on versions); needs a product decision, harmless as is (cost is zero on a cache hit).
  - 7 done: `hashtextextended` in the extract, draft and check routes (no `hashtext` left in `app/`).
  - 8 done: `GET /requirements/{id}/draft` selects only version, author, word_count, created_at for the list and loads the text of the chosen version only. Test `test_get_draft_returns_the_chosen_version_text_and_a_light_version_list`.
  - 9 done: a failing draft handler attaches the tokens used so far (`AppError.task_tokens`), `runner.run_one` records them. Test `test_tokens_used_before_a_failure_are_kept_on_the_task`.
  - 10 done: `split_sentences` keeps "Ltd. and", "e.g. 9001", "No. 5" together (lowercase or digit follower). Test `test_trimming_does_not_split_on_abbreviations`. Known limit: an abbreviation followed by a capitalised word still splits.

T-201
- 7. done: `extract._is_heading` refuses a one-line block that opens with a question verb. Test `test_tender_extract.py::test_an_unnumbered_one_line_previous_question_is_not_taken_as_the_next_heading`.
- 8. already done: `queue_check` takes the pack row FOR UPDATE (`routes/tender.py`, `test_tender_review.py::test_queue_check_still_works_with_the_pack_row_locked`); sign-off locks too (see b).
- 9. done, no code change: EVAL.md "Threat notes" lists the sentence-initial one-word name and the no-figure/no-name residual for L1.
- 10. done: `maintenance.purge` deletes soft-deleted evidence documents (passages cascade) 90 days after `deleted_at` unless a pack with an exports row has a draft citing one of their passages (`EVIDENCE_PURGE_DAYS`, key `soft_deleted_evidence`); DATA.md rows updated. Tests in `tests/test_tender_t199.py`: `test_purge_removes_evidence_deleted_over_90_days_ago_and_its_passages`, `..._keeps_recently_deleted_and_live_evidence`, `..._keeps_evidence_cited_by_an_exported_pack`, `..._removes_aged_evidence_when_the_pack_was_never_exported`.
- 11. already done, verified: sign-off and export both call `claimcheck.export_check` server-side (`routes/tender.py`; `test_tender_review.py::test_signoff_reruns_the_gate_on_the_server_even_if_the_pack_says_ready`, `test_tender_export.py::test_export_refused_without_sign_off` and the tamper tests).

## Review fixes (reviews/T-199-review.md, CHANGES)
- M1 done: the purge protects everything the export appendix prints: `[E-n]` markers in the draft text, `cited_ids`, `outside_ids` and the claims' `cited_ids`, for drafts of packs with an exports row. Tests `test_purge_keeps_evidence_cited_only_through_outside_ids_or_the_text`, `test_one_tenants_export_does_not_protect_another_tenants_evidence_with_the_same_number`.
- `_is_heading` narrowed: a question-verb line is the previous question only if it also says you/your/us; "How we deliver social value (max 300 words)" is a heading again (test extended).
- Dead "No." rule removed from `split_sentences`; `AppError.task_tokens` declared on the class. Known: tokens spent inside a `draft_answer` that then raises are still not reported (ai_usage has the real spend).

## Verify
`cd app/backend && TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""` (fresh Postgres: role studio/studio superuser, db starter_test; `pip install -r requirements-dev.txt`). New tests: `tests/test_tender_t199.py`.

# STATUS (T-204, T-192 review follow-ups S1, S2, S4, S5, S8 + fragile test) - code done, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-204` (off main). Not merged. No migrations, no frontend change, no live model calls.

## Done
- S1: `export.load_rows` is the only reader of the gate inputs; `claimcheck.load_gate_inputs` is `export.gate_inputs(export.load_rows(...))`.
  Sign-off, export-check and export share it (test: `test_one_loader_feeds_export_signoff_and_claimcheck`).
- S2: `Rows.live` is the set of live display numbers (what the gate needs); `Rows.evidence` holds full items only for passages cited by the
  claims or the answer text. Test with an extra uncited live item.
- S4 DECISION: export moves the pack `signed` to `exported`. The route now locks the pack FOR UPDATE (`_lock_pack`) because it writes the row.
  Re-download from `exported` still works (each click adds an `exports` row), reopen is allowed from `exported`. Frontend already treats
  `exported` as signed and reloads after the download, so no frontend change.
- S5 DECISION (revised after review C1): keep GET, but the route itself requires X-Requested-With (403 csrf_check_failed), because Lax cookies ride
  cross-site top-level GETs and CsrfGuard only covers unsafe methods. `apiDownload` already sends it. Tests added; e2e run for the download.
- Also: evidence-race 409 not 500 (live set trimmed to the loaded snapshot), `exported` badge green, extra tests for exported edits/re-download.
- S8: reopen sets `ready` only if `claimcheck.pack_checked` passes, else `drafting` (e.g. evidence removed after sign-off). Test added.
- Fragile appendix test now counts claims of the latest draft version only.

## Verify
Backend full: see report. Frontend: `npx vitest run`, `npx tsc -b`. A fresh Postgres needs role studio/studio (superuser) and db starter_test.

# STATUS (T-192 part 2: Playwright e2e of the 7 SPEC steps) - PASSES on ScriptedFakeAI, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-192-e2e`. Not merged. No live model calls.

## What works
`app/tests/e2e/tender_flow.cjs` passes all 7 steps in chromium: sign up/in, create pack + upload tender DOCX, extract + confirm checklist,
upload 2 evidence files, draft, claim check (verdict Supported shown), coverage + sign-off, export Word (download saved, zip valid, python-docx
reads it, header "Draft prepared with AI assistance; reviewed by Alex Reviewer ...", body has the answer text and [E-n]).
- `app/tests/e2e/e2e_app.py`: ASGI app = normal `create_app(ai=ScriptedFakeAI())`. Needed because `AI_PROVIDER=fake` builds the plain `FakeAI`,
  which returns prose and makes every tender task fail `ai_invalid_output`. Lives under tests/, no production route or hook added.
- `app/scripts/e2e.sh`: starts that app with `AI_WORKER_THREADS=2`, writes fixtures (`tests/e2e/make_fixtures.py`), runs tender_flow first, then core_flow.
- Fixtures are shaped for ScriptedFakeAI's heuristics (one passage per evidence file, no full stop, no shared words between topics).

## Fixed (run 6986)
- `app/tests/e2e/core_flow.cjs` waited for "Free trial:", which never shows with billing off. It now waits for the Tender packs heading and
  asserts the trial banner is absent. `scripts/e2e.sh` exits 0: tender flow 7/7 and core flow both PASS. Backend 1192 passed, vitest 232, tsc clean.

## Run it
`cd app && PYTHON=python3.13 NODE_PATH=/opt/node-tools/node_modules bash scripts/e2e.sh` (needs Postgres role studio/studio; creates db starter_e2e;
ports 8000 and 4173 free; uses the pre-installed playwright via NODE_PATH, no `playwright install`).

# STATUS (T-192, slice S8 part 1: Word export, reopen) - code done, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-192` (off main). Not merged. No live model calls.

## Done
- `app/tender/export.py`: rows loaded once (`load_rows`), plain gate values built from those same objects, `gate.export_allowed` run, then the
  docx rendered from the same objects (header "Draft produced with AI assistance; reviewed and signed off by <name> on <date>", footer =
  responsibility statement, one section per confirmed question with limit/word count and inline [E-n], appendix of each cited E-n with document,
  page and passage). XML-bad chars stripped, no fields/links, deterministic bytes (fixed core props and zip timestamps), safe filename.
- `GET /api/packs/{id}/export` (DESIGN's `export.docx` path was not used): tenant scoped (404), pack row FOR SHARE, 409 `export_blocked` with
  reasons unless pack is signed/exported, a non-voided sign-off exists, the gate passes on current rows and the digest matches. Stores an
  `exports` row (sign-off id, docx sha256, user). Pack status is left as `signed` (not moved to `exported`).
- `POST /api/packs/{id}/reopen`: pack row FOR UPDATE, 409 `not_signed` unless signed/exported, voids the sign-off, pack back to `ready`.
  DECISION: migration 0019 adds `signoffs.voided_at`; the row is kept for audit and the exports FK. Gate, coverage and export read the latest NON-voided sign-off.
- T-199: sign-off already takes the pack row FOR UPDATE; new test holds the lock and shows the sign-off waits.
- Frontend coverage page: when signed, "Export Word document" (blob download via `apiDownload` in api.ts) and "Reopen for edits" (window.confirm). 3 vitest tests.
- Tests: `tests/test_tender_export.py` (11): docx text vs DB, markers, appendix, header/footer, exports row, determinism, refused without sign-off,
  after evidence soft delete, after tampered answers, after reopen; reopen then edit then sign again then export; cross-tenant 404; 401; lock.

## Left
- Playwright e2e of the 7 SPEC steps on ScriptedFakeAI (not started).
- `claimcheck.export_check` is covered because the route runs the same `gate.export_allowed` on its own single read (does not call `export_check`, to keep one read).
- Reopen does not clear claim checks; the pack returns to `ready` and the sign-off re-runs the gate.

## Verify
Backend (python3.13, deps from requirements-dev.txt): `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""`
-> 1191 passed, 1 skipped. Frontend: `npx vitest run` 232 passed, `npx tsc -b`, `npm run build` clean.

# STATUS (T-191, slice S7: review screens, coverage and sign-off) - MERGED to main after reviewer CHANGES then PASS (reviews/T-191-review.md)

Branch `p/sme-council-tender-drafting/T-191` (off main at 39daebf). Not merged. No migrations. No live model calls (ScriptedFakeAI / Judge fakes).

## Done
- Frontend `app/frontend/src/pages/tender.tsx`: `/packs` (list + create + optional upload), `/pack?id=` (documents, upload, extract / draft / check
  buttons, question list), `/checklist?id=` (confirm, edit, remove, add, amber flags and unverified quotes), `/evidence` (upload with category, list,
  soft delete with confirm), `/draft?id=<requirement>` (answer with [E-n] chips and non-supported spans marked, the cited passages side by side,
  claims table with unsupported/contradicted red and unchecked amber, edit, redraft, re-check), `/coverage?id=` (coverage table, checklist-not-compliance
  banner, gate blockers, responsibility statement, name + tick sign-off). `"/"` stays the dashboard with links. No price text anywhere on these pages.
- Polling (`usePoll`, `usePackStatus`): a timeout chain (one request in flight), 3 s pause, doubling to 15 s after a failure, hard stop at 200 ticks,
  active only while the pack is `extracting`/`checking` or a task is queued/running; stops on terminal states and on unmount.
- `api()` takes `form` (multipart, no JSON Content-Type). `CLIENT_ROUTES` + `App.tsx` mirror: /packs /pack /checklist /evidence /draft /coverage.
- Backend (`routes/tender.py`): `GET /packs/{id}`, `GET /evidence/passages?ids=` (tenant scoped, removed text hidden), `GET /packs/{id}/coverage`,
  `POST /packs/{id}/signoff` (pack row FOR UPDATE; refuses without the tick and the current statement version, 409 unless `ready`; re-runs
  `gate.export_allowed` on the current rows with the sign-off it would create, so a stale `ready` flag is not trusted; stores name, user id,
  digest; pack becomes `signed`). `GET /requirements/{id}/draft` now also returns `requirement`. `gate.STATEMENT_TEXT` fixed in code.
- T-201: item 8 (`queue_check` and sign-off take the pack row FOR UPDATE), item 5 (`pack_checked` also runs the gate and refuses `ready` on
  evidence_removed / claims_blocked / over_limit / not_checked / missing_draft). Items 7, the purge horizon and the name-check residual are NOT done.

## Left
- S8: Word export button and e2e (the coverage page has no export button yet); sign-off voided by an edit (edits are blocked after sign-off for now).
- Review fix: edit_draft, edit_requirement and add_requirement now take the pack row FOR UPDATE (re-read) before the status check, so an edit cannot
  commit after a sign-off (FOR UPDATE not SHARE: these routes then update the row, two sharers would deadlock). Polling stops on 4xx. Tested.
- No Playwright run in this slice.

## Verify
`cd app/backend && TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python -m pytest -q -o addopts=""`
(new: `tests/test_tender_review.py`, deep links in `tests/test_spa.py`); `cd app/frontend && npx vitest run && npx tsc -b && npm run build`.
# STATUS (T-203, A4 hardening + T-202 should-fix S1-S4) - code done, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-203`. Only `eval/`, `EVAL.md`, `tests/test_tender_eval.py`. No `app/tender/` edits, no live calls.

## Done
- A4 gap exemption stricter (can only lower A4): `CLAIM_WORDS` (free, compliant, accredited, certified, ...) and hyphenated compounds
  ("incident-free") make a sole word a claim; letter+digit codes (S1); `cannot` and `n't` negations. Pre-registered in the EVAL.md A4 row and Amendments.
- S1: `sample.gap_exempt_rows` + `sample_claims/write_sheet(gap_exempt=...)` put exempt gap sentences in the A5 population. Not yet wired
  into a driver (there is none for A5 sheets yet); call it with the E2 exports.
- S2: test renamed `test_e4_uses_a_passed_claimcheck`; `_check` raises `PhaseNotReady` if `ctx.claimcheck` is None.
- S3: `Context.__post_init__` rebuilds a default claimcheck (flag `is_default_claimcheck`) so `dataclasses.replace` follows the new provider.
- S4: full stop was already fixed in 3a0e7ec.
- Mutation-style tests: removing CLAIM_WORDS, `_NEG_RAW` or `_HYPHEN` fails a test. Letter+digit codes are triple-covered, pinned by parametrized cases only.

## Verify
`cd app/backend && TEST_DATABASE_URL=... python3.13 -m pytest -q -o addopts="" tests/test_tender_eval.py`

# STATUS (T-202, T-193 follow-ups) - code done, awaiting reviewer

Branch `p/sme-council-tender-drafting/T-202`. Only `eval/`, `EVAL.md`, tests. No `app/tender/` edits, no live calls.

## Done
- Real claim check wired: `Context.claimcheck=None` now defaults to `eval.run.default_claimcheck(ctx)` (`app.tender.claimcheck.check_draft`, the cited
  live passages from the DB, `LedgerBudget` with `CHECK_CAP`, claims returned as dicts). E4 fixtures may carry `retrieved_ids`. Dry runs use the
  ScriptedFakeAI `ClaimcheckOutput` heuristic. `config` prints the claimcheck prompt SHA-256. `eval/ledger.py` still imports nothing from `app`.
- R1: A4 `split_claims` / `carries_other_content`: a gap sentence stays exempt only if no digit and at most 3 non-connective words remain after
  stripping the marker. A4 reports `gap_exempt`, `gap_exempt_share`, `gap_exempt_sentences`. Rule in EVAL.md (A4 row).
- R2: T2, T3, R2 return `reseed_required` and print to stderr. AFTER ANY T2, T3 OR R2 RUN, RE-RUN `python -m eval.seed` BEFORE A DEMO (the clear wipes the recorded demo cache).
- R3: `Ledger.rows()` reads under `LOCK_SH`. R4: only `TaskFailed` is recorded as an item failure; other `AppError` is fatal for the phase.
- Should-fix 11: `REF_SIM_MIN = 0.5` on ref matches, in EVAL.md. One fixture item changed ("Safeguarding" -> "Provide your safeguarding arrangements").

## Left
- Inputs still absent (keys, trap sets, fixtures, packs); live provider path (L1); `--live` still refused.

## Verify
`cd app/backend && TEST_DATABASE_URL=... python3.13 -m pytest -q -o addopts="" tests/test_tender_eval.py`; `python -m eval.run config`.

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

# STATUS (T-190, slice S6: claim check and export gate) - code done, awaiting reviewer PASS

Branch `p/sme-council-tender-drafting/T-190`. Not merged. Migration 0018 (drafts.check_sha256 and checked_at, source_documents.deleted_at,
and the (tenant, sha256) uniqueness becomes a partial unique index on live documents). alembic upgrade, check, downgrade -1, upgrade,
check clean. No live model calls (ScriptedFakeAI / Judge fakes only).

## Done
- `app/tender/claimcheck.py`: `ClaimcheckOutput`, `CLAIMCHECK_SPEC` (medium effort, 6000 cap; the draft and the cited passages only, each in a
  DATA block, the same `check_payload` for the app and the harness), `apply_rules` (pure): span not in the draft is discarded; `supported`
  needs a quote that is a normalised substring of a cited passage; every number, GBP/% figure and accreditation code of the span must be in
  the quote; a citation outside the retrieved set, a removed passage, or no citation at all gives `unsupported`; the unchecked-sentence detector
  (a digit, GBP, %, year, accreditation code or a run of 2+ capitalised words not under any claim span, per trigger, so a tiny span cannot cover a
  long sentence) adds `unchecked` claims. `claimcheck_handler` (runner kind `claimcheck`), `store_check` (claims replaced, draft.check_sha256 =
  text_sha256, draft status `checked_ok` or `blocked`), failure hook, a gap-only draft is checked with no model call.
- `app/tender/gate.py`: pure `export_allowed(pack, requirements, drafts, claims, signoff, live_evidence_ids, statement_version) -> (bool, reasons)`
  over plain dataclasses, plus `drafts_digest` (confirmed requirements with kind and word limit, and each latest draft's text hash and version).
  Reasons are `code: message` (`not_confirmed`, `no_questions`, `missing_draft`, `not_checked`, `claims_blocked`, `evidence_removed`, `over_limit`,
  `no_signoff`, `statement_changed`, `digest_mismatch`). The text hash is recomputed, the limit is the current requirement's, markers in the text
  count as citations as well as claim ids. `claimcheck.load_gate_inputs/export_check` build the inputs from rows.
- Routes: `POST /packs/{id}/check` (202, idempotent, 409 `nothing_to_check`; pack `checking`), `GET /packs/{id}/export-check`,
  `GET /requirements/{id}/claims`. The pack ends the check as `ready` (every question checked clean) or back to `drafting`.
- Evidence delete is a soft delete (T-186 F10): `source_documents.deleted_at` and `evidence_items.deleted_at`, passage text kept; hidden from the
  list, search and the check; the gate treats it as deleted; packs whose drafts cite it go `ready` -> `drafting`; the same file can be uploaded again.
- T-199: edits reset a ready pack (`reopen_pack`: draft edit, AI redraft saved, requirement add or patch, evidence delete). Sizing test
  (`test_upload_extract_draft_and_check_fit_the_30k_trial_day`): reservations extract 18,046 / draft 11,344 / check 13,758 (Azure headroom 1,500);
  settled 4,137 / 2,061 / 2,265. One question end to end settles at about 8.5k; the largest pack that fits one trial day (every step
  settled + next reservation <= 30k, all drafts then all checks) is **3 questions**. A longer tender needs a paid plan or a second day.
- T-200: extract pack lock is now the first statement of the write transaction (concurrency test); the F5 limit window starts at the question's heading
  (the line above the quote, or the one-line block above it, or the numbered line), never at the previous question.
- Tests: `test_tender_gate.py` (7, incl. a 600-example Hypothesis property against an oracle), `test_tender_claimcheck.py` (27), extract +4,
  one ingest test updated for soft delete.

## Design deviations / notes
- `hypothesis` is a new test dependency (not yet in pyproject dev extras or requirements-dev.txt; the Lead should add and re-pin it).
- Passage text for the check is cut at `APP_PASSAGE_CHARS` (1000), like the draft's input, so a quote beyond that is unsupported (safe direction).
- Number words ("forty") are not figures; a draft that says 40 against "forty" is downgraded (false block, safe direction).
- No sign-off route yet (S7); `Signoff` rows are read by the gate when they exist. The statement text is S7's; only `STATEMENT_VERSION = "v1"` is here.
- A removed requirement stays in the digest history only through its absence (the digest covers confirmed rows).

## Left
- S7 sign-off and S8 export route must call `claimcheck.export_check` / `gate.export_allowed` again server-side. No frontend.

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

# STATUS (T-190 review fixes)

Done: must-fix 1 (claim check: names must be in the quote, minimum quote size `quote_big_enough`), 2 (DATA.md says evidence deletes are soft),
should-fix 3 (own-sentence marker needed; repeated unmarked sentence flagged), 4 (gate pack state is an allow-list), 6 (0018 downgrade warning).

Board-worthy: **add a purge horizon for soft-deleted evidence documents and their passage text** (today they are kept until account deletion; DATA.md says so).

Left for S7/S8 (reviewer items): 5 (`pack_checked` ignores evidence liveness; a delete during `checking` is not reopened), 7 (extract heading heuristic
can give an imperative-question line the previous question's word window; known limitation), 8 (S7 sign-off and the check route should lock the pack row
`FOR UPDATE`). Also: `hypothesis` is now in the dev extras and requirements-dev.txt (the T-190 line above is out of date).

Threat note (S6): claims with no figure, code or name rest on the model's judgement plus the human sign-off; A6a measures how often the model gets them wrong.
