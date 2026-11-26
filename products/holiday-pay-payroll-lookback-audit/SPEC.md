# SPEC: holiday pay look-back audit (T-153)

**DRAFT until Q-17 is answered A.** If Q-17 is answered B or C, this file is parked and nothing below is built. Stage stays G0 (score 64) until a conditional G1 is granted; the 70 bar still applies before G4. Evidence is from `state/ideas/holiday-pay-payroll-lookback-audit.md` (the idea file), accessed 2026-11-23 to 26. Nothing here is validated by a buyer.

## 1. Customer profile
- **Business:** UK payroll bureaux, accountants who run client payroll, and in-house payroll teams at firms of 20 to 500 staff with irregular-hours, part-year or variable-pay workers (hospitality, care, retail, events, agencies).
- **Who buys:** bureau owner or partner; finance or HR director in-house. **Who uses it:** the payroll manager or senior processor. **Who signs off:** a named payroll professional or adviser. The tool never decides legal status.
- **Triggers:** records duty in force since 6 April 2026 (regulation 16B, six years); Fair Work Agency (FWA) enforcement "expected to begin in 2027" with no date; proposed penalty of 200% of arrears, capped at £20,000 per worker (consultation, closed 22 Sept 2026, response unpublished); a client asking "are we right?". Penalties are proposed only, and the FWA starts with a letter, so urgency is unproven.

## 2. The problem, in cited words
Quotes are published, not from customers we spoke to.
- Xero users: "still stuck manually calculating everything in a spreadsheet" (Apr 2025); "Xero doesn't even produce reports with the necessary figures" (Nov 2025). A Xero admin: a 52-week report "is not a feature we have planned in our roadmap" (27 Nov 2025). Source: productideas.xero.com, 94 votes.
- BrightPay docs: the amount "is not automatically calculated by BrightPay and thus must be entered manually".
- CIPP (24 Sept 2026): "difficulties remain around interpreting and applying the rules in practice", citing "manual calculations and payroll software limitations".
- Bureau price lists already bill it as an extra: DCK £73.50 an hour; PSSG "price on application"; Irwin Mitchell review £1,500 + VAT.
- Survey (consultancy.uk, sample unknown, low weight): 11% calculate by hand.

## 3. Job to be done and core flow (the demo must nail this)
Job: "Show me, for every worker and past pay run, what holiday pay should have been under these settings, and where we differ, with working I can hand to a client or adviser."
1. **Upload** the payroll export (history, leave, workers CSVs; pseudonymous IDs only).
2. **Map pay items:** AI suggests a category per pay-item name (overtime, commission, bonus, holiday); a person confirms the table.
3. **Set options:** per-element "counts as normal pay", rounding variant, leave-year start, worker type (the user sets status).
4. **Recompute** holiday pay under the 2024 rules across the look-back window (52-week average, 104-week count-back, 12.07% rolled-up checks).
5. **Exceptions:** each underpaid, overpaid or cannot-check leave week with the working in plain English.
6. **Sign-off:** named reviewer approves or annotates each exception.
7. **Export:** an evidence pack (exceptions.csv, report.md or PDF) worded "recalculated under these settings", never "owed" or "compliant".

Demo data: the synthetic 60-worker payroll with seeded errors (regular overtime missing from the average; rolled-up pay in a pre-April-2024 leave year; rolled-up pay not shown separately).

## 4. MVP scope (two-week build from `products/_starter`, synthetic data only)
**Must (reuse, do not rewrite):**
- Wrap the existing `engine/`, `ingest/`, `report/` and `mapper/` behind a starter-based web app: sign-in, tenancy, upload, run, results page.
- Mapping screen: AI suggestion plus human confirmation (via the starter's AI adapter and cap; FakeAI in tests).
- Exceptions table with expandable working; sign-off with reviewer name and timestamp; export download.
- Option settings for per-element normal pay and leave-year start (already in the engine).
- Pseudonymised design: payroll ID only, no reason codes on absence, inputs deleted within 30 days (needs security sign-off).
- Demo seed, the legal-boundary wording, and an end-to-end browser test of the flow.

**Should:** rounding variants as an option; join of an HR leave file; a client-by-client view for bureaux; a PDF pack.

**Won't (this build):** real customer data; direct integrations with BrightPay, Xero, Sage or Moneysoft; accrual-hours (12.07% of hours) checks; sickness or family-leave modelling; pre-2024 rules; live payments; any contact with the FWA or workers; letters, claims, or legal conclusions.

## 5. Pricing hypothesis (UNVALIDATED)
Method: anchor on what firms pay today, then test with the demand test questions (section 7 of the idea file's new section), unprompted price first, then a bracket. Nothing is committed; selling is locked.
- Anchors: DCK £73.50 an hour for holiday pay calculations; Irwin Mitchell £1,500 + VAT a review; Muckle £500 to £1,500 + VAT HR audit; BrightPay Bureau about £229 a year (startups.co.uk, possibly out of date); a £13.99 spreadsheet template. No published price exists for look-back software.
- Hypothesis, per month ex VAT: **Starter £49** (up to 100 workers audited); **Bureau £149** (up to 500 workers, multiple clients); **Firm £349** (up to 2,000). Logic: a bureau recovers the monthly fee if it saves under one billable hour (£73.50) to two hours a month.
- **Free trial:** one audit on the customer's own pseudonymised export, 14 days. **First customers:** the first 3 pilots free for 3 months, then 50% off for 6 months, in return for feedback. All of this waits for the unlock.

## 6. Positioning
- **One sentence:** For payroll bureaux and accountants, a holiday pay look-back that recomputes every worker's past pay runs under the 2024 rules and shows the working for your sign-off.
- **Replaces:** the spreadsheet and hourly manual re-calculation (and one-off £500 to £1,500 audits).
- **Differentiators (true on the evidence read):**
  1. Whole-workforce look-back across past runs: no product among about ten checked documents one (not documented, not confirmed absent).
  2. Working shown per leave week, reproducing 17+ gov.uk and Acas worked examples.
  3. Calculation only: user-set settings, no legal conclusion, pseudonymous data.
- **Versus:** Fair Work Solutions (NMW payroll-upload underpayments; no holiday pay on its page); PayslipIQ (unlaunched waitlist; forward pre-pay-run checks); BrightPay and Xero (no holiday pay amount calculation); IRIS/Staffology (forward averaging only). **Kill triggers:** FWA calculator takes a whole payroll, or any of these ships a look-back (Competition falls to 2).

## 7. Pilot success metrics (when contact is allowed)
- **Activation:** at least 3 of 5 pilot firms run an audit on their own export within 14 days, and map at least 95% of pay items without edits beyond 5.
- **Weekly use:** at least 2 of those return for a second audit in 4 weeks.
- **Time or money saved:** self-reported hours per audit versus today at least halved (target 4 hours down to 1); at least one real exception confirmed by the firm.

## 8. Risks and open questions
- Urgency: no enforcement date, FWA letter first, six-year window under challenge (CIPP prefers two).
- FWA calculator scope unknown; free whole-payroll upload would end the idea.
- Payroll exports often lack leave data (Armstrong Watson, July 2026): HR leave file join may be needed, which may hurt the "upload one export" story.
- AI is a helper (mapping), not the core; incumbents could copy.
- Worker personal data and the advice boundary; real error rates unknown.
- Open: Q-16 (mapper test, up to $2), security sign-off of the data design, Q-17 answer, a named channel.
