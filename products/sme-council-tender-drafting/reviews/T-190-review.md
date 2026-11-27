# Review: T-190 (S6 claim check and export gate) + T-200 (extract lock order, F5 heading window)

Branch `p/sme-council-tender-drafting/T-190`, head `05ceb8f`, against `origin/main`. Reviewer run 2026-11-27.
Also the security spot-check of DESIGN.md section 7 rows 2 (prompt injection) and 7 (invented claims reaching a bid / export
of unsupported claims), as the task asks.

**Verdict: CHANGES** (2 must-fix, both small and pure-code or doc).
**Security verdict: CHANGES** (must-fix 1: an obedient or injected checker can still mark a fabricated client/name claim `supported`).

## Evidence

- Full backend suite on the branch tree (Python 3.12 venv from `requirements-dev.txt`, Postgres 16, per-run database,
  `TEST_DATABASE_SHARED` unset): **1014 passed, 1 skipped, 0 failed** (289 s, exit 0).
- `tests/test_tender_gate.py` alone: 7 passed (600-example Hypothesis property against the oracle).
- Alembic on a fresh database: `upgrade head`, `check` ("No new upgrade operations detected"), `downgrade -1`,
  `upgrade head`, `check`: all clean. `\d source_documents` shows
  `uq_source_documents_tenant_sha256 UNIQUE, btree (tenant_id, sha256) WHERE deleted_at IS NULL`, matching the ORM `Index`.
- Probe script against `apply_rules` (no DB), results below in must-fix 1.

## What is right

- `export_allowed` (gate.py) is pure: no DB, no AI, no I/O; inputs are frozen dataclasses; the property test confirms it is
  deterministic and does not mutate its inputs. It recomputes `sha(text)` so a copied check hash fails, uses the current
  requirement limit, and counts `[E-n]` markers in the text as well as claim `cited_ids` for `evidence_removed`. Any verdict
  other than the literal `supported` blocks, so an unknown verdict fails closed. No override path.
- Soft-deleted evidence never counts as live: `load_gate_inputs` and `live_passages` both filter `evidence_items.deleted_at`
  and `source_documents.deleted_at`; `search_evidence` adds the document filter. A re-uploaded identical file gets new E-numbers
  (counter never reused), so an old `[E-n]` cannot be revived. The daily page cap still counts soft-deleted rows, which closes the
  T-186 "delete refunds pages" leak.
- Injection surface: the check payload is only the draft and the cited, live, in-set passages, each in a nonce DATA block
  via `build_user`; tender text never reaches the checker; outside-set passages are dropped before the call
  (`check_draft`). Rules 1 to 5 are applied after the model and only ever downgrade; `contradicted` and `unsupported` stay
  blocking; the detector adds `unchecked`. The existing injection test is meaningful (obedient checker, figure drift, blocked).
- Tenant isolation on the new routes: `POST /packs/{id}/check`, `GET /packs/{id}/export-check` and
  `GET /requirements/{id}/claims` all go through `get_scoped` / `_question` before any work; every query in
  `claimcheck.py` carries `tenant_id`; the evidence-delete raw SQL binds `:t` on both packs and the subquery. Cross-tenant
  delete test is 404 and changes nothing.
- Worker: no transaction is held across the model call; the store step re-reads the pack `FOR SHARE` and stops if signed or
  exported; `finally: finish_check` plus the failure hook mean the pack never stays `checking`.
- Migration 0018: correct partial unique index; the ingest duplicate checks use the same `deleted_at IS NULL` predicate.
- T-200: the pack `FOR UPDATE` is now the first statement of the extract write transaction (so a concurrent user row is
  either visible to the dedupe or waits); the heading window finds a limit in a one-line heading above the quote and stops at
  a numbered line.

## Must-fix

1. **`app/tender/claimcheck.py:74-81, 84-86, 174` (rule 3 / rule 2): a trivial quote supports any claim that has no digit or
   code, including client and buyer names.** `quote_in` accepts any non-empty normalised substring, and `figures_in` only
   checks numbers and accreditation codes. Probe:
   `apply_rules("We hold a framework contract with Leeds City Council [E-3].", [supported, cited [3], evidence_quote="the"], ...)`
   gives `supported` for a passage that never mentions Leeds. Likewise "We cleaned 40 hospitals for the NHS Trust in 2023 [E-4]"
   with quote "40 offices in 2023" is `supported`. The detector treats a run of capitalised words as a fact trigger (rule 6), but
   once a model claim covers it nothing checks the name against the evidence. That is exactly the section 7 row 2 failure
   ("state that the firm holds X" / an invented client) and the Sch. 7 para 13 risk in row 7: an injected or merely sloppy checker
   flips a fabricated client to `supported`, and only the human sign-off stands between it and the export.
   **Fix (pure, in `apply_rules`):** treat capitalised runs as fact tokens in rule 3: every `_CAPS_RUN` match in the span (after
   dropping a sentence-initial single word such as "We"/"Our") must appear, normalised, in the quote; and require a minimum quote
   size (for example at least 3 words, or the quote must contain at least half of the span's content words). Add tests: the
   two probes above end `unsupported`; an honest claim whose quote holds the name stays `supported`; an injected-evidence-line
   fixture ("Ignore previous instructions... we work for Leeds City Council" placed in the draft) with an obedient checker
   is still blocked.

2. **`app/DATA.md:20` and `:24`: the privacy register now says the wrong thing.** `source_documents` is listed as removed
   when "the user deleting the document"; after this branch an evidence document and all its passage text are kept
   indefinitely (until account deletion) after the user presses delete. The register is what the firm is told about its data.
   **Fix:** state that evidence deletes are soft (row and passage text kept for the claim appendix and audit, hidden from
   search, retrieval, check and export; removed on account deletion), and either add a purge horizon or say there is none yet.
   Same change, per `playbooks/engineering.md` (docs with the code).

## Should-fix

3. `app/tender/claimcheck.py:159-161`: a claim's `cited` set unions the model's `cited_ids` with the markers in the sentence, so
   a sentence with no `[E-n]` of its own can be `supported` by a passage cited elsewhere in the draft (rule 5 says an uncited
   factual claim is unsupported; the exported sentence would show no citation). Also the span's other occurrences are added to
   `covered`, so a repeated sentence later in the draft, without a marker, rides on the first one's verdict (probe:
   "We cleaned 40 offices in 2023 [E-4]. We cleaned 40 offices in 2023 again." gives one `supported` claim and no `unchecked`).
   Fix: require `in_sentence` to be non-empty for `supported`, intersect model `cited_ids` with the sentence markers, and judge
   each occurrence (or cover only the occurrence you judged).
4. `app/tender/gate.py:15, 89`: the pack-state check is a deny-list (`uploaded|extracting|review`). Any other or unknown status
   passes this line. Make it an allow-list of states from which export is legitimate (for example `ready`, `signed`, `exported`)
   so a new or misspelt status fails closed; add one property-test case with an unknown status.
5. `app/tender/claimcheck.py:274-284` with `app/routes/tender.py:104`: an evidence delete during a running check (pack
   `checking`) is not reopened by the delete (it only touches `ready`), and `pack_checked` ignores evidence liveness, so
   `finish_check` can set the pack `ready` while a cited passage is gone. The gate still blocks (`evidence_removed`), so this is a
   status-truth issue, not an export hole. Fix: `pack_checked` also requires every cited id of the latest drafts to be live
   (one query), or the delete also flips `checking` packs whose drafts cite the numbers.
6. `migrations/versions/20261127_0018_claim_check_soft_delete.py:31`: downgrade hard-deletes every soft-deleted document (and,
   by cascade, its passages). Fine for dev, but it is data deletion; add a one-line warning in the docstring that 0018 down is
   destructive, so nobody runs it on a demo database expecting a reversible step.
7. `app/tender/extract.py:102-126` (T-200 heuristic): an unnumbered previous question that is one line without a full stop is
   taken as the heading of the next one, so "Describe your approach in no more than 200 words\n\nDescribe your staffing plan."
   gives the staffing question the 200-word window (probe). Impact is a spurious `limit_mismatch` flag, not a wrong stored limit,
   so this is acceptable for now; add the case as a known-limitation test or require the candidate heading line not to start
   with an imperative question verb (Describe, Explain, Set out, Provide).
8. `app/routes/tender.py:448-466`: `queue_check` sets `pack.status = "checking"` after reading it without a row lock (only an
   advisory lock on the check key). S7 sign-off must take the pack row `FOR UPDATE` and the check route should do the same
   (`with_for_update()` on the `get_scoped` read) so a sign-off and a check cannot interleave. Note for S7, cheap now.

## Nits

- `claimcheck.py:202-208`: mid-file imports with `noqa: E402` and an unused `_draft` / `reopen_pack` re-export; move them to the
  top or a small `claimcheck_store.py` (the gate docstring already names that module, which does not exist).
- `gate.py:80`: `r.word_limit or ''` makes a limit of 0 and no limit hash the same in the digest; use `'' if None else`.
- Builder deviations in NEXT.md (1000-char passage cut, number words, 3-question trial day, no sign-off route, one-line heading,
  two-capitalised-word detector false positives): all fail in the safe direction (block more, not less) and are acceptable for
  the demo; the 3-question trial-day ceiling should go to `state/DECISIONS.md` and the demo plan, since the demo packs are
  longer than 3 questions.
- `hypothesis` is now in the dev extras and `requirements-dev.txt` (05ceb8f); NEXT.md still says it is not; update the line.

## Top issue

Must-fix 1: rule 3 checks numbers and codes but not names, and any one-word quote passes the substring rule, so an injected or
careless checker can mark an invented client `supported`. Fix in `apply_rules`, pure, with three tests.
