# T-56 slice 3 review: scorer, extractor, budget guard

Reviewer, 2026-11-24. Branch `p/pepr-packaging-data-pipeline/T-56` at 90e0745. Scope: `benchmark/score.py`, `benchmark/tests/test_score.py`, `extractor/` (package, CLI, tests). Checked against `benchmark/README.md` ("Scoring rules", "Run budget"), the kill test plus amendments 1 and 2 in `state/ideas/pepr-packaging-data-pipeline.md`, and slice 2 re-review items 3, 4, 5 and 8. No model or network calls were made.

## Verdict: CHANGES

The scorer and extractor are careful and mostly faithful to the fixed rules. Two things must be settled before the first paid call, because the test set is run only once: (1) as configured, the budget guard is likely to stop the 30-sheet test run partway through, and (2) pass mark 4b uses a stricter definition than the kill test, and that choice is not yet written down. Both fixes are small.

## Evidence

- `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` (from the product folder): **65 passed in 6.05s**.
- Oracle test: truth answers fed through the full pipeline (layout text and images, `clean_output`, scorer) score 100% and pass every check. So the scorer accepts the truth's own quotes, and image pages are sent for every scanned page.
- My check: all 234 truth quotes on text sheets appear verbatim, after `norm_quote`, in the pypdf **layout-mode** text that the extractor sends. A model that copies quotes from its own input should therefore pass the scorer's plain-text check.
- `RAM_CATEGORY` covers exactly `MATERIAL_VOCAB`, and it matches every truth `ram_category` in the test and tuning truth files (0 mismatches).
- System prompt: 4,829 bytes.

## Critical issues

### C1. The budget guard will probably stop the one-shot test run early (`extractor/extract.py:12`, `extractor/run.py:249-255`)
The guard is correct: it refuses before a call whose worst case could cross USD 12 or 3M tokens. Line 147 reserves the estimated input (counted as 1 token per byte, an upper bound) plus all of `max_output_tokens`. At the default `max_output_tokens=12000`, that reservation is about USD 1.44 of output plus about USD 0.1 to 0.2 of input, so roughly USD 1.6 per call. The guard therefore refuses every call once spent is above about USD 10.4.

The plan is about USD 2.5 for tuning plus up to USD 9.49 for 30 sheets at the per-sheet bar. On that plan the guard refuses roughly the last 5 to 8 test sheets. `run.py` then returns 3, and the unrun sheets score as empty predictions. The test set "is run once for the score", so a truncated run is wasted and cannot be rerun. Note also that any sheet that genuinely needs close to 12k output tokens costs about USD 1.4 or more, which is far above the USD 0.316 bar anyway.

**Fix (no change to the caps):**
- (a) Lower the default to `max_output_tokens` 6000 (reservation about USD 0.85). After tuning, set it to about 3x the largest output observed on the tuning sheets, and never below 4000, and record the value used.
- (b) Add a pre-flight check in `run.py` for `--set test`: refuse to start unless the remaining budget is at least `n_sheets * 0.316 + one worst-case reservation`. Print the shortfall so tuning stops in time rather than the test run.
- (c) Add a test for (b).

### C2. Pass mark 4b uses a stricter definition than the kill test, and the choice is unrecorded (`benchmark/score.py:234`)
Kill test pass mark 4 says: "Contradictory values must be flagged as conflicts, not silently chosen, in at least 80% of conflict cases". The README says pass-mark definitions stay in the kill test. Rule (a) and amendment 1 item 2(a) define how a conflict *field* scores (flag AND both values), and that feeds field accuracy. They do not redefine pass mark 4.

The scorer's `4b` check uses `conflict_ok`, the strict both-values rate. The flag-only rate is reported as `conflict_flagged_any` but is not used for the pass mark. Being stricter is defensible, but it is a pass-mark definition. If it is chosen after seeing results, it can be argued either way.

**Fix:** before any model call, choose one of these:
- add a dated "Amendment 3" to the idea file stating that 4b is the strict both-values rate (my recommendation, since a flag without the values is not usable by a producer); or
- switch `4b` to `conflict_flagged / conflict_slots` and keep the strict rate in field accuracy.

Either way, add one line to the README.

## Rules checked (faithful unless noted)

- **Slots.** Per truth component: material, colour, weight, the plausible features, and `ram_category` only when the truth material is present. Taken from `tx.scored_slots`. OK.
- **Closed-vocabulary equality.** Uses `taxonomy.canonical` with no containment matching. OK. Weight uses `weight_within`. OK.
- **(a) Conflicts.**
  - A flag plus both values within tolerance scores 1; order does not matter, and the value count must be exactly 2.
  - A silent pick scores 0 and counts as unflagged.
  - A flag on a truth-present weight scores 0 and counts as a false conflict.
  - A flag on a present string slot scores 0 without being counted as a false conflict. The rules only define false conflicts for weights, so this is fine.
- **(b) Traceability.** A value is untraced if any of its refs fails `quote_ok`, or if any conflict value has no passing ref. This holds on unmatched components too. It matches README (b): "Zero quotes may fail this rule" means each quote is checked. Two side effects:
  - A value outside the vocabulary is both wrong and untraced (`_canon` gives a sentinel). That is consistent with "the quote names exactly the extracted value", but it is a double penalty on pass mark 3. Say so in the slice 4 report.
  - Feature keys that are not in `tx.VOCAB` are skipped by the tracing loop at line 167, which is slightly lenient (see S1).
- **(c) Page text.** Text sheets use pypdf `extract_text()` and scanned sheets use the manifest `page_text`, both normalised inside `quote_ok`. OK.
- **(d) Component matching.**
  - Matching uses normalised names, greedy, one-to-one, in sheet order. Material is a tie-break only when the truth material is present.
  - An unmatched extracted component adds 4 plus its plausible-feature count as wrong slots.
  - A missed truth component misses all its slots.
  - OK.
- **Missing values.** An extractor value where truth is `missing` counts as fabricated and wrong. An absent key counts as wrong but not fabricated. OK.
- **Cost mark.** The check fails if there is no ledger, if a `--ledger` path does not exist (it reads as `{}`, and 0 of 30 sheets is not 30), or if any sheet has no cost entry. The mean is taken over all 30 sheets. OK.
- **Item 3, isolation.** The PDF is copied into an empty temp directory and only the copy is read. Tests monkeypatch `open` to prove `manifest` and `truth` are never opened. A source scan finds no truth or manifest names outside `run.py`. `taxonomy.py` does no file I/O. OK.
- **Item 4, layout-aware input.** Layout-mode text is sent for text pages and images for scanned pages, and the mode is recorded per page in the prediction. OK.
- **Item 5, guard before the call.** The guard checks before the call and reserves the full `max_output_tokens`. Reasoning effort is explicit (default `low`, validated). Billed tokens are logged per sheet to a JSONL ledger with fsync. A timeout or unreadable answer is charged at worst case. The ledger is reloaded at start-up, so tuning and test share one budget. Logic OK (see C1 for the configuration).
- **Item 8.** The prompt includes "Sleeve: none" -> `no sleeve` and "Liner: to be confirmed" -> missing. OK.
- **Azure gate.** `T56_SPEND_APPROVED=1` is checked both at construction and at call time, and the CLI returns 2 with "refused". Tested. OK.
- **Responses API shape.**
  - `POST {root}/openai/v1/responses` with an `api-key` header.
  - Request body: `model`, `instructions`, `input` (a user message of `input_text` and `input_image` parts, with data-URL `image_url` and `detail`), `max_output_tokens`, `reasoning.effort`, `store:false`.
  - Response parsing: `output[].type=="message"` -> `content[].type=="output_text"`, plus `usage.input_tokens` and `usage.output_tokens` (which include reasoning tokens). An `incomplete` status is charged its actual usage.
  - Consistent with `_starter/backend/app/ai.py` (same endpoint normalisation and Responses usage). Plausible.
- **Secrets.** The key is read only from the environment, sits in `self._key`, and is never printed. Error messages contain the HTTP status and at most 300 bytes of the *response* body. Nothing secret is logged. OK.

## Suggestions

- **S1.** `score.py:167`: count a non-missing predicted value under a feature key that is not in `tx.VOCAB` as untraced, or drop such keys in `clean_output`. Today it escapes pass mark 3 ("every non-missing value").
- **S2.** `providers.py:146`: a 5xx can arrive after the model has run and billed. Either charge the worst case before retrying a 5xx, or re-run `budget.check` before each retry. Today one reservation can cover up to 4 billed attempts.
- **S3.** `gpt-5.4-pro` reasoning effort: earlier "pro" deployments accepted only `high`, or `medium` and above. If `low` is rejected with HTTP 400, nothing is billed, but `run.py` will try every sheet anyway. Stop the run on the first HTTP 400, and confirm the accepted effort on the first tuning call. A forced `high` effort would threaten the USD 0.316 bar, so record it if that happens.
- **S4.** The ledger has no file lock. Run tuning and test sequentially and never in parallel; say so in `run.py`'s docstring.
- **S5.** `clean_output(raw, page_modes)`: `page_modes` is unused. Remove it.
- **S6.** `IMAGE_TOKENS_WORST=6000` is a reasonable upper bound. After the first scanned tuning sheet, record the billed image tokens.

## Re-review (fce0c59): PASS

Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` gives **73 passed in 6.66s** (8 new tests).

- **C1, fixed.**
  - `MAX_OUTPUT_TOKENS` is now 6000, so the worst-case reservation per call is about USD 0.72 of output plus input.
  - `budget.preflight` runs for `--set test`. It exits with code 4 and prints the shortfall unless the remaining budget is at least `30 x 0.316 + usd(20000, max_output_tokens)` (USD 10.50 at 6000), and it applies the same kind of check in tokens.
  - I checked the margin: the largest estimated input across the 30 test sheets is 16,913 tokens, below the 20,000 assumed in the pre-flight. So if the mean per-sheet cost stays within the bar, the guard cannot cut the run short.
  - If the run does get cut short, pass mark 5 would have failed anyway.
- **C2, settled.** The Studio Lead decision is logged on main (`state/DECISIONS.md` line 157, before any run). 4b is now `conflict_flagged / conflict_slots`, as the kill test wrote it. Rule (a)'s both-values requirement still counts in field accuracy, and the both-values rate is reported as information. The README is updated to match. No amendment is needed, because this follows the text written before any run.
- **S1, fixed.** A non-missing value under a feature key that is not in the vocabulary now counts as untraced.
- **S3, fixed.** HTTP 400, 401 and 403 now set `fatal`, and `run.py` stops with code 5.
- **S4, fixed.** `run.py`'s docstring now says to run tuning and test sequentially, because the ledger has no file lock.
- **S5, fixed.** The unused `page_modes` parameter is removed.
- **Still open (non-blocking).**
  - S2: a 5xx retry can bill more than one attempt under a single reservation. The USD 1.5 gap between the USD 10.50 pre-flight and the USD 12 cap absorbs a few such retries.
  - S6: record the billed image tokens after the first scanned tuning sheet.
  - Confirm the accepted reasoning effort on the first tuning call.
