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

## Second pass (bureau-side)

Brief: sell to the bureau itself (AI workbench; bureau keeps client and liability). Time about 20 minutes, 22 searches and 8 page fetches on 2026-11-24. Evidence is mostly search summaries except where "fetched" is stated. No prompt-injection attempts seen. Several hits were pages.dev sites (low trust, noted).

### Written (1 file, G0, scores blank)
| Slug | Pitch | Per-unit prices (own pages) | Count | Independent pain | Why an incumbent can't trivially follow | Biggest doubt |
|---|---|---|---|---|---|---|
| uk-cosmetic-cpsr-assessor-workbench | Assessor bureau workbench drafting CPSR Parts A and B from formulation and supplier documents | Euverify £250 / £370 / £465 + VAT by ingredient count (https://euverify.com/cpsr/, fetched); Oxford Biosciences £220 up to 20 ingredients, "from £70" (https://oxbio-site.pages.dev/regulatory-compliance/uk, fetched) | 24,112 UK Responsible Persons, 861,686 notifications (https://www.gov.uk/government/news/new-data-on-uk-cosmetic-product-safety-notifications, fetched); number of assessor bureaus NOT found | Nov 2026 parliamentary committee report on beauty regulation (https://www.itv.com/news/2026-11-03/hair-and-beauty-products-less-regulated-than-ballpoint-pens-report, secondary) | Assessor sign-off liability stays with the bureau; brand-side vendors won't sign | OrAIsi (https://oraisi-website.pages.dev/en/index.html) already sells an AI PIF/CPSR platform to assessors (EU focus, no UK mention); price race to £70; arithmetic is deterministic; no bureau count |

Weak survivor. Not written: leasehold information packs (below).

### Dropped at the kill test (bureau type, evidence)
1. Bookkeeping and VAT-return bureaus: Combinely (VAT return checks, Burgess Hodgson 75% claim), Dext AI Assist, Acxite (https://www.accountingweb.co.uk/node/227017, search 2026-11-24).
2. Personal tax return outsourcing: QX TaxReady already runs AI plus human review at fixed per-return prices for over 500 firms (https://qxaccounting.com/uk/tax-outsourcing-support). The bureaus are building their own AI.
3. R&D tax claim preparers: SmartClaim, WhisperClaims, Boast.AI, Thomson Reuters Neo.Tax AI (https://www.accountingweb.co.uk/node/230372; G2 Swanson Reed TaxTrex https://www.g2.com/products/swanson-reed-specialist-r-d-advisors).
4. Conveyancing personal-search bureaus: Search Acumen REI (LLM for CON29 extraction, https://www.legalfutures.co.uk/associate-news/1-in-10-of-uks-top-200-law-firms-using-ai-to-improve-accuracy-and-insight-into-con29-searches) and SearchFlow AI.
5. Certified translation agencies: £18-£80 a page on agency pages (https://translayte.com/blog/cost-of-translation-uk); post-editing tools are a mature category, and a certified sign-off is by the translator. Not checked in depth; dropped on reasoning.
6. Grant-writing bureaus: Plinth AI Grant Writer (£150 a month, https://blog.plinth.org.uk/an-update-on-no-win-no-fee/), SwiftBid (from £149 an application, https://swiftbid.pages.dev/grant-writing; low-trust domain), ZenGrants on Capterra UK (https://www.capterra.co.uk/software/1112343/ZenGrants).
7. Surveyor and asbestos report-writing bureaus: GoReport from £149 a user a month (https://goreport.com/how-one-london-practice-reduced-report-writing-time-by-50/), Blooming Surveys pay-per-report; no outsourced per-report price exists, only bundled survey prices.
8. Biodiversity net gain assessors: Gentian True Sight, AiDash BNGAI inside LandTech (https://land.tech/blog/smarter-faster-biodiversity-planning-with-bngai-by-aidash-and-landtech); no consultant per-site price found.
9. HACCP and food-safety documentation: Fiverr gigs at $50-$400 and FoodReady AI (https://sourceforge.net/software/product/Beacon-by-SystemPath/ for context); no UK bureau price page found.
10. Safety data sheet authoring: SDS Studio €59 an SDS pay-as-you-go, ULGHS $275, SDS Manager UK (https://sdsmanager.com/uk/sds-authoring); cheaper than any bureau and already software.
11. DSAR and redaction bureaus: DPAS £1.50-£2.50 a page, Penningtons AI-assisted DSAR service, Smartbox.ai about £17 a case (https://www.penningtonslaw.com/sector/technology/dsar-support-service/; Smartbox claim via Microsoft blog https://www.microsoft.com/en-gb/industry/blog/?p=70397).
12. Planning-application agents: RICS reports generative AI already used for planning statements and heritage assessments; PAI by Studio Bark; Government PlanAssist on the council side (https://ww3.rics.org/uk/en/journals/land-journal/ai-planning-officers-development.html). No agent price page found.
13. Payroll bureau query desks: Sage Copilot, PayFit Copilot, Ask The Payroll Centre for bureau operators (https://thepayrollcentre.co.uk/asktpc/).
14. Motor repair-estimate audit bureaus: no UK per-claim bureau price or AI vendor found; only a £125 + VAT fraud desk review (DWF); insurance-adjacent, so left (see off-limits note).
15. Recruitment RPO, customs brokerage, export documentation, EPC assessors, R&D-adjacent ISO 9001 consultancies: not searched this pass; customs, origin, EPC and SAP are covered in rounds 12 and 13; RPO and ISO dropped on reasoning only (large AI-native field, unverified).

### Near-miss, not written: leasehold information packs (LPE1)
- Per-unit prices: £125-£500 in a conveyancer's fee schedule; Norwich £150 inc VAT, Southwark £269 (council pages in search results: https://norwich.gov.uk/info/20047/leaseholders/1214/buying_and_selling_the_property/5, https://www.southwark.gov.uk/preassignmentinformation; not fetched).
- Forcing function is unproven: Service and Administration Charges (England) Regulations 2026 made 10 Nov 2026 with first duties from 1 April 2027 and 1 November 2027 (https://www.propertymark.co.uk/resource/key-dates-confirmed-for-leasehold-service-charge-reforms.html, fetched), but the £200 + VAT cap and 15-working-day pack deadline appear only in a Dwellant blog and solicitor commentary; the Propertymark page and the government response page (fetched) do not mention it.
- No tool found that generates LPE1 packs (August page, fetched, says no), but block-management suites (Inox, MRI, Re-Leased) can add it, packs are produced in-house by managing agents (not a bureau), and the buyer count is unknown. Revisit if the pack cap gets a made instrument.

### Lessons for the next scout
- The bureaus themselves are the ones already buying or building AI (QX, Penningtons, DPAS, Plinth). Where a bureau price page does not mention AI, an AI vendor usually sells to the same bureau already (OrAIsi, Combinely, SmartClaim).
- Bureau-side evidence is thin: no register of assessors, no bureau counts and few price pages. Counting bureaus is the step that failed most often; check CTPA, CIEEM, ARMA and CIAT membership lists first.
- Prices that bureaus publish are collapsing (£70 CPSR, £1.50 a page redaction), which caps what a bureau pays a workbench.
