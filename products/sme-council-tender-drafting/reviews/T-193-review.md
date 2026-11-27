# Review: T-193 (S9 eval harness and demo seed, no live calls)

- Branch: `p/sme-council-tender-drafting/T-193` at `8e7ab5b`, diff against `origin/main` (11 files, +1,416).
- Reviewer: reviewer agent, 2026-11-27.
- Read against: SPEC.md section 6 (A1 to A8), DESIGN.md sections 8 and 9, Q-19 (answered A) in `state/QUESTIONS.md`, `playbooks/engineering.md`.

## Verdict: CHANGES

The ledger arithmetic is right. The no-live-call and no-`ai_usage` guarantees hold. The Q-19 gate fails closed. The fixed-seed sampler is deterministic. But the harness as written cannot complete the one scored run: the preflight blocks E2 to E4, and results are gitignored, so a resume from a fresh clone re-runs scored items. Also, three scorers disagree with the app or with SPEC in ways that would misstate A4, A6a and A7. All of this has to be fixed before the pre-registration freeze, so it should be fixed in this slice.

## Tests (run by the reviewer on the branch tree)

Python 3.12.3 venv, local Postgres, `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/rev193_test`, `-o addopts=""`:

- Full backend suite: **1022 passed, 1 skipped** (`test_spa.py:152`, frontend not built), 1 warning, 257 s.
- `tests/test_tender_eval.py`: **46 passed**.

## What is verified correct

- **No live path.** `run.py main` builds only `ScriptedFakeAI`. `--live` exits 3 (`run.py:235-237`, tested). No Azure provider is constructed. `ScriptedFakeAI.cacheable = False`, so dry runs don't put fake answers into `ai_cache` under the live keys.
- **Never writes `ai_usage`.** `ledger.py` imports nothing from `app`. `test_ledger_budget_never_writes_ai_usage_or_calls_reserve` asserts a count of 0.
- **The Q-19 gate fails closed.** `load_budget_config` refuses a missing `approved_by` or answer, a missing QUESTIONS.md, or a header answered with another option (tested with "answered B"). `Q-190` cannot match `Q-19` (the regex needs `\s*\(` after the id). The real header at `state/QUESTIONS.md:158` matches.
- **The worst case never under-prices a single call.** `estimate_tokens` is input *bytes* plus the cap (bytes bound tokens). `worst_usd` prices `min(est, 2*cap)` as output and the rest as input:
  - First call: worst minus true worst is at least `cap*(p_out - p_in)`, which is above 0.
  - Doubled retry: the two are equal.
  - Holds are re-taken per retry inside `run_task`, so each attempt is pre-checked.
- **Failed calls are charged.** A failed call with 0 tokens reported is charged its worst case. A failure that reports tokens is charged those tokens.
- **Wrong model.** A model other than `gpt-5-mini*` is recorded at the approved price, then raises `ModelMismatch`. Nothing in `run_phase` or `main` catches it, so the run stops.
- **Caps and headroom.** The sub-caps are checked with the total cap. Headroom other than 0 is refused.
- **`sample.py`.** The draw is seeded (20261127) and sorts by id before sampling, so it doesn't depend on export order. With fewer than 100 claims it returns all of them. Tested.
- **`seed.py` with no packs.** `find_packs` runs before sign-up in `main` and first in `seed()`, so the run fails cleanly and nothing is written (tested with row counts).

## Must-fix

**M1. The scored preflight runs before every scored phase and every resume, so E2 to E4 can never run** (`eval/run.py:195-196`, `eval/ledger.py:202-209`).
- What happens: `preflight_scored` always demands $2.54 free in the scored group.
- Reproduced: after one E1 extraction call costing $0.25, the E2 preflight refuses: "scored reserve $2.35 is below the scored worst case $2.54".
- The same happens when E1 is resumed after an infrastructure failure, which breaks the T-56 resume rule in DESIGN 8.1.
- DESIGN 8.5 says the check is "before E1".
- Fix: run it only when nothing has been spent in the scored group, or require the remaining reserve to cover the summed `Phase.worst_usd` of the unfinished scored phases. Add a test with a live ledger: E1 spends something, then E2's preflight passes.

**M2. Results are gitignored, so a resume from a fresh clone re-runs finished scored items** (`eval/.gitignore:3`, `results/*.jsonl`).
- Every studio run starts from a fresh clone (CLAUDE.md section 2), and DESIGN 8.5 says "the ledger and results are committed after every phase".
- With results ignored, the resume set in `run_phase` (`run.py:200`) is empty on the next run. Finished items run again and are paid for again. That breaks "one scored run" and could double-count items.
- Fix: commit `results/<phase>.jsonl` and keep only `results/dry/` ignored. Optionally, refuse a live phase when the ledger has rows for that phase but the results file is missing.

**M3. The A4 claim splitter doesn't match the app's, and it fails correct drafts** (`eval/score.py:108-119`).
- `app/tender/draft.py split_sentences` keeps a citation that follows the full stop with its sentence and keeps a `[NEEDS FIRM INPUT: ...]` marker whole. The scorer does neither.
- Reproduced on `We cleaned 40 schools. [E-3] We will deliver - on time [E-3]. We hold [NEEDS FIRM INPUT: ISO 14001 cert. Provide copy]` (every citation valid): A4 is **0.25**.
  - "We cleaned 40 schools." scores as uncited.
  - The gap marker splits into two "claims", both uncited.
- Separately, a sentence that has a gap marker in it ("We hold [NEEDS FIRM INPUT: ...]") counts as an uncited claim. So the honest-gap behaviour that A8 rewards lowers A4.
- Fix: score with the app's `split_sentences`, imported or copied, with a parity test. Exclude sentences whose only unsupported content is a gap marker. Write the claim definition into EVAL.md's A4 row.

**M4. The A7 word count doesn't match the app's** (`eval/score.py:112-114` against `app/tender/draft.py:74-76`).
- The app counts only tokens that contain a letter or digit. The scorer counts every whitespace token, so stray `-`, `–` and `.` tokens are counted. On the example above: scorer 21 words, app 19.
- A7 needs 100%, so one draft that `fit_to_limit` left exactly at the limit can fail the bar.
- Fix: use the app's `count_words`, with a parity test on punctuation-only tokens and cite-then-period text.

**M5. The A6a overlap is a raw character substring in either direction, which is easy to over-match on A6a, the headline bar** (`eval/score.py:158-160`).
- Reproduced: a checker span of `"in"` marked unsupported "catches" the seeded claim "We cleaned 400 schools in 2019". One checker claim spanning the whole draft catches every seeded claim in that draft (2 of 2).
- A checker that flags broadly would score 40/40.
- Fix: compare word tokens on word boundaries. Require the checker span to cover at least about 50% of the seeded span's tokens, and the seeded span to be at least about 30% of the checker span, or that the two sit in the same app sentence. Pre-register the rule in EVAL.md.
- Add tests for a tiny span and a whole-paragraph span (both must miss), and ideally a mutant for them.

**M6. Holds exist only in memory, so a killed process can let spend pass the cap** (`eval/ledger.py:173-199`).
- A hold is never written to the ledger. If the process dies during `provider.complete`, nothing is recorded but the call may have been billed:
  - SIGTERM or SIGKILL, a cut-off cloud run (CLAUDE.md section 2), or KeyboardInterrupt;
  - `run_task` catches only `Exception` (`app/tender/llm.py:219`).
- The next run's `spent()` then under-counts, and a later call can pass the sub-cap or the total cap. That breaks DESIGN 8.5 ("a reset after the request was sent is charged at the worst case").
- The checks also ignore holds that are still open. That is safe only while everything is sequential in one process.
- Fix: before the call, append a `hold` row with its worst-case dollars. `spent()` counts an unsettled hold at worst until a matching `settle` row (with the hold id) replaces it. Take the check and the append under one lock: a file lock (`fcntl.flock`) on the ledger, not the per-instance `threading.Lock`.
- Test: a hold with no settle, then a new `Ledger` on the same file shows the worst case as spent.

**M7. E2 and E3 record drafts with no claim check as finished items** (`eval/run.py:171-172`).
- With `ctx.claimcheck is None`, `_draft` writes a result with no `claims`, and `run_phase` marks the item done. Once T-190 is wired in, the resume skips those items, so the scored run's A5, A6c and A8 inputs never get checked, and the drafting money is already spent.
- NEXT.md says this behaviour is intended ("E2/E3 draft but record no claims"). It shouldn't be.
- Fix: for phases whose plan needs a check (E2, E3, T3 and the end-to-end ones once drafting is added), raise `PhaseNotReady` before the first item when `claimcheck` is None, as `_check` already does for E4.

## Should-fix

1. **The claimcheck cap is hard-coded** (`eval/run.py:179`). The LedgerBudget for claimcheck uses a literal 6000. If T-190's spec cap is larger, `worst_usd` prices the excess output at the input price and under-reserves. Take it from the claimcheck `TaskSpec.max_output_tokens`.
2. **`budget.json` isn't tied to the approved values** (`eval/ledger.py:87-105`). Pin `model == "gpt-5-mini"` and the approved caps (6.00, 2.00, 2.60, 1.40) in code, or check them against the Q-19 text. Also validate each group cap and price as finite and above 0:
   - a `NaN` group cap makes `spent + worst > NaN` False, so the sub-cap is never enforced;
   - a price of 0 makes every call free.
3. **Worst-case rounding** (`eval/ledger.py:188`). Converting the worst case back to tokens uses `round`, which can under-charge by half a token. Use `math.ceil`.
4. **Fake-model rows in a live ledger** (`eval/ledger.py:130`). `spent()` drops `model == "fake"` rows even in a live ledger. Drop them only when `dry_run` is set, so a stray fake row in a live ledger can't hide spend.
5. **Item failures abort the phase** (`eval/run.py:207-211`). A non-budget exception on one item (`TaskFailed` for invalid or truncated output) stops the whole phase uncaught, and the resume retries the same item. Record failed items as results with their error code, since they count against the bar, and carry on. Let infrastructure errors (`AIUnavailable` without a truncation) stop the phase for a resume.
6. **Provider headroom.** Assert `provider.output_headroom == cfg.headroom` when the Context is built, so a live provider with headroom above 0 can't make `worst_usd` (which assumes output of at most twice the cap) under-reserve.
7. **The held-out drafting rule** (`eval/run.py:127`). The SPEC rule (first held-out pack of each sector) depends only on manifest order. Name the 3 drafting packs explicitly in `manifest.json` (for example `"drafting_heldout"`) and check that it has 3 entries.
8. **Cache effects on tuning and A9.** A live provider is cacheable, so T2 passes 2 and 3 hit the demo tenant's `ai_cache` and repeat pass 1 at 0 tokens. R2 says "cache cleared", but nothing clears it. Handle both before L1: per-pass nonce in the payload, or a cache-bypass flag for the harness, plus a cache clear for R2.
9. **`seed.py` details.**
   - `:47-54`: a `manifest.json` with no `demo` key, or an empty one, seeds 0 packs without complaint. Refuse it.
   - `:125`: the login after a 409 isn't checked, so a wrong password ends in a confusing upload error. Also, `r.json()` on a non-JSON error body raises.
   - `:94`: re-seeding creates duplicate packs. Skip a pack whose title already exists.
10. **A3 matching** (`eval/score.py:76`). Key mandatory items are matched against *all* extracted items by ref first. A question and a mandatory item that share a ref like "1.2" would pair up and count as "shown optional", which fails A3 outright. Match refs only against non-question items, or require text similarity with a ref match.
11. **A1 ref-only matching** (`eval/score.py:34-41`). A shifted ref (the text of Q4 labelled Q3) counts as a hit. The design does pre-register ref-first matching, so this is optional, but consider a minimum text similarity (for example 0.5) on ref matches.
12. **A6a false positives.** SPEC doesn't require it, but report the checker's flag rate on the non-seeded claims in E4 next to A6a, so a checker that flags everything is visible.
13. **An unreadable test** (`tests/test_tender_eval.py:485-491`). It writes the ledger file as a side effect inside a conditional expression. Split it into plain statements.

## Security

- No secrets. The seed password comes from the environment only.
- No new endpoints.
- `seed.py` reads manifest names as paths under `packs_dir` without a containment check. It is a local operator tool, so the risk is low, but a `resolve().is_relative_to(packs_dir)` check is cheap.
- `run.py` connects to whatever `DATABASE_URL` says, despite the comment "local database only". Consider refusing a non-localhost host unless a flag is passed.

## AI cost

None in this slice. All calls go to `ScriptedFakeAI` and the dry ledger. The ledger design keeps a live run inside Q-19 A once M1, M2 and M6 are fixed.
