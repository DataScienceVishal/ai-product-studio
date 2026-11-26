# Meta-review 2: can anything reach 70 while contact is locked? (T-152, validator, 2026-11-26)

Desk reading only: pipeline.md, META-REVIEW-validator.md, RANKING.md, QUESTIONS.md (Q-6, Q-10, Q-15, Q-16), round 18-20 summaries, T-148 and T-151 validator files, and the holiday-pay idea file and KILL-TEST.md. All caps below are my estimates, read from the scores we have actually given.

## 1. Is 70 reachable with desk-only evidence?

Only just, and only when every row sits at its desk ceiling at once. Four rows need evidence the studio can't collect while it can't talk to buyers (Q-15 B: no buyer chat; Q-4 C: partner sector unknown):

| Row | Desk ceiling (estimate) | Why | Points only contact can add |
|---|---|---|---|
| Pain /20 | about 16 | Public complaints and surveys, but no measured hours per job | 4 |
| Pay /20 | 12-13 when the wedge is real | If nobody sells the job, no software price exists. Only bureau hourly rates or adviser fees can be found. Our highest Pay ever was 15 (Jelly, a mature market) | 7-8 |
| Reach /10 | 7 | The channel is unknown | 3 |
| Competition /10 | about 8 | "Not documented" is not "confirmed absent". Free trials (Q-9) help a little | 2 |

That is roughly 16 points out of reach. AI, Build and Risk can be earned at the desk (benchmarks, design, security sign-off).

The rows also pull against each other. A strong wedge means nobody sells the job, so Pay has no price to cite. A gap that survives usually has a fixed-rule core, so AI is low, or it holds personal data, so Risk is low.

**Arithmetic**
- **holiday-pay (64):** 15+12+7+7+11+7+5. Best desk case: Pain 16 (government response published), Pay 13, AI 8 and Build 12 (part B passes), Reach 7, Competition 9 (FWA calculator works one worker at a time), Risk 7 (pseudonymised design signed off) = **72**. That needs two government events with no date plus four other wins. Without the government events: 15+12+8+7+12+7+7 = **68**.
- **sme-council-tender-drafting (60):** 12+14+6+8+12+1+7. Competition is 1 because CleanTender sells the same job to the same niche at £99. Contact doesn't fix that. Desk ceiling is about 63.
- **subcontractor-rams-drafting (59):** the same story (RAMSGen). Ceiling about 62.

**Answer:** 70 is reachable only in theory, for an idea with a real wedge. The one idea that has a wedge is capped at 68 until outside events happen. The other ideas fail on real rivals, not on missing contact.

## 2. Did the Q-10 wedge rule fix calibration?

It removed the double count, but it didn't close the gap.
- **The five real products, re-scored under the rule:** Jelly 64, CleanTender 66, RemitClear 68. All still miss 70. RemitClear loses 21 points on Pain (12), Pay (11) and Reach (7), which are the contact rows.
- **The T-57 re-score of five parked ideas:** only holiday-pay moved, by 1 point (63 to 64).
- **New work since Q-10:** retailer-deduction 51 (Competition 2), leasehold 41, vet re-scored 50. Rounds 18, 19, 20 and 24 wrote 0 files, and T-148 found 0 KEEP. The drops died on direct rivals (SafeRec, Xero Syntax, Booke AI, EdgePetrol).
- **Verdict:** the rule is honest and should stay. Low Competition scores now reflect real rivals. But the leftover miscalibration sits in Pain, Pay and Reach, and the rule doesn't touch those rows. Proof tests are also filtering correctly (mtd, pepr and restaurant all failed their own tests), but as written a pass mostly moves only AI and Build, by +1 or +2.

## 3. Recommended changes (at most two)

**Change 1: conditional G1 ("G1c"). This changes the gate, so it needs Vishal as a question.**
- **Entry, all required:**
  - no red flag;
  - a pre-registered proof test passed;
  - score 64 or more;
  - the validator lists the contact-only points per row (at most 6 in total), and score plus those points reaches 70;
  - every desk-earnable row is already at its evidenced level.
- **What it allows:** G2 spec and a G3 core-flow MVP, capped at two weeks of runs. It uses one G3 slot, and only one G1c idea can exist at a time.
- **Exit:** a demand test written before G2 starts. It runs at the first contact Vishal allows (a friend demo, or `unlock selling`). If it fails, that counts as a failed gate attempt, and with the earlier REVISE the idea is killed.
- **What stays the same:** the 70 bar, the red flags and the kill rules. No idea goes to G4 without a full G1 pass.
- **Why it is honest:** it doesn't lower the bar. It moves the contact-only points to the first moment they can be tested, and fixes the pass mark in writing beforehand.
- It also bounds something that already happens: holiday-pay has an engine with 318 tests built while still at G0.

**Change 2: a desk-ceiling pre-screen and a contact-points column. This is a Lead-level process change.**
- Every score table adds two things: a "desk ceiling" row and a "held by contact" column.
- A scout writes a G0 file only if the desk ceiling reaches 70, or 64 if Change 1 is adopted. This extends the existing "score a pass first" rule from proof tests to G0 files.
- Stop open-ended scouting rounds. Seven rounds without a KEEP show they can't produce a pass. Re-check monthly instead.
- In each digest, show Vishal how many points declining contact costs.

## 4. Which idea would pass under Change 1?

**holiday-pay-payroll-lookback-audit, and no other.** Ranks 2 and up are 60 or below, with no evidenced wedge.

It needs three things:
1. **Part B proof test (Q-16, at most $2):** B1 at least 95% of the 200 frozen names mapped correctly, and B2 under $0.02 per payroll. That gives AI 8 and Build 12, so **66**.
2. **Risk design sign-off by security:** payroll ID only, absences coded "excluded week" with no reason, UK region, inputs deleted after 30 days. Risk 7, so **68**.
3. **Contact-only points listed:** Pain +2 (bureau hours per run), Pay +2 (a monthly price a bureau accepts), Reach +2 (a named bureau or accountant channel), 6 in total. 68 + 6 = 74, which meets the Change 1 entry.

**Demand test, written before G2:** at a friend demo, the friend's business or 3 bureau-type firms it introduces confirm that they calculate holiday pay by hand or in a spreadsheet today and name a monthly price they would pay. Without that, it is a failed attempt.

**These kill triggers stay in force:** the FWA calculator takes a whole payroll, or a vendor (Fair Work Solutions, PayslipIQ, BrightPay, Xero, IRIS) ships a look-back. Either one sends Competition to 2 and kills the idea.
