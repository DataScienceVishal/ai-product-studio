# Review: T-205 (e2e follow-ups from the T-192 e2e re-review)

Branch `p/sme-council-tender-drafting/T-205`, HEAD `519e19d`, against `main`. Reviewer run, 2026-11-28.

**Verdict: PASS**

## Evidence
- `git diff main...HEAD` changes 2 files and 12 lines, all in test tooling: `app/scripts/e2e.sh` and `app/tests/e2e/tender_flow.cjs`. No product code changes.
- Two back-to-back `scripts/e2e.sh` runs on the default ports 8000 and 4173 both exited 0. Each printed `E2E PASS: tender core flow (7 steps)` and `E2E PASS: core flow`. On the previous branch, the second run exited 2 with "port in use".
- After both runs, `pgrep` found no uvicorn or vite process still running.
- An EXIT trap does not swallow the script's exit code. A minimal bash check with `set -euo pipefail`, a trap that never frees the ports, and `exit 3` still exited 3. It printed the warning.

## Checked
- **`cleanup()`** works as described. It kills both process groups, as the old trap did. It then polls `port_free` on both ports every 0.5 s, for at most 20 polls (10 s), and prints a warning if the ports are still taken. It never loops forever and never changes the exit status.
  - The `&&` chain inside the loop does not trip `set -e`.
  - `port_free` is defined at line 13, before the trap is set.
- **`tender_flow.cjs`**: the body is now cut at `"\nTABLEROWS:"`, so the answer-order check and the `[E-n]` check only see document paragraphs. The appendix heading is still a paragraph, so its assertion is unaffected.

## Suggestions (non-blocking)
- These remain open from the earlier review:
  - the dead `...click().catch(() => {})` navigation in `tender_flow.cjs`;
  - running the docx check as `python -I`;
  - asserting the 150-word limit on the checklist page;
  - asserting the source passages on the draft page.
