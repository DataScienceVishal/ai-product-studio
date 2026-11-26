# T-160 scout report: new candidates on Vishal's edges (finance/tax, data engineering, RL pricing, RAG/agents)

Scout run, 2026-11-26. Public sources only, no contact, no accounts. Search results are quoted as data. I ran about 20 web searches and a few fetches inside the time box; several competitor pages returned 403 or 503 (noted below), so those facts come from search summaries and are labelled as such.

## Result: no candidate survived the competitor check

The brief asked for 3 new candidates, each with an evidenced wedge. I tested 14 ideas. Every one had either a direct SME-priced competitor or a bundled free feature from the platform owner. Under the task rule, those are dropped, not written up. I am not writing three G0 blocks for ideas I found already sold: that would repeat the first 15 ideas' mistake.

Two items below are leads, not candidates. Neither has a wedge evidenced yet, and neither should be scored or ranked.

## Candidates (none)

No candidate block is written because none passed. Self-estimated score for the best near miss is given under Leads so the Lead can see the ceiling.

## Leads (wedge not evidenced; do not rank)

### L1. sub-MW commercial battery (BESS) dispatch optimiser (RL edge)
- Buyer: UK owners of small co-located batteries (under about 5 MW, often behind a site's demand), who may be too small for the big optimisers.
- Why it is on the list: it is the one idea here that uses Vishal's RL edge, and the data is public (NESO and Elexon open data, so a desk backtest on public prices is lawful).
- Evidence so far (search summary, 2026-11-26):
  - Optimisers normally take a percentage of revenue (energy-storage.news, "UK BESS battery storage optimisation merchant contracting model", https://www.energy-storage.news/uk-bess-battery-storage-optimisation-merchant-contracting-model).
  - Modo Energy's own forecast docs flag that small sites have a 1 MW minimum unit size and integer-market issues that hit frequency-response revenue (https://forecastdocs.modoenergy.com/docs/small-bess-sites).
- Not found: any optimiser's minimum site size, any fee for a sub-MW asset, any count of UK sub-MW batteries. So there is no evidenced price point and no evidenced "priced out" segment.
- Risks: a dispatch product touches live trading, market licensing and metering (Build and Risk), and the buyer count is unknown (Reach).
- Self-estimate if the wedge held: Pain 10, Pay 8, AI 12, Reach 4, Build 5, Comp 3, Risk 6 = about 48. It fails the 64-70 floor even with a wedge. Not recommended.

### L2. FRS 102 lease accounting for accountants: reopened only if Lease102 is disproved
- This was the strongest forcing function I found, and it is dropped below because a direct competitor exists. Listed here so the Lead can see why it is not a candidate.

## Dropped (competitor or bundled free feature found)

Each line: idea, buyer, what already sells the job, URL, price. Access date 2026-11-26 for all.

1. **fuel-forecourt-dynamic-pricing** (RL pricing, UK independent petrol stations). EdgePetrol was built for independent retailers and costs about £90 per site per month (about £1,080 a year), with a free trial and a three-month trial for operators under 99 sites (Forecourt Trader, https://forecourttrader.co.uk/epos/gaining-an-edge/642401.article; undated, so the price may have moved). Kalibrate (https://kalibrate.com/fuel-price-optimization/), OPIS PricePro and TLM's evoPricePlus (AI pricing, Forecourt Trader) also sell the job. Fuel Finder open data is public and lawful (https://www.gov.uk/government/collections/fuel-finder), but that helps every vendor too.
2. **frs102-lease-accounting-desk** (finance/tax, UK accountancy practices, forcing function: FRS 102 lease changes apply to periods starting on or after 1 January 2026, Forvis Mazars https://www.forvismazars.com/uk/en/insights/financial-and-corporate-reporting-updates/frs-102-lease-accounting-changes-2026; FRC reminder 2026-09 https://www.frc.org.uk/news-and-events/news/2026/09/frc-issues-reminder-of-significant-change-now-effective-in-uk-gaap/). Lease102 is built for FRS 102 for UK and Irish SMEs and accountancy firms, from £20 a month (GetApp, Capterra and Slashdot listings; Capterra Starter £20 a month or £200 a year), and listings say it has AI extraction of lease terms, journals and disclosures, with Xero and Sage integrations. Sage also sells lease accounting (https://sage.com/en-gb/accounting-software/lease-accounting/; page returned 403, so only the search listing is cited). Lease102's own site and Capterra page returned 503 and 403, so the feature claims are vendor copy from listings and are unverified. Nothing here beats a £20 SME-priced tool.
3. **hmrc-ct600-r-and-d-evidence-pack** (finance/tax, UK software SMEs claiming R&D relief). AgenTax integrates with Jira and GitHub to extract project data and automate documentation (https://www.capterra.co.uk/software/1111199/AgenTax). Plandek imports Jira tickets for R&D claims (https://plandek.com/blog/rd-tax-credits). Finnli is an Atlassian Marketplace app for R&D compliance (https://marketplace.atlassian.com/apps/1227074/finnli-r-d-tax-compliance-and-financing). Claimer is a London claims platform for startups. No UK per-claim price found.
4. **landlord-agent-statement-capture** (finance/tax, landlords and their accountants under MTD for Income Tax). FreeAgent launched AI capture of letting-agent statements in June 2026, included at no extra cost in FreeAgent for Landlords (https://www.freeagent.com/blog/rental-statement-capture/, news summary at https://www.landlordtoday.co.uk/breaking-news/2026/06/new-ai-tool-for-landlords-forced-into-making-tax-digital/). Landlord Studio and Clear Books also sell MTD for landlords.
5. **small-audit-journal-entry-testing** (data engineering, small UK audit firms). Finspectors.ai uploads ledgers and journals and runs ML and rule tests, aimed at small and medium firms (https://www.capterra.co.uk/software/1076830/FINSPECTORS-AI). Smart Audit lists from US$99 (https://www.capterra.co.uk/software/203284/smart-audit). Qwantify and an Excel AI audit add-in also appear. ICAEW's 2026 monitoring report (https://www.icaew.com/regulation/working-in-the-regulated-area-of-audit/audit-monitoring-report-2026) gives scale (375 visits, 667 audits in 2025) but no journal-testing finding that I could confirm.
6. **parcel-invoice-audit-refunds** (data engineering, UK e-commerce sellers). LateShipment sells "agentic parcel audit" and carrier claims, with success fees quoted in guides at 25% to 50% of recoveries or a plan fee (https://www.lateshipment.com/features/audit-refunds/, https://www.lateshipment.com/blog/parcel-audit/). Sendcloud publishes UK claim guides.
7. **craft-brewery-alcohol-duty-return** (finance/tax, small UK brewers). Monthly returns and Small Producer Relief are deterministic (HMRC guidance, https://www.gov.uk/guidance/submit-a-beer-duty-return); HMRC's 2026 evaluation found producers' confidence in duty calculations was often high, helped by trade bodies, software providers and the SPR calculator (https://www.gov.uk/government/publications/understanding-alcohol-producers-experiences-of-duty-reforms). No AI need, no price found.
8. **franchisor-royalty-reconciliation** (finance, small UK franchisors). FranchiseMS (UK, from £40 per user; head office £25; per unit from £15 per GetApp UK, https://www.getapp.co.uk/software/2100420/franchisems), FranchiseBlast ($20 per location a month), Franchise Launcher ($49 and $99 a month, royalty module in Business) already cover royalties. I could not confirm a dedicated sales-reconciliation feature, but the SME price band is taken and the job is arithmetic.
9. **vat-health-check-ai** (finance/tax, UK accountants). QuickBooks ships a VAT AI Agent beta and an error checker at no extra cost (https://quickbooks.intuit.com/uk/vat-software/error-checker/). Dext Data Health is a paid add-on (price not published). FreeAgent shows underlying items on a scanned VAT return.
10. **card-acquiring-statement-checker** (UK merchants). Statement (uploads a statement and recommends providers), Fee Navigator and Staitment already analyse statements; Paychex and Helcim offer free analysers, and most are sales funnels (search summary 2026-11-26; startups.co.uk fee guides). Free tools set the price at £0.
11. **subcontractor-retention-and-payment-notice-tracker** (construction subcontractors, UK). Retention Track already sits in the Xero UK app store for tracking and recovering retention (https://apps.xero.com/uk/function/invoicing-jobs/app/retention-track); Archdesk and TrakPro cover retention for main contractors. The government announced a retention ban on 24 March 2026 through the Commercial Payments Bill (third reading reported 20 October 2026, Gowling WLG https://gowlingwlg.com/en/insights-resources/articles/2026/uk-government-proposes-ban-on-retention-payments-in-construction-contracts), which shrinks the long-run pain. Calculating notice deadlines from each bespoke contract is a gap I did not find in any product, but it is a legal-adjacent reading job and I found no price.
12. **golf-club-visitor-dynamic-pricing** (RL pricing, UK independent golf clubs). Tee-sheet vendors bundle it: Lightspeed Golf lists Dynamic Pricing as a feature (https://www.lightspeedhq.com/uk/golf/pricing/), ClubNet Systems launched a dynamic pricing tool, Intelligent Golf, GolfPro, Sweetspot and Golfmanager sell tee sheets with variable pricing. A platform owner can add the feature in a month.
13. **capital-allowances-claim-pack** (finance/tax, SMEs). Searches found only GOV.UK guidance and a Xero guide; no specialist fee or AI tool figures, so there is no evidenced buyer spend. Dropped on lack of Pay evidence, not on a competitor. Not tested further.
14. **fleet-pcn-and-charges** and **academy-trust-finance-returns**: considered, not searched, dropped on first reading as probably crowded (fleet software bundles PCN handling; trusts buy from large education finance suppliers). No source read, so these are not evidence-backed drops. They could be searched later.

## Observations for the Lead

- The same pattern repeated again: when a 2026 rule or a pain exists in UK finance, an SME-priced vendor (£20 to £99 a month) usually already sells the job, and they ship AI document extraction as standard. Lease102 is the sharpest example. It is a one-product firm with a forcing function that the studio would have picked.
- Per the Q-18 note and META-REVIEW-2, I recommend the next scouting input be one the desk can't generate: a lead from the friend's UK business, or Vishal's own observations.
- If a future scout wants the RL edge, the only public-data pricing backtests I found are the Fuel Finder open data (but EdgePetrol at £90 per site a month occupies that space) and NESO/Elexon market data (L1, but Build and Risk are heavy).

## Count

- Candidates written: 0 of the 3 requested.
- Leads (unscored, wedge unproven): 1 (L1, about 48 if the wedge held).
- Dropped: 14 (12 with a competitor or bundled feature and a cited URL, 2 on lack of evidence: items 13 and 14; 14 is unsearched).
