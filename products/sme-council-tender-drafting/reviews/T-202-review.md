# T-202 review: T-193 follow-ups (R1-R4, real claimcheck wiring, should-fix 11)

Branch `p/sme-council-tender-drafting/T-202` at 93dc439, diff `git diff origin/main...HEAD` (6 files, +242/-50).
Reviewer: reviewer agent, 2026-11-27.

## Verdict: CHANGES

One must-fix: the new A4 gap-sentence exemption still lets short, uncited factual claims through. Everything else is correct and tested.

## Tests (run on this exact tree, python3.13, fresh Postgres db `r202`)

- `tests/test_tender_eval.py`: **84 passed** in 7.35s
- Full suite from `app/backend`: **1109 passed, 1 skipped** in 234.89s (main after T-193 had 1097 passed, 1 skipped)

## Checklist

| Point | Result | Evidence |
|---|---|---|
| Default claimcheck uses LedgerBudget with the real CHECK_CAP | OK | `eval/run.py:85-87` defaults `claimcheck` to `default_claimcheck(ctx)`; `_check` at `eval/run.py:220` builds `LedgerBudget(..., "claimcheck", CHECK_CAP)` from `app.tender.draft.CHECK_CAP`. The test `test_default_claimcheck_calls_the_model_through_the_ledger` checks that `run_task` receives a budget with `output_cap == CHECK_CAP`. |
| No live call possible; `--live` refused | OK | `main` (`eval/run.py:316-350`) returns 3 on `--live` before it builds anything, and otherwise only builds `ScriptedFakeAI` with a dry ledger. The default claimcheck uses `ctx.provider`, so it can't reach a provider the harness wasn't given. Covered by the test at `test_tender_eval.py:774`. |
| `eval/ledger.py` imports nothing from `app` | OK | Imports are stdlib only (`eval/ledger.py:17-27`). The AST test is at `test_tender_eval.py:241`. |
| R3 `rows()` under `LOCK_SH` | OK | `eval/ledger.py:151-156`. The thread lock is not re-entered: `reserve` reads the file inline and never calls `rows()`. Tested by `test_reading_rows_takes_the_shared_file_lock`. |
| R4 catch narrowed to `TaskFailed` | OK | `eval/run.py:282`. Other `AppError`s propagate, and the earlier `TaskFailed` row is still on disk. Tested by `test_only_task_failed_is_recorded_other_app_errors_are_fatal`. |
| M7 test rewrite: PhaseNotReady | OK by design | The `NEEDS_CLAIMCHECK` guard was removed because every `Context` now has a claimcheck, so E2, E3, E4 and T3 can no longer record a draft without claims. PhaseNotReady still fires for missing keys and inputs (`test_phase_without_inputs_says_what_is_missing`) and on a headroom mismatch (`eval/run.py:88-90`). `test_e2_drafts_and_records_claims_end_to_end_with_the_real_claimcheck` proves that E2 records `claims`. See suggestion S2. |
| A1 fixture "Safeguarding" changed to "Provide your safeguarding arrangements" | Not weakened | Against the key text "Provide your safeguarding arrangements for vulnerable service users", the new text scores 0.724 and the old one 0.304. 0.724 is below the 0.8 text threshold, so the item is still matched by ref only, as the comment says, and still exercises the ref path. The old text now falls under `REF_SIM_MIN`, which is exactly the behaviour should-fix 11 introduces. |
| A1 ref floor 0.5 pre-registered | OK | `EVAL.md:20` and `eval/score.py:25,48`. Tested by `test_a1_ref_match_needs_minimum_text_similarity`. |
| R2 reseed note | OK | `eval/run.py` sets `reseed_required` and writes it to stderr only when a cache clear actually ran. Tested. |

## Critical issues (must fix)

### M1. The A4 gap exemption ("no digit, at most 3 non-connective words") still hides uncited factual claims

`eval/score.py:123` (`RESIDUAL_MAX_WORDS = 3`) and `eval/score.py:132-138` (`carries_other_content`). Rule text: `EVAL.md:22`.

I probed `score.claims_of` on this tree. A result of `[]` means the sentence is exempt and A4 never scores it:

| Sentence (no `[E-n]`) | Residual | Exempt? |
|---|---|---|
| We hold ISO 9001 [NEEDS FIRM INPUT: cert]. | hold iso 9001 | no, the digit catches it (good) |
| Our team cleaned schools [NEEDS FIRM INPUT: names]. | team cleaned schools | **yes** |
| We are ISO certified [NEEDS FIRM INPUT: cert]. | iso certified | **yes** |
| We have zero RIDDOR incidents [NEEDS FIRM INPUT: x]. | zero riddor incidents | **yes** |
| We clean forty schools [NEEDS FIRM INPUT: x]. | clean forty schools | **yes** (a number written as a word escapes the digit rule) |
| We hold Cyber Essentials [NEEDS FIRM INPUT: x]. | hold cyber essentials | **yes** |
| We have never had a breach [NEEDS FIRM INPUT: dates]. | never breach | **yes** |
| We won the council award [NEEDS FIRM INPUT: year]. | won council award | **yes** |

**Why it matters.** R1 was meant to close exactly this loophole. A draft can assert a certification, a safety record or a contract count with no evidence, as long as it hangs a gap marker on the sentence and keeps it short. Those are the most damaging claims a tender can make (pass/fail items such as ISO, Cyber Essentials, RIDDOR and DBS), and A4 would report them as "the draft said it does not know". This rule is pre-registered in EVAL.md and is about to be frozen. Fixing it after the freeze needs a dated amendment, so now is the cheap moment.

**Fix** (any combination that makes all the rows above count as claims, except the stubs):
1. Reuse the app's own fact detector. If `app.tender.claimcheck.fact_triggers` fires on the gap sentence once the marker is blanked, keep the sentence as a claim. That detector covers caps runs ("Cyber Essentials"), codes ("RIDDOR", "ISO 9001"), £ and %. It also keeps A4 consistent with the rule the app uses to decide whether a sentence needs checking.
2. Treat number words (zero to twenty, thirty to ninety, hundred, thousand, million) like digits.
3. Tighten the residual. Either allow at most 1 content word, or require every residual word to come from a short fixed stub list (hold, held, have, provide, cover, insurance, policy, certificate, details, number, name, ...). With the list, "We hold [gap]" and "Our insurance cover is [gap]" stay exempt, and "team cleaned schools" and "never breach" do not.
4. Add the rows above as parametrized tests in `test_tender_eval.py`, beside `test_a4_gap_sentence_with_other_factual_content_still_counts`.
5. The current test asserts `claims_of("We hold ISO [NEEDS FIRM INPUT: x].") == []`. Fix 1 would flip that result, so decide which outcome you want and record it in EVAL.md.

## Suggestions (should-fix, non-blocking)

- **S1.** Add the exempt gap sentences (`gap_exempt_sentences`) to the A5 human-sample population (`eval/sample.py`), so whatever slips past the rule is still checked by a person. This is cheap, and it backs up M1 whatever threshold you choose.
- **S2.** `test_check_phase_needs_a_claimcheck` (`test_tender_eval.py:636`) no longer tests what its name says. Rename it (for example `test_e4_uses_a_passed_claimcheck`). Also consider a guard in `_check`: if `ctx.claimcheck` is set to `None` after construction, raise `PhaseNotReady` instead of `TypeError`. As it stands, an item fails mid-phase with an unclear error.
- **S3.** `default_claimcheck` closes over the `Context` it was built for. `dataclasses.replace(ctx, provider=other)` copies that closure, so the new context's claimcheck still uses the old context's provider, sessions and tenant. Today this fails safe, because it keeps the fake provider. At L1 it could send claimchecks to the wrong tenant or provider. Fix: rebuild the claimcheck in `__post_init__` whenever the existing one is a `default_claimcheck` closure, or pass `ctx` into the callable when it runs.
- **S4.** `EVAL.md:22` is missing a full stop: "...so the reader can see what was excluded A claim passes...".
- **S5.** The A1 ref floor of 0.5 means a correct but truncated extraction (for example a bare heading such as "Safeguarding" for a long question) now counts as a recall miss. That is defensible and pre-registered. Mention it in the A1 notes so the reader doesn't take it for an extractor regression.

## Security and cost

No new endpoints. The default claimcheck reads passages through `cc.live_passages(db, ctx.tenant_id, ...)`, which is scoped to the tenant and skips deleted items, and it rolls back. Every claimcheck call is held against the LedgerBudget at CHECK_CAP (twice the cap if the truncation retry runs). There is no live spend path: `--live` returns 3.

## Re-review (2cacae2)

**Verdict: CHANGES**

Scope: `git show 2cacae2` (`eval/score.py` `carries_other_content`, the A4 row in `EVAL.md`, and the new parametrized test). `tests/test_tender_eval.py`: **92 passed** in 10.75s (python3.13, db `m5bb5`). I did not run the full suite. The caller is running it.

### M1 examples, probed with `score.claims_of` on this tree

| Sentence | Residual | Now |
|---|---|---|
| Our team cleaned schools [gap]. | team cleaned schools | claim (OK) |
| We are ISO certified [gap]. | iso certified | claim, acronym (OK) |
| We have zero RIDDOR incidents [gap]. | zero riddor incidents | claim (OK) |
| We clean forty schools [gap]. | clean forty schools | claim, number word (OK) |
| We hold Cyber Essentials [gap]. | hold cyber essentials | claim, caps run (OK) |
| We won the council award [gap]. | won council award | claim, 3 words (OK) |
| **We have never had a breach [NEEDS FIRM INPUT: dates].** | never breach | **still exempt** |

The last row was in the M1 table, but it is not in the new parametrized test, and it still passes A4 as "the draft does not know".

### The stubs are still exempt (OK)

"We hold [gap]", "Our insurance cover is [gap]", "We [gap]", "Insurance [gap]" and a bare "[NEEDS FIRM INPUT: ISO 9001 cert, provide copy]" are all exempt. The acronym and fact-trigger checks run on the sentence with the marker blanked, so text inside the marker never counts.

### EVAL.md matches the code (OK)

The A4 row describes all five triggers (digit, number word, acronym, `fact_triggers`, more than 2 content words), and the earlier missing full stop is fixed. One small gap: the row doesn't say that `no` and `not` are on the connective list. That matters for the finding below.

### More phrasings that still get through (negation)

| Sentence | Residual | Exempt? |
|---|---|---|
| We have had no incidents [gap]. | incidents | yes |
| We have had no reportable incidents [gap]. | reportable incidents | yes |
| There were no breaches [gap]. | breaches | yes |
| We have no complaints [gap]. | complaints | yes |
| We do not subcontract [gap]. | do subcontract | yes |

`no` and `not` are in `CONNECTIVES` (`eval/score.py:119-120`), so they are stripped before any check runs. `never` is not on the list, but "never breach" is only 2 words. A clean safety record stated as a negation is the same claim as "zero RIDDOR incidents", which the fix now catches. Meanwhile `zero` and `none` are number words. So the rule catches "We have had none [gap]" and misses "We have had no incidents [gap]". That is inconsistent, and it is the same class of claim M1 was about (safety record).

**Fix (small):** treat negations as figures. Drop `no` and `not` from `CONNECTIVES`, and add `no`, `not`, `never` and `nil` to a negation set checked like `NUMBER_WORDS`. Add "We have never had a breach [gap]." and "We have had no incidents [gap]." to `test_a4_short_uncited_claims_with_gap_marker_still_count`. Re-assert that "We hold [gap]" and "Our insurance cover is [gap]" stay exempt. Then add "a negation (no, not, never, nil)" to the trigger list in the EVAL.md A4 row.

### Accepted residual risk (not blocking)

Two-word positive claims such as "We are accredited [gap]", "Staff are vetted [gap]", "We guarantee compliance [gap]", "We are award-winning [gap]" and "certified to iso [gap]" (lowercase) are still exempt. That follows from the 2-word threshold and is a fair trade-off against keeping stubs exempt. S1 (put the exempt sentences in the A5 human sample) is now the backstop for these, so I'd do it before the freeze.
