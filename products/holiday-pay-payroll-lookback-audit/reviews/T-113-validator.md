# T-113 validator ruling: kill-test Part B (holiday-pay-payroll-lookback-audit)

Validator, 2026-11-26. Independent checker, not the mapper author or the Lead.

**VERDICT: KILL.** B1 failed on its own pre-registered line. Under the proof-test route this counts as a failed gate attempt. It is the idea's second G1 failure, after the 2026-11-23 REVISE (63), so the pipeline kill rule applies.

## What I checked (evidence)

- Results read from the T-113 worktree (`/home/user/t113`, branch `p/holiday-pay-payroll-lookback-audit/T-113`): `results/RESULTS.md`, `results/run.json`, `results/predictions.csv`.
- **One run only, no retry.** `run.json` shows `"fake": false`, `requests: 1`, `transport_attempts: [1]`, `failed_attempts: []`, `earlier_attempts_worst_case_usd: 0.0` and `finish_reasons: ["completed"]`. The prompt is `mapper-prompt-v2`, sha `ae175fa9...`, reasoning effort low, strict JSON schema. 0 rows were UNMAPPED. So the "retried with a changed prompt" half of the KILL line did not fire, and the run is a clean single shot.
- **Arithmetic re-derived from the confusion matrix.**
  - Off-diagonal cells: commission→bonus 1, expense→allowance 6, statutory→allowance 1, statutory→deduction 5, deduction→expense 2. That is 15 wrong, so 185/200 = **92.5%**.
  - Folding deduction into expense removes only the 2 deduction→expense errors. The statutory→deduction errors become statutory→expense and are still wrong. That is 13 wrong, so 187/200 = **93.5%**.
  - Subsets: AMBIGUOUS rows 23 of 32 correct (71.9%); other rows 162 of 168 correct (96.4%). Both figures match RESULTS.md.
- **Cost (B2):** 5,738 input and 2,222 output tokens, $0.0059. This passes under $0.02. Cost was never the risk.
- Gold sha `6323f7fb...` is reported as verified by the scorer. I did not re-hash it myself, because I have no shell in this run. The scorer refuses to run on a mismatch (`--expect-sha`).

## (1) Is B1 a KILL as pre-registered? Yes. No re-scoring is legitimate.

The mark in KILL-TEST.md (on main, written before any code) is: "at least 95% [of 200 names] are mapped to the correct holiday-pay category". The KILL line is "Below 95%". 92.5% is below 95%.

Each proposed rescue, tested against what was written before the run:

| Rescue | Pre-registered? | Ruling |
|---|---|---|
| Eight-category score (93.5%) | Ruled out in advance. DECISIONS.md, 2026-11-26T02:55Z (run 84ae, before the live run): "judged on the nine-category accuracy ... the eight-category figure ... is reported alongside but **does not rescue a nine-category fail**." mapper/README.md says the same. | Not allowed, and it fails anyway: 93.5% < 95%. |
| Drop the AMBIGUOUS rows (96.4% on 168) | No. The Lead counted the 32 AMBIGUOUS rows in the frozen gold before the run (DECISIONS run 84ae) and left them in the denominator of "200 names". No exclusion rule was written. | Goalpost moving. It is also backwards on substance. The studio's own lesson from the mtd kill is to "measure accuracy on the ambiguous lines a human reviews ... not on clear lines". The ambiguous names are the ones a payroll professional would need help with. Scoring only the clear names would test only what a keyword table already does. |
| "A person confirms the mapping table anyway" (mapper/README.md) | No. That README line is a prompt-injection control on audit use. It is not part of the B1 pass mark. The argument was available before the run and was not written into the mark. | Not allowed. It also works against the idea. If every mapping needs human confirmation, the AI is a suggestion layer over a deterministic engine. That supports the original "AI 7, rival could build without AI" view, or lower, not AI 8. |
| Consequence-weighted score (my own check, not proposed by anyone) | No. | I report it only so nobody discovers it later and treats it as a rescue. Of the 15 errors, 7 swap one excluded category for another (statutory↔deduction↔expense) and do not change the calculation. Counting only the 8 errors that change inclusion gives 192/200 = 96%. That would be a post-hoc metric written after seeing the labels, so it is inadmissible. The 8 errors also do real damage. 6 expenses mapped to `allowance` (which is in `COUNTS_FOR_NORMAL` in engine/elements.py) and 1 statutory payment mapped to `allowance` would inflate normal pay and create false underpayment flags. 1 commission mapped to `bonus_non_regular` would drop commission from the reg-13 average and hide real arrears, which is the liability direction. Each wrong element is applied to every worker paid that element, so an element-level error spreads across the whole workforce. |

The only open sub-question is the BrightPay layout half of B1. Xero and Sage 50 layouts could not be fetched, and the results do not report a separate layout score. That cannot rescue the result. B1 needs at least 95% on both halves, and the names half has already failed.

## (2) Outright kill, or only void the conditional G1? Outright kill.

- pipeline.md, proof-test route: "If it passes, the validator re-scores ... **if it fails, that counts as a failed gate attempt.**"
- The first failure is the G0→G1 REVISE (63) on 2026-11-23. The T-57 re-score to 64 was explicitly "not a new G1 attempt", so it is neither a pass nor a third attempt. The proof-test failure is the second.
- Kill rules: "An idea that fails a gate twice is killed." Nothing in the playbook lets the studio choose to park instead.
- This is the same pattern as pepr-packaging-data-pipeline (68, T-66) and restaurant-margin-copilot (66, T-80). Both were killed on "second failure after the proof test". Parking this one would break that precedent for the studio's favourite idea, which is the kind of exception the pre-registration exists to stop.
- Q-17 A does not change this. It allows a conditional G1 only "with a passed proof test", and the proof test here is the single KILL-TEST.md with Parts A and B ("PASS on A and B" is the pass). Part A passing alone was pre-registered to "move nothing". Even if Q-17 were read loosely, it is a route into G2. It does not suspend the kill rule for a failed gate attempt. The demand test (T-153) never starts.
- Effect on the score: AI stays at 7 at best, and Build stays at 11. The test that was meant to justify AI 8 instead shows mapping needs a human in the loop. The total stays at 64 or below, and the desk ceiling is unchanged below 70.

## (3) Verdict: KILL

**Reason.** The pre-registered B1 mark (at least 95% of 200 frozen pay-element names mapped correctly) was missed in a clean single live run: 92.5% on nine categories, 93.5% even on the eight-category fold, and 71.9% on the 32 ambiguous names. Every proposed rescue was either ruled out in writing before the run or would have to be invented after seeing the labels. Under the proof-test route a failed test is a failed gate attempt, and with the 2026-11-23 REVISE it is the second, so the kill rule applies. The underlying finding stands either way. The core of this product is a deterministic rules engine (Part A passed, and that engine is good), and the AI layer cannot sort pay elements reliably enough to run unsupervised. So AI is a helper, not essential, and the idea could not reach 70 on desk evidence in any case.

**Lessons**
1. **Put the hard cases in the pass mark, on purpose.** The ambiguous names are where the product's value lies, and they scored 71.9%. A future kill test should state a separate threshold for the ambiguous subset in advance, and a design should not depend on AI where its value lies only in the ambiguous tail.
2. **Score by consequence, but before the run.** Element-category accuracy treats a harmless swap between two excluded categories the same as an expense counted as pay. If inclusion versus exclusion is what matters, pre-register that metric, and give the harmful direction (dropping commission or overtime, which hides arrears) its own zero-tolerance or low-tolerance line. Per-element errors spread across the whole workforce, so judge them at payroll level.
3. **When the core is deterministic, a "make the AI look essential" test is the wrong bet.** Part A proved the engine. Part B was there to lift AI from 7 to 8, and even a pass reached only 66. The studio spent a gate attempt on a test that could not get the idea over 70. That breaks the pipeline's "score a pass first" rule in spirit: proceeding was justified by Q-17's conditional G1, not by the 70 bar. Before spending a gate attempt, check that a pass actually changes the decision.

**What would revive it** (all needed, and it is then a new idea file with a new gate count):
- The government consultation response and the FWA calculator's published scope, showing it works one worker at a time (Competition 8 to 9), plus a firm enforcement start date (Pain).
- Buyer evidence once Vishal allows contact: the T-153 demand-test pass lines (manual calculation today, an unprompted price of at least £49 a month, past behaviour, sign-off named).
- Either (a) a product framed honestly as a deterministic engine with a human-confirmed mapping table, scored at AI 6 to 7 and reaching 70 from Pain, Pay and Competition, or (b) a new pre-registered mapping test on a fresh held-out set (the 200 names are now burned), with an ambiguous-subset threshold and a harmful-error line, that passes.
- Keep the engine. Part A (merged e888e54, 46 tests green) is reusable and should not be deleted. Archive the product folder; do not extend it.

## For the Lead (I have not edited these files; the caller asked for this file only)

- Idea file Gate log line to add: `2026-11-26 | validator (T-113) | G1 proof test | KILL (second failure) | B1 92.5% nine-category (8-cat 93.5%, ambiguous 71.9%) < 95% pre-registered; one clean live run, $0.0059; rescues ruled out by DECISIONS run 84ae. See products/holiday-pay-payroll-lookback-audit/reviews/T-113-validator.md.`
- Move `state/ideas/holiday-pay-payroll-lookback-audit.md` to `state/ideas/killed/` (git mv).
- RANKING.md: remove it from rank 1 and add it to the Killed list with the reason above. Rank 1 becomes sme-council-tender-drafting (60, a kill candidate). Nothing in the queue is within 10 points of 70. Counts: 33 killed, 0 PASS, 21 ranked.
- Q-17's conditional G1 has no eligible idea now. Report this in the next digest, along with the kill, and do not start any G2/T-153 work.
