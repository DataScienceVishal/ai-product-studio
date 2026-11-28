# Review: T-205 (close the e2e coverage gaps from T-192)

Branch `p/sme-council-tender-drafting/T-205`, HEAD `03f952c`, against `origin/main`. Reviewer run, 2026-11-28.

**Verdict: CHANGES** (1 must-fix item, a one-line test change. No product code needs to change.)

## Evidence
- `git diff origin/main...HEAD --stat`: 6 files, all under `app/tests/e2e/` and `app/scripts/e2e.sh`. No files under `backend/app/` or `frontend/src/` changed.
- `NODE_PATH=/opt/node-tools/node_modules bash scripts/e2e.sh` ran twice in a fresh worktree, on separate ports (8211/4211 and 8212/4212). Both runs exited 0, and both printed all six results:
  - `E2E PASS: tender core flow (7 steps)`
  - `E2E PASS: tender export refused`
  - `E2E PASS: tender limits, gaps and blocked claims`
  - `E2E PASS: tender unicode`
  - `E2E PASS: tender larger pack`
  - `E2E PASS: core flow`
- Failure path: `tender_unicode.cjs` was run against a dead base URL. Both scenarios printed `E2E FAIL`, wrote their screenshots, and the process exited 1. `runScenario` sets `process.exitCode = 1`. A failure outside the try block (for example a browser launch failure) becomes an unhandled rejection, which also exits non-zero. In `e2e.sh`, each scenario runs as `|| one=$?` and the first non-zero status is kept, so a failing scenario fails the script. `core_flow` still runs and `logs:` still prints.
- Backend `pytest`: 1212 passed, 0 failed. pyproject has `addopts = "-q"`, so the summary line is suppressed, and the count comes from the progress dots. Frontend `vitest`: 232 passed in 7 files. Both match the builder's claims.
- Exported unicode docx (`e2e2/fixtures/unicode-export.docx`), read back with python-docx. The answer paragraphs contain `Zoë O’Brien–Núñez`, `“Zoë Café”`, `£1,250,000`, `£75,000`, `“Aroma Bär”` and `Besançon Road` exactly, with `[E-1]` and `[E-2]` markers. The title is `Quartier – Zoë’s pack`.

## What is right
- **The refusal path is real.**
  - `exportDoc` (`tender.tsx:709-721`) only builds a download link after `apiDownload` succeeds. On a refusal it calls `setProblem`, which renders an error `Alert` with `role="alert"`. Only error alerts carry that role (`ui.tsx:94`): the info notice and the success note use `status`.
  - So "an alert appeared" means the export call failed. `downloads` is `[]` at that point, and no success note is shown. These are genuine checks that no file was produced.
  - The reopen race is handled. The `other` page waits for "Responsibility statement", and that blockquote is rendered only on the unsigned branch, so the wait cannot pass until the reopen POST has returned and the page has reloaded.
- **No race-prone navigation from T-192.** Every task is queued through `queueTask` (it waits for the 202) and finished through `waitIdle` (polls `/status`, with a 90 s deadline). The `waitForTimeout(500)` there only sets the poll interval. There are no fixed-sleep synchronisations and no swallowed `.catch(() => {})` clicks.
- **Limits, gap and unsupported-claim UI are asserted on what the user sees:**
  - word count "n words of 150/40/10";
  - the exact gap marker text, "1 gap to fill", and "This answer cites no evidence.";
  - the "Over the limit" badge appears only after the user's longer edit, and the auto-draft for the over-long passage turns into a gap rather than being silently cut;
  - the coverage `Over` badge and gap count;
  - the "10-word limit" and "not supported by evidence" blockers;
  - the `tr`/`mark[data-verdict='unsupported']` rows carrying the new claim, the original claim staying supported, and the sign-off button disabled even with the tick and name filled in.
- **Unicode and the larger pack go through extract, draft, check, sign-off and export, and the docx text is compared.**
  - The header must include the accented reviewer name.
  - The footer must carry the statement.
  - Answers come from evidence-only strings, which can only appear if the answer text survived.
  - A mojibake regex runs over the body.
  - The appendix must contain the pound figure and the file name.
  - In the larger pack, all 8 answers must appear in order (`indexOf` strictly increasing, and a missing answer fails because -1 > -1 is false). The pack needs at least 8 distinct `[E-n]` markers and at least 9 appendix rows.
- `readDocx` runs `python -I`, which addresses T-192 suggestion (c). The T-192 suggestions on word limits on the checklist page are covered too.

## Must-fix

1. **`tender_limits.cjs:182-185`: the server-side refusal of sign-off is vacuous.**
   - **The problem.** The POST sends `statement_version: "x"`. The sign-off route rejects that with `422 statement_required` (`routes/tender.py:577-578`) before it looks at claims. So `status >= 400 && < 500` passes even if the server would let an unsupported claim through. The step says it proves the opposite.
   - **Line 185 has the same weakness.** The pack is not signed, so the export returns 409 for `no_signoff` whatever the claims are.
   - **Fix.**
     - Send `statement_version: "v1"` (or read it from `GET /api/packs/<id>/coverage` as `statement.version`).
     - Assert `status === 409`, `json.error === "export_blocked"`, and `json.message` matching `/claims_blocked/`.
     - For the export call, assert `json.message` matches `/claims_blocked/` as well.

## Suggestions (not blocking)
- **(a) `tender_refusal.cjs:83-85`.** The second regex `/removed|evidence/i` repeats the filter, so it adds nothing. Assert the specific reason, `/evidence_removed|E-1 .*was removed/`. (`claims_blocked` messages also contain "evidence".) In practice nothing else changes between the sign-off and the export, so this does not make the step wrong today.
- **(b) `tender_refusal.cjs:63`.** `/claim check|not been checked|checked/i` is loose, because "checked" matches almost anything. Match `/no claim check for its current text/`.
- **(c) `tender_limits.cjs:145`.** `/\t1\t/` depends on Chromium's `innerText` tab layout for table rows. Prefer a cell locator, for example `getByTestId("cov-2").locator("td").nth(3)` with text `1`.
- **(d) `tender_unicode.cjs:232`.**
  - `"“Zoë Café”"` and `"–"` are also present in the question headings that the export writes into the body, so those two entries would pass with no answer.
  - The other five strings carry the check.
  - Add an assertion that the docx title is `Quartier – Zoë’s pack`, and check that `suggestedFilename()` is sane for a unicode pack title.
- **(e) The "larger" fixture is 8 questions over 4 pages.** That is enough to prove multi-page extraction and ordering. Real council ITTs often run 30-60 items, so a future perf check of extraction and draft time at that size would be worth a separate task.
- **(f) `uploadEvidence` posts through the API, not the UI.** The comment says so, and the UI upload is covered by `tender_flow.cjs`. That is fine.

## Re-review scope
Must-fix 1 only. Re-run `scripts/e2e.sh` once and attach the output.

## Re-review (5798483, 2026-11-28)

**Scope:** `git diff 85cff27..5798483` (one file, `app/tests/e2e/tender_limits.cjs`, +8/-2).

**Must-fix resolved.** The sign-off POST now sends `statement_version: "v1"` (equal to `gate.STATEMENT_VERSION`), so the 422 `statement_required` branch in `routes/tender.py` `sign_off` (line 577) is no longer what refuses it. The test asserts exactly 409 with `not_ready` or `export_blocked`, and the export GET asserts 409 `export_blocked` with `/claims_blocked/` in the message.

**Would it fail if an unsupported claim got through?** Yes, via the export assertion. `gate.export_allowed` (gate.py 113-117) collects every reason and adds `claims_blocked` only when a latest-draft claim has a verdict other than `supported`; `routes/tender.py` 615 joins all reasons into the message. If the claim were wrongly marked supported, the message would lack `claims_blocked` and the test fails. The UI assertions at lines 79 and 89 (“1 claim is not supported”, “1 unsupported”) also guard it.

**Suggestion (non-blocking):** the sign-off refusal alone does not isolate the claim. At that point the pack also has the question 2/3 gaps and an over-limit answer, so `not_ready` would fire even with no unsupported claim. The export assertion covers this, so it is fine as is. A follow-up could fix the gaps first so the unsupported claim is the only blocker.

**Tests:** `NODE_PATH=/opt/node-tools/node_modules bash scripts/e2e.sh` exit 0; 6/6 PASS (core flow 7 steps, export refused, limits/gaps/blocked claims, unicode, larger pack, core flow).

**Verdict: PASS**
