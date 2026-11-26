# DRAFT for Q-18 option A — not started; T-159

Validator, 2026-11-26. This draft is used only if Vishal picks Q-18 A or A becomes the default. Nothing here has been run or spent. RANKING.md, the idea files and QUESTIONS.md are unchanged.

**Result: no eligible candidate.** None of the four ideas at 58 or above can plausibly reach 70, even if a desk proof test passes and every contact-only point is earned under the Q-17 rules (at most 6 contact points, at most +2 per row). All four are capped by the Competition row. Contact can't fix that row, and neither can a desk proof test.

## 1. Eligibility table

Rule applied (Q-17 rules extended by Q-18 A): desk score after a passed proof test, plus contact-only points (at most 6 in total, at most +2 a row, as in the holiday-pay demand test amendment 8), must plausibly reach 70. Each row is capped at its evidenced desk ceiling (META-REVIEW-2-validator.md section 1).

| Idea | Now (Pain/Pay/AI/Reach/Build/Comp/Risk) | Rows a passed desk proof test could move | Rows only contact could move (held by contact) | Plausible ceiling | Main kill risk |
|---|---|---|---|---|---|
| sme-council-tender-drafting | 60 (12/14/6/8/12/1/7) | AI 6→8 (pack-to-question extraction and grounded drafting on public OGL tender packs); Build 12→13. **+3, giving 63** | Pain +2 (bids a year, hours per bid); Pay +1 (already 14, above the desk norm of 12-13); Reach +2. **+5, giving 68** (69 only if every row maxes out at once) | **66-68** | No wedge against a same-niche incumbent. CleanTender, re-read 2026-11-26 (https://cleantender.co.uk/): soft-FM only (cleaning, security, grounds, waste and hygiene, catering), drafts answers from the firm's evidence, one-click claim check, fit score and bid/no-bid verdict, £99 a month or £990 a year, a free plan, and a 7-day trial that needs a card. A measured quality gap would need a CleanTender trial (card and account, so ask-first). Competition stays at 1. Procurement Act Sch. 7 para 13 exclusion risk from invented claims. |
| subcontractor-rams-drafting | 59 (12/13/6/8/13/1/6) | AI 6→8 (RA-to-MS consistency and site-rule capture from a synthetic site pack); Build 13→14. **+3, giving 62** | Pain +2 (rejection rate, days lost); Pay +1; Reach +1. **+4, giving 66.** The only quality wedge, "accepted first time", needs real submissions to principal contractors. That is contact, and it goes beyond the 6-point cap. | **65-66** | Same job already sold. RAMSGen, re-read 2026-11-26 (https://www.ramsgen.com/): drafts RAMS from the uploaded pre-construction information, drawings and specification, with page citations. Custom templates and RAMS review at £99, £59 Standard, £199 Principal, first RAMS free with no card. swiftRMS £49 unlimited; RamsBox £7 a RAMS. The output is safety-critical (Risk 6). |
| b2b-win-loss-interviewer | 59 (10/12/8/6/12/3/8) | AI 8→9 (adaptive follow-up and theme-tagging eval on synthetic buyer personas); Build 12→13. **+2, giving 61** | Pain +2, Pay +2, Reach +2. **+6, giving 67.** The participation rate (Clozd: 5-30%) is contact-only too, and it decides the value. | **67** | User Intuition charges $30 an interview with a $0 Starter plan. Clozd's HubSpot app auto-invites buyers on close. Klue sells an AI Interviewer. The buyers (UK SaaS product marketers) are outside the partner's reach as a UK business owner, and few deals a quarter means few interviews. |
| esos-phase4-evidence-pack | 58 (10/12/7/7/11/2/9) | AI 7→8 (utility invoice extraction, a commoditised job; see the restaurant photo lesson); Build 11→12. **+2, giving 60** | Pain +2, Pay +1, Reach +1. **+4, giving 64** | **62-64** | The job comes round every four years, so there is no subscription. Lead assessors bundle the data work with the sign-off (Carbon Footprint Sustrax already has a digitised evidence pack). Most groups already compile annual energy data for SECR. |

**Why none qualifies:**
- **Desk scores after a pass:** 63, 62, 61 and 60. All are below Q-17's own entry score of 64, and below the pipeline's proof-test floor of 63, except tender at exactly 63.
- **Total after contact points:** 64 to 68, short of 70 in every case. Tender reaches 69-70 only by assuming every row hits its maximum at once and by breaking the 6-point contact cap. That is not "plausible".
- **The binding row is Competition (1-3), not the contact rows.** Under the Q-10 wedge rule, Competition moves only with an evidenced wedge against the incumbent the buyer would otherwise pay. None of the four has one. A benchmark against a raw LLM (the cheapest substitute) is not a wedge against CleanTender, RAMSGen or User Intuition.
- **The "score a pass first" lesson in `playbooks/pipeline.md` (T-66, T-113) forbids spending on a benchmark whose pass can't reach 70.** Holiday-pay was killed partly for this reason.

## 2. Proof-test draft

**None written.** Writing a pre-registered test for an idea that can't reach 70 would spend a gate attempt and up to $2 to learn nothing decision-relevant. A failure would kill an idea that is already parked. A pass would leave it at about 61-63 with Competition unchanged.

### Closest miss and the only free check that could change this

The closest miss is **subcontractor-rams-drafting**. It is the easiest build, and its wedge check is desk-only and free.
- **Desk check (no spend, no contact, no accounts):** read 3 or more large UK principal contractors' public supply-chain or subcontractor handbooks. Find a mandatory RAMS requirement beyond layout that RAMSGen's, swiftRMS's and RAMS Pro's own pages show they don't meet. Examples: a structured digital submission, a required hazard-control matrix keyed to the PC's own permit system, or a sign-off workflow.
- **If found and evidenced:** Competition goes 1→5. Then 59 + 4 + 3 (AI and Build after a proof test) = 66 on desk, and 66 + 4 to 6 contact points = 70-72. That would be eligible.
- **Expected outcome: negative.** RAMSGen Professional already sells custom templates and a RAMS review against project requirements, so a format-only requirement won't count.
- **Only after a positive check** would the validator write the proof test. The likely metric is RA-to-MS consistency and site-rule coverage on 30 synthetic site packs, run on the T-56 kit with gpt-5-mini at an estimated cost under $0.50.

The tender equivalent is a segment none of the tools serve, sized from the Contracts Finder OCDS API. Round 11 (T-48) already looked and found none, so it is not recommended again.

### Contact-only demand test (only if an idea later becomes eligible)

It would follow the holiday-pay demand test format, including amendments 1 to 8 (killed/holiday-pay-payroll-lookback-audit.md):
- at least 3 firms interviewed, the friend counting once;
- verbatim questions about how the job is done today;
- a past-behaviour fact (hours, or money paid);
- an unprompted monthly price above the incumbent's floor. For RAMS that is at least £49 a month, swiftRMS's unlimited price. Below it, Pay stays flat.

## 3. Recommendation to the Lead

- **Q-18 A has no eligible candidate.** If A is picked or defaults, the result is "nothing to build". Say so in the next digest, or amend Q-18 before its default time, so Vishal isn't choosing an option that yields nothing.
- **Of the remaining options, only C changes the numbers,** and only partly:
  - a friend demo earns contact points, but it doesn't lift Competition for tender or RAMS;
  - its main value is a real lead from the friend's own UK business (the unknown partner sector, Q-4). That is the one scouting input that desk rounds can't produce.
- **B keeps the bar honest but builds nothing.**
- **The validator's preference is C, with B as the fallback.** A shouldn't stay marked as recommended, because it has no eligible candidate.

Competitor facts re-checked 2026-11-26: CleanTender homepage and RAMSGen homepage, both fetched. The other facts come from the idea files' 2026-11-23/24 reads and were not re-fetched.
