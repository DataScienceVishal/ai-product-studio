# Review: T-221 slice 1, end-to-end tuning plans, no live ai_cache, clean provider stops, `main --live` tests

Branch `p/sme-council-tender-drafting/T-221` at 7d18e72, against `main` (merge base c6aaf3b; main has not changed this product since then). Reviewer: `reviewer` (opus). No live model calls were made: the Azure env vars were unset for every test run.

**Verdict: CHANGES.** There is one blocking issue: the demo draft items are sent with `word_limit: None`, but every demo pack prints a word limit for these questions (C1). T1 and T2 are the paid calibration and tuning runs for E2, which does pass word limits. With no limit they would measure and tune a different regime (longer drafts, a dearer claim check, and the shorten path never runs). The rest of the slice is sound, and the S1, S3, S4 and S6 fixes are proven by tests that fail on the old code.

## Summary

The diff touches 3 files (+246/-15): `eval/run.py`, `tests/test_tender_eval.py` (20 new tests) and `NEXT.md`.

- T1 and R2 now plan 1 extraction plus 5 drafts. R1 plans 18 items and T2 plans 36 (3 packs x 3 passes x (1 extraction + 3 drafts)). Every draft runs the real claim check.
- A live phase clears the demo tenant's `ai_cache` before every item. Tuning phases turn off `cacheable` for the run.
- `ai_*` AppErrors stop the run cleanly with exit 8.
- Non-tuning phases are refused whenever `not ctx.dry`.

**Tests.** I ran the full backend suite on a fresh `starter_test` database (dropped and recreated), python3.13, Azure env unset, in a clean worktree at 7d18e72: **1376 passed, 1 skipped, 0 failed (379.6 s)**. This matches NEXT.md. My first run in the shared checkout overlapped a brief checkout switch, so I killed it and did not count it.

## The six checks

1. **S1, live served from ai_cache.** PASS for tuning.
   - `run_task` reads `ai_cache` before every call (llm.py:185), whatever `cacheable` says. So the per-item clear at run.py:324 is the fix that matters, and it is in place.
   - Mutation: dropping `live_clear` from that condition fails `test_a_live_phase_never_serves_an_item_from_ai_cache` and `test_live_phase_clears_a_preseeded_cache_before_every_item`.
   - Side effects:
     - Live **T1** now clears the recorded demo cache too. Before this slice only T2 and T3 did. `RESEED_NOTE` is printed and returned as `reseed_required` whenever a clear happened, so the operator is told. The T-219 NEXT.md line "T2 and T3 clear the demo tenant's ai_cache" is now incomplete (S3 below).
     - No clear happens when every item is skipped, which is correct.
     - The per-item clear would break R1 when it is enabled (S1 below).
2. **S4, provider AppErrors.** PASS.
   - `except AppError` (run.py:343) re-raises anything whose code does not start with `ai_`.
   - On `ai_rejected`, `ai_disabled` or `ai_busy` the item is not recorded, `stopped` is set, and `main` returns 8 with "live phase stopped early".
   - The settle row is written by run_task's `except Exception` (llm.py:225) with 0/0 tokens and `failed=True`. That makes `charged_worst` true on a live ledger. `test_a_provider_ai_rejected_stops_the_run_cleanly_and_settles_the_ledger` asserts `["hold","settle"]`, `charged_worst` and `usd > 0`.
   - Mutation: making the `ai_` filter catch every AppError fails `test_other_app_errors_stay_fatal` and `test_only_task_failed_is_recorded_other_app_errors_are_fatal`.
   - Stop messages are the app's fixed strings, so no secrets reach them.
3. **S3, `main --live` tests.** PASS.
   - The tests monkeypatch `LIVE_LEDGER`, `RESULTS_DIR`, `load_budget_config` and `build_live_provider`, and set fake env values.
   - Exit 0: hold rows exist, and they are only written when `dry_run=False` (ledger.py:237). Settles have `usd > 0`, and `live-results/T1.jsonl` holds 6 items.
   - Exit 7 is the wrong model. Exit 8 covers the sub-cap, `AIUnavailable` and `ai_rejected`, with no traceback.
   - With main's `run.py` put back, 19 of the new or changed tests fail, including the exit-0 test and the ai_unavailable/ai_rejected exit-8 test.
   - The exit-7 and sub-cap exit-8 tests also pass on the old code. That is expected: the wiring existed, and these tests now pin it.
   - The `not any(r.get("dry_run"))` assertion is vacuous because ledger rows carry no `dry_run` key. The hold rows are what prove non-dry. This is not blocking.
4. **T1 question source and held-out leakage.** Partly sound. See C1.
   - `retrieval_labels.json` covers only the 3 demo packs (S04, S08, S12, which are `demo` in manifest.json). Only `ref` and `text` are read. `relevant`, `primary` and `why` are not.
   - None of the 30 labelled question texts appears in any held-out key, `trap_set.json`, `dev_trap_set.json`, `fixture_drafts.json`, `seeded_claims.json` or `evidence_map.json` (exact-text check).
   - So nothing held-out enters tuning. The labels are seen data already (they drive the retrieval diagnostic), and tuning on them is within the DESIGN 8.3 demo-pack intent.
   - The file is opened read-only. `sha256sum -c eval/keys/FROZEN.sha256` reports 34/34 OK.
   - `git diff main...7d18e72` is empty for `eval/keys/`, `demo-data/`, `eval/budget.json`, `eval/ledger.jsonl`, `eval/results/` and `app/backend/app/`.
5. **Worst-case $ figures.** Believable, but slightly low.
   - The arithmetic checks out: T1 0.047 + 0.086 + 0.124 = 0.257. Per draft item, about $0.017 for the draft plus $0.025 for the check. That gives T2 about $1.62, R1 $0.79 and T3 about $1.26.
   - `LedgerBudget.worst_usd` prices up to twice the output cap at the output rate. A check hold therefore floors at about $0.024 (12,000 x $2/M), and the dry-run figure of $0.0248 means the check input was only about 400 tokens over that floor.
   - That small input reflects the short ScriptedFakeAI draft. A real unlimited draft can be up to 4,000 tokens (about 16 KB), which adds about $0.004 to $0.005 per check.
   - Corrected roughly: T1 about $0.28 and T2 about $1.75. Both still fit, and T1 + T2 is about $2.03, so T3 is mostly squeezed out at worst case. Fixing C1 shortens drafts and moves the figures back towards the builder's numbers.
   - The caps are enforced at hold time on the real estimate whatever these figures say. So these are planning numbers, not a safety property. The $2.00 tuning cap and the $6.00 total are unchanged.
6. **S6, refusal on `not ctx.dry`.** PASS. `phase not in LIVE_PHASES and (not ctx.dry or name != "fake")` refuses a non-tuning phase with any live ledger, and also with a non-fake provider on a dry ledger. A dry run with the fake is still allowed. `main` never builds a non-dry context for those phases anyway, because it exits 3 earlier. All 6 parametrised refusals fail on the old code. Moving the "ledger rows but no results" test from E1 to T1 loses nothing, because that check does not depend on the phase.

## Critical issues

- **C1: demo drafts are sent with no word limit, but the packs print one (run.py:158-164; NEXT.md "no word limit is passed (the labels hold none)").**
  - What the packs print:
    - `demo-data/pack-sources/S04-cleaning-halls-and-toilets.md:134-145`: 4.1 to 4.3 share 1,000 words in total; 4.4(a) and 4.4(b) are 400 words each.
    - `S08-security-trust-cctv-keyholding.md:173-179`: Q1 and Q2 are 750 words, Q3 is 500, Q4 is 400, and Q5 is 1,000 words across parts (a) and (b).
    - S12 prints limits too.
  - What the code does: the docstring says "the pack prints no word limit in the labels". The labels hold none, but the packs do.
  - Why it matters: T1 is the calibration that replaces DESIGN 8.2 with measured figures, and T2 tunes the prompts for E2. E2 passes the key's `word_limit`. With `None`:
    - drafts can run to the 4,000-token cap;
    - the claim-check input and cost grow (the T-216 note: an unlimited draft's check reserves about 33.7k);
    - `SHORTEN_SPEC` and `fit_to_limit` never run in tuning;
    - word-limit adherence cannot be judged.
  - The cost: about $0.26 to $1.6 of the $2.00 tuning cap, spent on a regime that is not the one scored.
  - Fix (cheap, no frozen file touched): add a small committed, non-frozen `eval/demo_questions.json` (or a `{pack: {ref: word_limit}}` map). Copy the limits from the pack-source tables. For S04 4.1 to 4.3, split the shared 1,000 words evenly over the four questions (250 each), or choose the first 5 refs with their own limits; write down which rule you used. Add a test that parses each pack-source table and checks every limit, so nothing is invented. Update the docstring and NEXT.md, and re-measure the worst-case figures.

## Suggestions (not blocking)

- **S1: the per-item clear will destroy R1's recording (fix before R1 goes live).**
  - Problem: DESIGN 8.3 says R1 "feeds the offline demo and the demo tenant's cache". With `live_clear` true for every live phase, R1 (cacheable, not tuning) would write each item's answers and then delete them before the next item, leaving only the last item cached.
  - Fix: for the recording group, clear once at phase start (R2 still clears per item, for the stopwatch). Add a test that a live R1 leaves every item's cache rows behind.
- **S2: there is no test for "tuning phases write nothing back".** Mutation: removing `ctx.provider.cacheable = False` (run.py:304) leaves all 178 tests in the module passing. Today the per-item clear hides the gap, except for the rows the last item writes. Assert that `ai_cache` is empty after a live tuning phase whose drafts actually call the model.
- **S3: the live draft and claim-check paths are not exercised in tests.** The `ctx` fixture and the `main --live` tests use `retrieve=[]`, so every draft takes the gap path (no model call, no check call). The 6 "items" in the live tests are 1 real extraction plus 5 free gap drafts. Add one live-path test where retrieval returns hits, so the draft and check holds and settles go through `LiveFake`.
- **S4: NEXT.md.** The T-219 section still says only T2 and T3 clear `ai_cache`; live T1 does too now. Add the corrected worst-case figures after C1.
- **S5: a stop inside the check re-pays the draft on resume.** An `ai_*` stop raised by the claim check after the draft succeeded drops the whole item, so a resume pays for the draft again. This is a small amount, but note it.
- **S6: the old S2 (wrong-model pricing and the reported model on AIUnavailable) is still open.** It was deferred, as agreed. It must be fixed before the scored phases.

## Evidence

- `git diff main...7d18e72`, read in full. I also read the context in `app/tender/llm.py` (`_cache_get`, `run_task` 156-240), `eval/ledger.py` (`worst_usd`, `hold`, `settle` 220-265), `app/tender/draft.py` (caps, `draft_answer`), `app/tender/claimcheck.py` (`check_payload`, `check_draft`), DESIGN.md 8.3, `demo-data/packs/manifest.json` and `demo-data/pack-sources/S04, S08, S12`.
- Suite: `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""`, with the Azure vars unset. Result: `1376 passed, 1 skipped in 379.58s`.
- Mutations were run on a throwaway worktree in the scratchpad, against database `starter_mut`. No product code was edited.
  - Main's `run.py`: 19 failed.
  - No live clear: 2 failed.
  - No `cacheable=False`: 0 failed (S2).
  - `ai_` filter removed: 2 failed.
