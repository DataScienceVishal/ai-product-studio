# Meta-review: is the rubric calibrated? (T-55, validator, 2026-11-24)

## 1. Calibration test: five real UK products scored as G0 ideas on their launch day

I scored each one on the evidence a scout would have had at launch: the competitors and prices that already existed, and the AI available then. Facts come from the studio's own fetched pages (Jelly, Paddl, CleanTender, RemitClear) and from public listings checked on 2026-11-24 (Lightspeed's Jelly page, RemitClear's Xero listing).

| Product (launch) | Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Comp /10 | Risk /10 | **Total** | Competitors that existed at launch |
|---|---|---|---|---|---|---|---|---|---|
| Jelly, restaurant costing (about 2018) | 15 | 15 | 6 | 8 | 6 | 3 | 9 | **62** | MarketMan, Kitchen CUT, Procure Wizard, Apicbase |
| Dext / Receipt Bank (2010) | 15 | 12 | 6 | 9 | 8 | 4 | 8 | **62** | Shoeboxed, Neat, Expensify |
| Paddl rates (2025/26) | 10 | 10 | 7 | 7 | 11 | 3 | 9 | **57** | Rightly Rated, ratings agents paid on contingency |
| CleanTender (2025/26) | 12 | 14 | 7 | 8 | 12 | 2 | 8 | **63** | BidWriter, mytender.io, Tenderforge, Stotles |
| RemitClear (about 2025) | 12 | 11 | 9 | 7 | 12 | 6 | 9 | **66** | HighRadius, Esker, Billtrust (enterprise only) |

**Result: none of the five clears 70.** They score 57 to 66, the same band as our parked ideas (60 to 68). Dext grew into a large business, and RemitClear reports more than 130,000 Xero invoices reconciled. Being on sale doesn't prove profit, but it does prove buyers.

**Why they fail, and what it says about the rubric:**
- **Competition is scored on whether rivals exist, not on the wedge.** Every one of these products launched into a market that already had paid competitors. That is the reason the market was worth entering, and it is what earned the Pay points. So the rubric counts the same fact twice: rivals raise Pay and then sink Competition.
- **Build (four weeks) and AI ("hard to copy in a week") cap mature products.** These products won through distribution and iteration, which a desk rubric can't see.
- **Reach is scored against an unknown channel.** The studio has one channel: a UK business whose sector we don't know. Every Reach score is a guess that tops out around 7.

**Proposed changes (defensible, and small):**
1. **Score Competition on the wedge.** 0 to 3 if a rival sells the same wedge, to the same segment, at a similar price (checked on the rival's own pages). 4 to 6 if there is a named wedge: a segment the rival doesn't serve, a price at least 30% lower, or a workflow the rival won't do. 7 to 10 only if there's no direct rival. Rivals merely existing is no longer a penalty.
2. **Proof-test route for 63 to 69.** An idea with no red flag can run one time-boxed benchmark against a numeric kill test written in advance (the mtd-quarterly-prep model), using public or synthetic data. If it passes, re-score. This replaces debating desk evidence with a test that can fail.
3. **Keep the 70 bar and the red flags.** The problem is how the bar is measured, not where it sits.
4. **Ask Vishal one question: the partner's sector.** The answer re-anchors Reach for every idea.

Under change 1, re-scoring the five products gives Jelly 64, CleanTender 66 and RemitClear 68 (Competition 8). So the rubric would still be strict, but no longer blind.

## 2. The three parked ideas closest to 70

| Idea (score) | Single most useful evidence | Can we get it without contact or spend? |
|---|---|---|
| pepr-packaging-data-pipeline (68, Comp 3) | Repackd's extraction failing on messy, real supplier spec sheets, measured by our own benchmark on public spec PDFs with a numeric kill test | **Partly.** Our side of the benchmark is free. A head-to-head needs a Repackd trial account, which is on the ask-first list. Without it, compare against Repackd's public demos and docs. |
| restaurant-margin-copilot (66, Comp 3) | A channel Jelly doesn't serve, which means knowing the partner's sector (accountant-led or a hospitality group) | **Yes.** It's one question to Vishal, not contact with anyone. A price wedge under Jelly's £129 per site can be checked on vendor pages for free. |
| holiday-pay-payroll-lookback-audit (63, Comp 6) | A government response or enforcement date for the 2024 holiday-pay rules, plus the FWA's calculator scope | **Yes.** All public, but it can't be hurried. Re-check monthly. The next free step is the Fair Work Solutions page check (T-42). |

Under the wedge rule, pepr would reach 70 if the benchmark shows a gap that can be named (Comp 3 to 5). Restaurant reaches 70 only with a confirmed channel as well (Reach 7 to 9, Comp 3 to 4).

## 3. Recommendation

The 0-of-53 record is a calibration fault as much as a scouting fault. The rubric rejects real UK products that are succeeding, mainly because Competition punishes rivals for existing while Pay rewards the same rivals. Adopt wedge-based Competition and the proof-test route in `pipeline.md`; that needs the lead's or Vishal's sign-off, and I haven't edited the file. Stop broad scouting rounds: 17 rounds have shown that more desk evidence won't move scores. Then:
1. Queue the partner-sector question to Vishal now.
2. Run the free pepr spec-sheet benchmark with a kill test written down in advance.
3. Re-score only pepr and restaurant-margin under the new rule.

If neither clears 70 after that, the studio should ask Vishal to pick one to build as a deliberate bet rather than scout an 18th round.
