# T-151 validator check: scout round 24 (switchover data jobs)

Run date 2026-11-26. Time box about 12 minutes: 3 fetches, 4 searches. No page-text injection seen.

## 1. Spot-check of DROP verdicts

| # | Candidate | Page fetched | What the page says | Drop holds? |
|---|---|---|---|---|
| 1 | Accounting-software migration clean-up | https://apps.xero.com/uk/function/conversions/app/mmc-convert | Confirms the scout's summary. The 1Y+YTD plans cover the chart of accounts, contacts, opening balances, aged AR/AP, all bank, card and PayPal transactions, tracking, invoices, bills, credit notes, journals and 12 monthly comparatives. 293 reviews, 4.8/5, 90% five-star. Paid add-ons include a customised chart of accounts, payroll and a fixed asset register. No prices are shown. | Yes. A human-checked incumbent already covers the data an AI mapper would touch, and the platforms subsidise the move. |
| 2 | Payroll provider switch | https://www.brightpay.co.uk/docs/24-25/moving-to-brightpay-from-another-payroll-software/importing-from-moneysoft/importing-from-moneysoft-using-a-csv-file-mid-year/ | Mid-year CSV import of YTD totals works "at any point in the tax year". FPS is named as an alternative. Basic PAYE Tools appears only as a linked guide title on this page. No fee is mentioned. | Yes. The scout's wider claim ("other software via CSV or FPS, and Basic PAYE Tools") is only partly shown on this page, but it was labelled S, which is honest. A deterministic import plus per-row employee personal data is enough to drop it. |
| 3 | MTD ITSA onboarding for landlords and sole traders | https://monzo.com/business-banking/features/making-tax-digital | The MTD for Income Tax tool (powered by Sage) is free and "built into Monzo Business as standard", including the free Lite plan. It auto-categorises with rules. It does not handle accruals, VAT or accountant access. | Yes. The tool is bank-bundled at £0 and repeats the earlier kill of mtd-quarterly-prep. |

All three drops hold. Every claim I checked was either confirmed on the page or correctly labelled S.

## 2. Best WATCH: catch-up bookkeeping for clients years behind

What I looked for and what I found:

- **UK per-year catch-up price.** I still found none from a practice. Osome's £850 a year for historical filing and bookkeeping is the only explicit yearly figure, from a single provider. Zmartly, Taxflow Partners and Better Account all quote after a review and publish no number. Audit Consulting Group says catch-up is usually hourly, at £400-£800+ a month for complex cases. VJM Global (2026) cites £35-£45 an hour for firms and £18-£22 for freelancers. QuickBooks UK advises pricing clean-up as a one-off premium project. Sources: https://osome.com/uk/bookkeeping-services/outsourced-bookkeeping/, https://zmartly.co.uk/services/bookkeeping-services-uk, https://taxflowpartners.com/pricing, https://betteraccount.co.uk/pricing/, https://auditconsultinggroup.co.uk/blog/accounting-bookkeeping/how-much-do-bookkeeping-services-cost-in-the-uk/, https://www.vjmglobal.com/feeds/blog/bookkeeping-services-small-business-uk-cost, https://quickbooks.intuit.com/uk/blog/value-pricing-new-accounting-clients-right/ (all from search summaries).
- **Practice-owner hours per backlog.** I found none. FigsFlow and RosterElf repeat that "there is no flat rate" and that catch-up is "a project of unknown depth", but neither gives an hours figure. The unbilled-time pain is plausible, but it is still not quantified.
- **Does an AI catch-up vendor already serve UK small practices?** Yes, more than the scout found:
  - Booke AI works inside Xero and QBO books, at $129 per business a month, with firm pricing on request (https://booke.ai/compare/docyt-vs-bookeai-the-future-of-ai-in-accounting, S).
  - Docyt sells AI catch-up bookkeeping from $200 a month, though it is US-focused (https://docyt.com/catch-up-bookkeeping-services/, S).
  - Acting Office's AccaBot is a UK practice tool with a built-in PDF/scanned-statement-to-CSV converter for clients with no bank feed (https://www.accountingweb.co.uk/community/industry-insights/acting-office-is-transforming-accounting-and-bookkeeping-with-accabot, S).
  - Sleek claims AI plus accountant review for UK companies in arrears. That claim is still unverified.
  - Xero, Dext and Hubdoc already ingest statements and auto-categorise.

### Score a pass would get (pre-check, not a G0 file)

| Criterion | Likely score | Why |
|---|---|---|
| Competition (wedge) | 2/10 | There is no evidenced wedge. Booke AI already sits on Xero for firms, AccaBot already solves the UK "PDF statements, no feed" step, and the ledgers auto-categorise. A wedge would need a measured quality gap, such as reconciliation accuracy on multi-year UK statements, and nobody has shown one. |
| Pay | low/mid | There is only one UK yearly figure (£850, Osome). The rest is quote-after-review or hourly. The 2-price-point bar is not met. |
| Pain | mid | The pain is real and the write-off behaviour is described, but it is not quantified in hours. |

With Competition near 2 and Pay unproven, a pass cannot reach 70. Under pipeline.md's "score a pass first" rule, I am not writing a G0 file.

**Decision: keep WATCH, downgraded.** Promote only if a future run finds all three of these:
1. A UK practice-owner source that quotes hours per backlog year, or the write-off value.
2. A second published UK per-year catch-up price.
3. A measured gap in Booke AI or AccaBot on multi-year UK statement reconciliation, for example their handling of VAT-period alignment or opening balances.

Otherwise drop it at the next re-check.

Candidate 6 (the bureau onboarding desk) still has no hours source. I agree it is a weak WATCH and that it overlaps with 5.

## 3. Quality of the scout output

The scout output is honest: the F and S labels are accurate, the failed fetches are disclosed, and the drops are justified. I found one gap. The incumbent check for candidate 5 missed the AI-native catch-up vendors (Booke AI, Docyt, AccaBot), so the WATCH looked stronger than it is. I am noting this for the next round, not sending it back, because the conclusion (no KEEP) is unchanged.

VERDICT: PASS
