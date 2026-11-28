# Review: T-192 part 2 (Playwright e2e of the 7 SPEC steps)

Branch `p/sme-council-tender-drafting/T-192-e2e`, HEAD `bfe5551`, against `main` (`630897a`). Reviewer run, 2026-11-28.

**Verdict: CHANGES** (3 must-fix items. All are in the test files. No product code needs to change.)

## Evidence
- `E2E_LOG_DIR=<scratch> NODE_PATH=/opt/node-tools/node_modules bash scripts/e2e.sh` printed `E2E PASS: tender core flow (7 steps)` and `E2E PASS: core flow`. It exited 0 in 16.5 s. Afterwards no uvicorn or vite process was left running, so the trap cleanup works.
- Timings from that run's `api.log` (they matter for item 1):
  - `POST /extract` finished at 29.571. The checklist page's first `GET /status` came at 29.637, about 60 ms later.
  - `POST /draft` finished at 33.452. The draft page's first `GET /draft` came at 33.524, about 70 ms later.
- The caller reported backend pytest 1192 passed, vitest 232 passed and tsc clean. I did not re-run those suites, because the diff touches no product code.
- `git diff main...HEAD --stat`: 6 files, all under `app/tests/e2e/`, `app/scripts/e2e.sh` and `NEXT.md`. No files under `backend/app/` or `frontend/src/` changed.

## What is right
- `tests/e2e/e2e_app.py` is a 3-line ASGI module, `create_app(ai=ScriptedFakeAI())`. It uses the existing `ai=` keyword of `create_app` (`backend/app/main.py:173`) and adds no route, flag or env hook. The `Dockerfile` copies only `backend/app`, `backend/migrations` and `alembic.ini`, so `tests/` cannot reach the image. This is safe.
- `e2e.sh` is still safe:
  - The drop is guarded by the `*e2e*` name check (lines 20-23).
  - Both servers run under `setsid`, and the EXIT trap kills both process groups.
  - The port pre-check is unchanged.
  - `AI_WORKER_THREADS=2` only affects the e2e process.
- The test uses no fixed sleeps. Every wait is a Playwright locator wait. Background work gets an explicit 90 s `LONG` timeout.
- Step 7 is genuinely checked. The test saves the download, `zipfile.testzip()` passes, python-docx opens the file, and the test asserts the exact header string with the reviewer name. The `[E-\d+]` assertion on the body is real, because only answer paragraphs carry numbered markers (the italic note says `[E-n]`, which does not match).
- Step 5 is a real wait. The pack only becomes `ready` ("Ready to sign off") through `finish_check` (`claimcheck.py:396`). Drafting leaves it at `drafting`. The verdict assertions use `\bSupported\b` plus a negative check for Unsupported, Contradicted and Not checked. The sign-off button then succeeding shows that the server-side gate passed.
- The `core_flow.cjs` fix is correct for a billing-off build.

## Must-fix

1. **Two navigation races make the test flaky: `tender_flow.cjs` lines 41-42 and 63-66.**
   - **What happens.** The test clicks "Find the requirements" (or "Draft the answers") and then immediately follows a link to another page. The click handler's `POST` is still in flight. The new page calls `usePackStatus`, which fetches `/status` once and polls only if that first response is busy (`tender.tsx:118-135`).
     - Checklist page: if the `GET /status` reaches the server before `POST /extract` commits, the pack still reads `uploaded` with no queued task. The page never polls, the rows stay empty, and "Confirm the checklist" never appears. The test fails after 90 s.
     - Draft page: the pack is already `drafting` before `POST /draft`. If the status read wins the race there, `busy` is false, the page never reloads, and `[E-n]` never appears.
   - **How close it is.** This run had about 60-70 ms of headroom (see Evidence). A slower DB or CI box can lose it.
   - **The existing waits do not help.** The guards at lines 64-65 do nothing. "Open answer" links are rendered for every confirmed question before any draft exists (`tender.tsx:290`). "Draft the answers" stays visible while busy, because it is only disabled.
   - **Fix.** Before navigating away, wait for the action to land. For example:

     ```js
     await Promise.all([page.waitForResponse(r => r.url().endsWith("/extract") && r.request().method() === "POST" && r.status() === 202), button.click()]);
     ```

     Do the same for `/draft`. Then delete lines 64-65.
   - **Also wait for drafting to finish.** Before clicking "Check the claims" (line 73), wait until the draft task is done, for example with `expect.poll` or a `waitForFunction` on `/api/packs/<id>/status` until no task is `queued` or `running`. Today that wait only happens implicitly: Playwright waits for a disabled button, but only for the 30 s default timeout. Worse, after `goBack()` the button is enabled until the first status fetch returns. A check queued while the draft task is still running checks only the first draft. The pack then ends as `drafting`, not `ready`, and the test fails at line 74.

2. **Step 6 asserts nothing about coverage, and the step 4 and 7 content checks are vacuous.**
   - **Step 6 (lines 81-90).** SPEC step 6 is "a table showing every question answered, within limit, mandatory items covered, gaps still open". The test only waits for the statement, ticks the box and signs off. Assert the two coverage rows (`data-testid="cov-1"` and `cov-2`): Answered "Yes", words shown as "n / 150", Gaps 0 and Checked "Yes". Also assert that the page does not contain the word "compliant" as a claim.
   - **`/safeguarding/i` checks are vacuous (lines 69 and 112).** In both places "safeguarding" is already in the question text: the draft page renders `req.text`, and the export writes the question as a heading. So both checks pass even when no answer text exists. Assert a phrase that can only come from the drafted answer, such as `/42 staff/` and `/12 apprenticeships/` from the fixtures. In the docx, assert that the safeguarding answer comes before the social value answer (SPEC: "answers in question order").
   - **Step 7 footer.** SPEC also requires the footer to repeat that the firm is responsible. Add the footer text to the Python check (`s.footer.paragraphs`) and assert it.
   - **Step 7 appendix.** Assert the appendix heading ("Appendix: claims and their sources") and at least one table row. You can read the rows through `d.tables`.

3. **`e2e.sh` lines 56-57: if the tender flow fails, the script exits silently and skips `core_flow`.**
   - Under `set -e`, a failing `node tender_flow.cjs` ends the script at once. That has two effects:
     - `core_flow.cjs` never runs.
     - `echo "logs: $logs"` never prints. By default `$logs` is a fresh `mktemp -d`, so the failure screenshot and `api.log` are written to a directory nobody is told about.
   - Fix: run the tender flow with `|| status=$?` like `core_flow`, keep the first non-zero status, and always print the log directory.

## Suggestions (not blocking)
- **Line 60:** remove the dead navigation `...first().click().catch(() => {})`. It swallows any error, and line 61 navigates anyway.
- **Step 2:** also assert that the checklist shows the 150-word limit for both questions. Extracting limits is part of SPEC step 2.
- **Step 3 ("show what was found"):** on the draft page, assert that `data-testid="passage-1"` (or the first passage) shows the evidence text. Today the test only checks `[E-n]`.
- **Step 5:** open the second answer too, or assert both coverage rows show "n supported" (overlaps item 2).
- **Line 110:** run the docx check as `PYTHON -I -c ...`. The current working directory is `frontend/`, and `-c` puts it on `sys.path`.
- **`core_flow.cjs`:** `getByText("Free trial:").count() === 0` is checked as soon as the heading renders, so it could pass before any banner had a chance to load. It is acceptable while billing is off at build level. Pairing it with the existing `/api/billing/plans` 404 check (already present) is enough.
- **`make_fixtures.py`:** the fixtures are tuned to ScriptedFakeAI heuristics (no full stop, no shared words), and the comment explains why. Keep it. If ScriptedFakeAI changes, this e2e will fail first, and that is the right place for it to fail.

## Re-review scope
Items 1-3 only. All three are test-file changes. Re-run `scripts/e2e.sh` three times in a row and attach the outputs.
