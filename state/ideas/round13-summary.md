# Round 13 scout summary (T-50, 2026-11-24)

Brief: per-unit bureau/agency jobs with public per-item prices where AI does most of each unit. Kill test first, on vendor and listing pages. Time box about 22 minutes. Evidence is mostly search-result summaries (each candidate got one or two searches). Fetched in full: buildhub SAP thread, Stroma SAP page. No prompt-injection attempts seen. Note: some search hits (pages.dev "idea-..." sites, ukbc-website.pages.dev) look like generated or throwaway sites; treated as low-trust.

## Written (1 file, G0, scores blank)
| Slug | Pitch | Per-unit price evidence | Kill-test result | Biggest doubt |
|---|---|---|---|---|
| sap-design-stage-input-desk | Pre-fills SAP input sheets from architect drawings with traced sources, for small assessors | £75 + VAT and £99 per plot (low-trust pages); £90-£120 forum quotes from 2017 | No AI drawing-to-SAP tool found in two searches; Elmhurst and Stroma release notes not checked; Stroma page shows none | Pay: per-plot prices too low to support a subscription, evidence weak; HEM replaces SAP |

Honest read: this is a weak survivor. Zero strong survivors this round.

## Dropped at the kill test (candidate, evidence, reason)
1. Domestic inventory and check-in reports (per inventory): The Property AI (https://www.capterra.co.uk/software/1100109/The-Property-AI), Inventory Hive (https://www.inventoryhive.co.uk/news/how-pricing-works, £30 a month, about £0.66-£3.60 a report), Kaptur, InventoryBase. Already cheap and AI.
2. Fire risk assessment report writing: FireCheckr (https://www.capterra.co.uk/software/1104708/FireCheckr), AssessHub, Property Inspect "Inspect AI" (https://propertyinspect.com/fire-risk-assessments/). No per-report outsourcing price either.
3. Minute-taking per meeting: Magic Minutes (£12 a month), BoardPro (https://www.boardpro.com/en-gb/pricing), GovClerk, MinuteSmith on Capterra UK. Human clerking £355-£450 a meeting (Lincolnshire) is governance, not just minutes.
4. Payroll per payslip (£5-£10 managed, https://www.expertmarket.com/uk/payroll-services/payroll-software-costs): deterministic, Xero £1.50 a person, no AI role. Dropped on reasoning.
5. EICR report write-up outsourcing: no outsourced per-report price found; only consumer EICR prices (MyBuilder, Checkatrade). Nothing to price.
6. Nutrition and allergen analysis per recipe (£50-£120, University of Aberdeen store https://www.store.abdn.ac.uk/product-catalogue/division-of-applied-health-sciences/analysis/nutritional-analysis): LabelCalc, NutriScheme, MenuSano and others already sell software (Capterra UK).
7. Tachograph analysis per driver (£4-£5 a month): Tachomaster £1 a driver a week (https://tachomaster.co.uk/pricing/), Descartes Smartanalysis 25p a driver a day (https://smartcompliance.descartes.com/solutions/smartanalysis-tachograph-analysis-software/pricing), Tachogram. Cheap and deterministic.
8. Transcription per minute (£1-£2.80, G-Cloud pricing PDFs): Trint and other AI tools already cut it (https://trint.com/blog/ai-can-cut-legal-costs-99-percent-heres-how); commodity.
9. Micro-company accounts and CT600 per set (£379-£649 + VAT Easy Digital Filing, £499 GoForma; DataTracks iXBRL £75-£98): Anna Auto Accountant and AccountsOS (£20 a month AI tier) already sell AI-prepared accounts. The HMRC free CT600 closure on 31 March 2026 is a forcing function, but vendors have already moved. Closest to the studio's edge; revisit only with a bureau-side wedge (iXBRL tagging).
10. Planning application validation: Planning Portal Application Check is AI and free to applicants (https://www.planningportal.co.uk/services/help/faq/applications/planning-applications/what-is-application-check), Valon at Milton Keynes, AI validation listings on G-Cloud. No per-unit price.
11. Product-copy translation: dozens of Shopify AI translation apps from about $9-$29 a month (e.g. https://apps.shopify.com/lokalize). Commodity.
12. Tender and bid drafting: Tenderforge, Bidwin AI, WinaContract (£49-£349 a month, https://www.g2.com/products/winacontract/pricing); already in RANKING (sme-council-tender-drafting).
13. CIS monthly returns (The Accountancy £30 a month + £6 per sub, https://theaccountancy.co.uk/services/cis-returns): CIS Manager and Xero CIS filing exist; deterministic.
14. MCS heat pump design and heat loss: free MCS Heat Load Calculator and Heatpunk, paid autarc and Aireo with AI (https://www.autarc.energy/gb/knowledge/mcs-design-software-ai-features-6cuiz). No outsourced price found.
15. Tenancy deposit dispute packs: DepositPack already sells a tenant-side pack; schemes' dispute service is free (https://www.mydeposits.co.uk/content-hub/deposits-disputes-and-damages-guide/). No per-pack price found.
16. Cyber Essentials assistance (£750-£1,500 consultancy plus £300-£650 IASME fee, https://connection-technologies.co.uk/blog/cyber-essentials-cost-uk-2026): not a clean drop. No AI questionnaire tool was found in one search, but the NCSC announced free hands-on consultancy for small firms (https://www.ncsc.gov.uk/blogs/helping-small-businesses-with-free-hands-on-cyber-consultancy), a reported (unconfirmed) funding scheme of £80-£125 from 3 Nov 2026, and compliance platforms (Vanta-type, CyberSmart) were not checked. Left unwritten: a once-a-year job, with a free state substitute and unverified competition.
17. Domestic EPC write-up: Elmhurst RdSAP Go is about £1 a submission (vendor claim) and lodging needs an accredited assessor; AI role limited. Dropped on thin evidence.

Count: 17 dropped, 1 written (weak), 1 left unwritten for lack of checks (Cyber Essentials, counted in the 17).

## Lessons
- Per-unit bureau prices are low where software exists (£1-£5 a unit for tachograph and payroll) and unit prices that are high (£355-£450 minutes, £379-£649 accounts) belong to jobs where incumbents already sell AI or software to SMEs. No quadrant looked open.
- Where the unit price is public and the work is regulated, the output is usually computed in accredited software (SAP, MCS, EPC, CT600). AI only adds input extraction, which is a feature the software vendor can ship.
- Public per-unit prices for the bureau side are scarce: most search hits were consumer prices or vendor guides. Pay evidence needs a named bureau price page, not a guide.
- Liability sits with an accredited human in most of these jobs, which supports a "pre-fill and trace" product but caps price per unit.
- Search tools return low-trust generated sites; check domain identity before counting a price.

## Suggested cheap kill tests
- SAP: read Elmhurst and Stroma help and release notes for "import", "DXF", "PDF", "AI"; find two named assessors' price pages (not guides); run a 10-PDF extraction test of areas against hand measurement from public planning portals; confirm HEM start date for new builds.
- Accounts and CT600: look for iXBRL tagging bureaus (DataTracks and others) selling to accountants, and test whether tagging is still sold per filing with AI competitors.
- Cyber Essentials: check CyberSmart, Vanta UK pages and the 3 Nov 2026 funding scheme on gov.uk before any file.
- A different cut for the next round: look for jobs priced per unit by UK bureaus where the output is judgement and the input is an image or audio, not a document, since document-to-field extraction is closed.
