# T-203 review: A4 gap-exemption hardening and T-202 should-fix S1-S4

Branch `p/sme-council-tender-drafting/T-203` at 7c97290, diff `git diff origin/main...HEAD` (6 files, +123/-13).
Reviewer: reviewer agent, 2026-11-27. I reviewed it in a separate git worktree, not the main checkout.

## Verdict: CHANGES

One must-fix, and it is about pre-registration, not the A4 code. The A4 hardening is correct, stricter by construction and well tested. But putting gap rows into the A5 sample changes A5 and A6c in a way EVAL.md doesn't define. The Amendments line also says the change "can only lower A4", which doesn't describe what it does to A5.

## Tests (run on this exact tree, python3.13 venv, fresh Postgres db `t203r`)

- `tests/test_tender_eval.py`: **113 passed** in 14.73s (T-202 final: 96). I did not run the full suite. No `app/` code changed.

## What I checked

| Area | Result | Evidence |
|---|---|---|
| Strictness (A4 can only get stricter) | Holds | `carries_other_content` (`eval/score.py:162-165`) only gains new `or` terms. No existing term, `CONNECTIVES` entry or `RESIDUAL_MAX_WORDS` changed. I fuzzed 20,000 random gap sentences (stubs, claim words, codes, negations, acronyms, hyphens) against `origin/main`'s `score.py`. Sentences exempt now but scored before: **0**. |
| "We are incident-free [gap]" | Now a claim | It is caught twice, by `_HYPHEN` and by `free` (from `_norm` splitting the hyphen). |
| Letter+digit codes | Now claims | "Section S1 [gap]" and "We meet H2 [gap]" are claims. The digit check already caught them, so `_CODE` is a belt-and-braces check, as the comment says. |
| cannot / n't | Now claims | "We cannot", "We haven't" and "We didn't" (curly apostrophe) are claims. "We can't" is a claim too. |
| Stubs still exempt | OK | "We hold [gap]", "Our insurance cover is [gap]", "We will provide [gap]", "Our team is [gap]" |
| Mutation tests | Real | `test_a4_each_new_trigger_matters_mutation_style` blanks each of `CLAIM_WORDS`, `_NEG_RAW` and `_HYPHEN` one at a time on a sentence that only that trigger catches, then checks the sentence becomes exempt. I checked by hand: "incident-proof" has no claim word, and "cannot" is not in `NEGATIONS`, so each case depends on one trigger only. `_CODE` can't be pinned this way because of the digit check, and the test says so. |
| EVAL.md A4 row vs code | Consistent | It lists codes, number words, negations plus cannot/n't, `CLAIM_WORDS`, hyphen compounds, acronyms, fact_triggers and the 2-word residual. That matches `eval/score.py`. EVAL.md is still TEMPLATE (no freeze hash), so this is a legitimate pre-freeze amendment, and it is dated. |
| S1 gap rows in the A5 population | Code OK, rule incomplete | See M1. |
| S2 | OK | The test is renamed. `_check` raises `PhaseNotReady` when `ctx.claimcheck is None`, and a test covers it. Building `LedgerBudget` first has no side effects, because holds happen only in `hold()`. |
| S3 | OK | `__post_init__` rebuilds the claimcheck when it is tagged `is_default_claimcheck`. A callable you pass in yourself is kept. |
| S4 | OK | `EVAL.md:22` "...excluded. A claim passes..." |
| Security and cost | No change | No endpoints and no live path. `--live` is still refused. |

## Critical issues (must fix)

### M1. How gap rows count in A5 isn't pre-registered, and they shrink SPEC's 100-claim A5 sample

Files: `eval/sample.py:25-33` (`sample_claims` with `gap_exempt`), the A5 row at `EVAL.md:23`, and the Amendments line at `EVAL.md:37`.

SPEC A5 (`SPEC.md:91`) says: "at least 90% of **cited** claims judged supported ... on a random sample of 100 claims". The gap rows have nothing cited (`cited: []`), yet they now compete for the same 100 slots. That causes two problems.

1. The A5 rule doesn't say what a gap row means for the score. It could go in the denominator as "not supported", be left out, or count only toward A6c. Each choice gives a different A5 number, and the choice could be made after seeing the results. That is exactly the freedom pre-registration exists to remove.
2. If gap rows are left out, A5 is judged on fewer than 100 cited claims, which goes against SPEC. The Amendments line ("Both can only lower A4") is also inaccurate: the sampling change doesn't touch A4, and it can move A5 either way.

**Fix:** keep SPEC's A5 sample at 100 cited claims, drawn with `A5_SEED` exactly as before. Put the gap rows on the same sheet as a separate block, either all of them or a fixed-seed sample of them. They should count only toward A6c (a gap row a person judges to assert something is an unsupported claim) and toward a reported "exempt-but-asserting" count. Write that rule in the A5/A6c row. Correct the Amendments line to say: "A4 can only go down; A6c gains rows, so it can only get stricter; A5 is unchanged." Then update `test_a5_population_includes_gap_exempt_sentences` to check that the 100 cited rows are the same with and without `gap_exempt`.

## Suggestions (should-fix, non-blocking)

- **S1.** Some sole-word claims are still exempt after this change: "We won [gap]", "We are trusted [gap]", "We are experienced [gap]", "We are leading [gap]", "We are the best [gap]", "We are unaccredited [gap]", and "We cant [gap]" (no apostrophe). Any word list is open-ended, and with M1 fixed, A6c is the backstop. If you'd like to tighten further before the freeze: add `won best leading trusted experienced` to `CLAIM_WORDS` and `cant` to `_NEG_RAW`.
- **S2.** The docstring for `split_claims` (`eval/score.py:170-174`) still lists only the old triggers ("no number word, acronym or app fact trigger"). Point it at `carries_other_content`.
- **S3.** `test_replaced_context_rebuilds_the_default_claimcheck_for_the_new_provider` only checks that the closure is a new object. It doesn't check that the new closure uses the new provider. Also check `c2.claimcheck.__closure__` (or call it on a fake that records which provider was hit) to confirm it holds `c2`, not `ctx`.
- **S4.** `_HYPHEN` also turns neutral hyphenated words ("e-mail", "follow-up") into claims. That is safe, because it only lowers A4, but it can push neutral stubs into the scored set. The `gap_exempt`/`gap_exempt_share` report will show it if it happens. No change needed now.
