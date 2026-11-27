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

---

## Re-review (cac2ab5)

Diff reviewed: `git diff a9b7f6d..cac2ab5` (ledger.py, run.py, score.py, seed.py, EVAL.md, tests). Nothing taken from the builder's report on trust.

### Verdict: PASS

### Tests (run by the reviewer on this exact tree, fresh database `t193rr_31246`, local Postgres)

- `tests/test_tender_eval.py`: **72 passed** in 6.5 s.
- Full backend suite (`python -m pytest -q -o addopts=""` from `app/backend`): **1048 passed, 1 skipped** in 220 s.
- Note: the container's `python` is 3.11 with no pytest installed. The tests ran under `python3.13`, which has the dev requirements. This is an environment detail, not a code issue.

### Must-fix status

| # | Status | Evidence |
|---|---|---|
| M1 preflight blocks E2 to E4 | Fixed | `eval/ledger.py:261` now needs only the worst case of this phase plus the later scored phases, less what this phase has already spent (capped at its own worst case). Before E1 that is still $2.54. Tested: E1 resume passes, E2 passes after $0.25, and E3 is refused when only $0.75 is left against $0.92 (`tests/test_tender_eval.py:169-178`). |
| M2 results gitignored | Fixed | `results/*.jsonl` removed from `eval/.gitignore`. Dry results go to `results/dry/` (still ignored). `run.py:240` refuses a live phase that has ledger rows but no results file. `run.py:244` touches the file so an empty finished phase is distinguishable. Tested (`:678`). |
| M3 A4 splitter | Fixed | `score.py:22` imports the app's `split_sentences` and `_GAP`/`_CITE`. Judgement call (b) is discussed below. |
| M4 A7 word count | Fixed | `count_words` is imported from `app.tender.draft` (`score.py:22`), so the scorer can't drift from the app. |
| M5 A6a overlap | Fixed | `score.py:179` works on word tokens. Judgement call (a) is discussed below. |
| M6 durable holds | Fixed | `ledger.py:182` `reserve()`. Judgement call (d) is discussed below. Tested: `:180-200` (a fresh Ledger sees the unsettled hold at its worst case, and a second "process" is refused on the cap). |
| M7 drafts without a claim check | Fixed | `run.py:234` refuses E2, E3, E4 and T3 before the plan's first item if there is no claimcheck callable. Tested (`:695`). |

### Judgement calls

**(a) M5 same-sentence arm.** I probed it directly.
- A whole-paragraph checker span (4 sentences) against a 7-token seeded span: **miss**. A span that crosses sentences can never be contained in one app sentence, and the 30% share rule fails.
- Exact span: hit. A tiny span ("ISO"): miss, because cover is below 50%.
- A checker span that is a single long sentence of about 35 tokens containing the seed: hit. This is the intended arm and is acceptable, because the checker flagged exactly the sentence that holds the fabrication.
- Residual: a short 2-sentence paragraph can still hit through the 30% share rule when the seeded span is at least 30% of it. That is a deliberate tolerance, not a loophole.
- The arm is only active when `draft_texts` is passed. Without it the rule is stricter, so there is no risk of over-matching.

**(b) M3: a gap-marker sentence with no [E-n] is not a claim** (`score.py:116-127`).
- It is defensible for a sentence that is mostly the marker.
- But I confirmed that a mixed sentence such as "We have delivered 40 contracts for 12 councils since 2015 and hold [NEEDS FIRM INPUT: insurer] cover." is dropped from A4 entirely, uncited factual claim and all.
- A trailing marker after the full stop is safe: the app splitter makes it its own sentence, so the preceding claim is still scored.
- It is pre-registered in EVAL.md, so it is not a correctness bug, and A6/claim check still sees the sentence. See should-fix R1.

**(c) M2: the refusal is correct.**
- The check runs after the plan is built and the preflight passes, but before the file is touched (`run.py:240-244`).
- `reserve()` raises before writing a row on refusal, so a refused first call leaves no ledger row and no false refusal.
- A stale but present results file (an older commit) re-runs only the unrecorded items. That spend is still bounded by the caps.

**(d) M6: flock check-and-append is correct.**
- `reserve()` opens `a+`, takes `LOCK_EX`, reads all rows, checks both the group cap and the total cap, then appends the hold and fsyncs, all under the one lock (`ledger.py:182-208`).
- `append()` takes the same flock. Both paths take the thread lock before the flock, so the lock order is consistent.
- flock is per open file description, so two Ledger instances in one process also serialise.
- `_spent_in` (`ledger.py:154`) counts a `hold` row whose `hold_id` has no settle row at its `worst_usd`. Settled holds count their real tokens. A failed zero-token call settles at `ceil(worst)` (`:245`).
- Fake rows are dropped only in a dry ledger (`:163`).

**ledger.py imports nothing from `app`.** Verified. Imports are stdlib only (`fcntl, json, math, os, re, threading, uuid, dataclasses, pathlib`; `ledger.py:17-27`). `score.py` now imports `app.tender.draft`. That is intended (M3 and M4) and does not touch spend.

### Should-fix status

- **Fixed and verified:** 1 (`CHECK_CAP` imported, `run.py:200`), 2 (model and caps pinned, prices and caps validated, `ledger.py:44`, `:99-121`), 3 (`math.ceil`, `:245`), 4 (`:163`), 5 (`run.py:259-264`; truncation surfaces as `TaskFailed("ai_truncated")` per `app/tender/llm.py:216-217`, so it is recorded; a plain `AIUnavailable` stops the phase), 6 (`run.py:82`), 7 (`run.py:97`), 8 (`clear_ai_cache` before each T2, T3 and R2 item, `run.py:253`), 9 (empty manifest, login check, non-JSON body, duplicate packs, path containment, all in `seed.py`), 10 (`score.py:84`), 12 (`false_flags`, `score.py:216`), 13 (test rewritten).
- **Skipped:** 11 (optional). Accepted.
- **Security notes from the first review**, both addressed: the path containment check (`seed.py`), and the non-local `DATABASE_URL` refusal behind `--allow-remote-db` (`run.py:284`, exit 5).

### Remaining suggestions (non-blocking, do before the EVAL.md freeze)

- **R1 (A4 gap-sentence exemption).** Report the number of exempted gap sentences, and their share of all sentences, next to A4. Or exempt only sentences whose text, minus the marker, is short (for example 6 tokens or fewer). Otherwise a draft that puts gap markers inside factual sentences hides uncited claims from A4. Cheap to change now; it becomes an amendment after the freeze.
- **R2 (cache clear wipes the demo's recorded cache).** `clear_ai_cache` deletes every `ai_cache` row for the demo tenant, including the rows `seed.py` loaded from recordings. Add a note in NEXT.md or EVAL.md to re-run `python -m eval.seed` after T2, T3 or R2 before any demo.
- **R3 (lock-free reads).** `Ledger.rows()` (`ledger.py:148`) reads without the flock, so `spent()` or `_phase_rows` could see a half-written line from a concurrent writer and raise `JSONDecodeError`. Take `LOCK_SH` in `rows()`, or skip a trailing line that doesn't parse. Low risk, since runs are single-process.
- **R4 (non-AI errors recorded as model failures).** `except AppError` (`run.py:262`) also records non-AI `AppError`s (for example a tenant or DB lookup error) as item failures that count against the bar. Narrow it to `TaskFailed`.
