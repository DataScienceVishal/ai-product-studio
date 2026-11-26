# T-153 validator gate check: demand test and draft SPEC

VERDICT: CHANGES

Validator, 2026-11-26. Desk reading only: `state/ideas/META-REVIEW-2-validator.md` section 4, the "Demand test (pre-registered, T-153)" section of `state/ideas/holiday-pay-payroll-lookback-audit.md`, `SPEC.md` (draft), plus `products/_starter/README.md`, `ingest/FORMAT.md`, `BRIEF.md` and `benchmark/KILL-TEST.md` to check claims. I changed no files except this one. Some of the demand-test edits change criteria, not only wording, and some edits are to the SPEC, so the "fix the wording and PASS" route doesn't apply.

## 1. Demand test: pre-registered, numeric, falsifiable, hard to game?

| Check | Result | Note |
|---|---|---|
| Pre-registered | PASS | Dated, written before G2, frozen once the test starts, and any change resets it |
| Numeric | PASS | 3 firms, at least £49, 2 of 3 on Q6, 60 days, at most 5 firms |
| Falsifiable | PASS | Clear fail lines, no extension, kill triggers included |
| Polite friend can't pass it alone | PARTLY | The friend's business can't pass it alone (3 firms needed). But the friend picks the other firms, may run the interviews, and the questions ask for opinions, not past behaviour |
| Questions not leading | PARTLY | Q1 is good (open answer first). Q4 assumes they would pay and assumes a monthly fee. Q6 is a cheap hypothetical yes |
| "Unprompted price" measurable | NO, as written | Not defined: what counts as a prompt, how a range or "it depends" is scored, and the starter's billing page could show our prices during the demo |

**Edits needed in the idea file's demand test.** Add them under a dated note "amended by validator before any contact, 2026-11-26":

1. **The friend counts once.** "The friend's own business may count as at most 1 of the 3 firms that meet any pass line. At least 2 must be other firms, and none of them may be the friend's own payroll clients or suppliers." (A firm that depends on the friend for business is a polite yes.)
2. **Who asks, and how answers are recorded.** "The interviewer reads Q1 to Q7 word for word, in order, and adds no product description beyond the demo. Notes are written during the call or within 24 hours and sent to the studio unedited. Every interview held counts: none may be dropped or repeated. The firms counted are the first 5 interviewed."
3. **Define 'unprompted'.** "Unprompted means the first number the firm gives in answer to Q4, before Q5, when no price, range, plan name, discount or anchor (including DCK £73.50, Irwin Mitchell £1,500 or the SPEC's tiers) has been said, shown on a screen, or put in any document the firm has seen. A range scores its lower end. A one-off or yearly figure is divided to give a monthly one (yearly ÷ 12, one-off ÷ 12). 'It depends', 'no idea' or no number scores £0." Also add: "The demo build shows no price, plan or checkout page."
4. **Reword Q4 so it isn't leading.** "Would you pay for a tool that does this look-back with the working shown? If yes, roughly how much, and per month, per year or per audit? If no, why not?" A "no" scores £0.
5. **Require past behaviour, not only opinions.** Add a pass line: "At least 2 of the 3 qualifying firms give a concrete past fact in Q2 or Q3: a date or period when they last re-checked holiday pay with an hours figure, or an amount they charge or pay for holiday pay work." Without this, the Pain +2 point is just opinion.
6. **No personal data in Q6.** Change "name a sign-off person" to "name the sign-off role (for example payroll manager or external adviser)". Record firms by type and size, not by person (CLAUDE.md section 10).
7. **Fix the ambiguous fail line.** Replace "Fewer than 3 firms meet any of the three pass lines above" with "Any one pass line is not met by enough firms."
8. **Decide the contact-only points now** (META-REVIEW-2 section 4 listed them, but the test says only "up to +2 each"): "Pain +2 if at least 2 qualifying firms report a concrete hours figure (median recorded). Pay +2 if the qualifying firms' median unprompted price is at least £49 a month. Reach +2 if the friend's business introduced at least 2 of the qualifying firms, or one bureau named a channel that reaches several employers. Points are all or nothing per row." Without this, the re-score can be argued after the fact.

## 2. Does it match the conditional-G1 exit I proposed?

**Yes, and it is stricter.** My exit wording was: "the friend's business or 3 bureau-type firms … confirm manual or spreadsheet calculation and name a monthly price". The test requires 3 firms, a £49 minimum, a Q6 intent line and a 60-day limit. It keeps "a failure plus the earlier REVISE means kill", the 70 bar before G4, and the kill triggers (it also adds Fair Work Solutions). The only gap is edit 8: the contact points need written criteria.

One reminder that isn't a test defect: my G1c entry in section 4 also needs part B to pass (Q-16, unanswered) and a security sign-off of the pseudonymised data design. T-149 is a code security review, not that design sign-off. Until both exist, Q-17 A allows the spec and build to start, but the idea isn't G1c. The SPEC's header and section 8 say this honestly.

## 3. SPEC (draft)

**Scope for two weeks from `_starter`: realistic, with two gaps.** The starter already provides sign-in, tenancy, the AI adapter with cap, FakeAI and the retention purge (its README). The engine, ingest, mapper and report already exist, and `leave.csv` is already a required input (FORMAT.md). The new work is the upload and storage of runs, the mapping screen, the exceptions, sign-off and export screens, and one browser test. That fits.

Edits needed:
- **S1 (blocks the demand test).** Add to Must: "Billing, plans and checkout are switched off in this build. No price appears anywhere in the app or demo." The starter README step 3 says to load the SPEC's prices into `app/billing.py`. Doing that would put £49, £149 and £349 on screen and spoil the unprompted price.
- **S2.** Add to Must: what the demo runs on if Q-5 (Azure deploy cost) or Q-16 (AI spend) is still unanswered. For example: "The demo runs locally or on a screen share, with FakeAI or the mapper's rule-based suggestions. A real model is used only after Q-16 is yes, within the $6.10 AI budget." Today the scope assumes a hosted demo with live AI, and neither is approved.
- **S3.** In section 4 Should, "join of an HR leave file" reads as if leave data is optional. Reword: "Import of a separate HR-system leave export (the engine's own `leave.csv` is already required)."
- **S4. Unbacked or mislabelled claims:**
  - Section 2 groups Irwin Mitchell's £1,500 + VAT review under "bureau price lists". It is a law-firm review. Move it to its own bullet.
  - Section 6 differentiator 2, "17+ gov.uk and Acas worked examples", isn't in the idea file. It comes from `benchmark/KILL-TEST.md` and `BRIEF.md`. Cite that file and add "on encoded official examples; real payrolls untested".
  - Section 5 cites "section 7 of the idea file's new section". The questions are in the idea file's "Demand test (pre-registered, T-153)" section. Fix the reference.
- **S5. Prices.** They are clearly labelled UNVALIDATED and nothing is committed: PASS. One fix to the logic: £149 is about 2.0 billable hours at £73.50 and £349 is about 4.7, so "under one to two hours a month" holds only for Starter and Bureau. Reword: "Starter and Bureau pay back at 1 to 2 billable hours a month; Firm needs about 5". Also label the pilot terms (3 months free, then 50% for 6 months) "hypothesis, not offered". They differ from the starter's EARLY50 (50% off for 3 months).
- **S6.** Section 7's activation line is garbled ("map at least 95% of pay items without edits beyond 5"). Reword: "at least 95% of pay-item names mapped correctly by the AI suggestion, with at most 5 manual corrections per audit".

## What turns this into PASS

Apply edits 1 to 8 to the idea file's demand test under the dated note, before any contact, and apply S1 to S6 to `SPEC.md`. S1, S2 and edits 3 and 8 carry the weight. The rest is wording. A re-check is desk-only and short.

## Re-review (2026-11-26)

VERDICT: PASS

I re-read the "Amendment 2026-11-26, before any contact, per T-153 validator review" in `state/ideas/holiday-pay-payroll-lookback-audit.md` (it states that it wins on conflict) and the current `SPEC.md`.

| Item | Applied? | Where |
|---|---|---|
| 1 Friend counts once; no clients or suppliers | Yes | amendment 1 |
| 2 Questions read word for word; notes within 24 h, unedited; every interview counts; first 5; firms recorded by type and size | Yes | amendment 2 (overrides "written down verbatim by the studio") |
| 3 "Unprompted" defined; no price, plan or checkout in the demo | Yes | amendment 3 |
| 4 Q4 not leading; "no" scores £0 | Yes | amendment 4 |
| 5 Past-behaviour pass line | Yes | amendment 5 |
| 6 Sign-off role, not a person | Yes | amendment 6 (overrides the original Q6 and the third pass line) |
| 7 Fail line fixed; the four pass lines listed | Yes | amendment 7 |
| 8 Contact-only points decided now, all or nothing | Yes | amendment 8 |
| S1 Billing off, no price shown | Yes | SPEC section 4 Must, plus section 5 |
| S2 Demo fallback without Q-5 or Q-16 | Yes | SPEC section 4 Must |
| S3 HR leave import reworded | Yes | SPEC section 4 Should |
| S4 Irwin Mitchell moved; 17+ examples cited to KILL-TEST; reference fixed | Yes | SPEC sections 2, 6 and 5 |
| S5 Payback logic; pilot terms labelled a hypothesis | Yes | SPEC section 5 |
| S6 Activation metric reworded | Yes | SPEC section 7 |
| G1c caveat | Yes | SPEC section 8: not G1c until Q-16 passes and the data design is signed off |

No new problems. The original text still says "the studio" records answers and "name a sign-off person", but the amendment overrides both, as it says it does. The test is now pre-registered, has numbers, can clearly fail, and defines the unprompted price. The SPEC's scope fits two weeks from `_starter`, its prices are labelled as guesses, and every claim is traced to a source. This passes T-153 only. It is not a G1 or G1c grant: that still depends on Q-17, Q-16 part B and the security sign-off of the data design.
