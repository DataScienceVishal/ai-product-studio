# Dental NHS contract delivery desk (Dentally marketplace add-on)

- slug: dental-nhs-contract-delivery-desk
- stage: G0
- market and segment: NHS-contracted general dental practices in England (owners and practice managers) on Dentally; later Software of Excellence and others
- one-line pitch: Each month reads the practice's Compass schedule and its own Dentally activity, explains every mismatch, forecasts year-end UDA, UOA and unscheduled-care delivery against the 2026/27 rules, and drafts the fix for each at-risk claim. It does not give clinical advice.

## Problem and who has it
NHS practices are paid against a contract and face clawback if delivery falls short (the NHSBSA page says year-end reconciliation is a contractual requirement). From 2026/27, providers with mandatory contracts of 100 UDAs or more must deliver 8.2% of contract value as unscheduled care, urgent care is paid per course rather than at 1.2 UDAs, and complex-care pathways are paid in instalments. Practice managers reconcile by hand: a Dentally community thread explains that Dentally's UDA report counts by completion date, while Compass shows what is scheduled to the financial year, so the two never agree without work. Rejected or unreturned claims need chasing.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.nhsbsa.nhs.uk/dental-provider-assurance/mid-year-and-year-end-reconciliation | 2026-11-24 | Year-end reconciliation is a contractual requirement; mid-year counts claims to 30 September; monthly schedules in Compass (search summary; page not fetched) |
| https://community.dentally.com/practice-management-58/nhs-uda-report-mismatch-418 | 2026-11-24 | Pain signal 1: practices see a mismatch between Dentally's UDA report and Compass (search summary of a user reply) |
| https://help.dentally.com/en/articles/8407876-nhs-ni-manually-reconcile-claims | 2026-11-24 | Pain signal 2: Dentally's own help tells NI practices to reconcile claims manually, because the amount allocated is never reflected in the claim |
| https://www.england.nhs.uk/long-read/nhs-dentistry-quality-payment-reforms-contractual-guidance/ | 2026-11-24 | Forcing function: 2026/27 package, 8.2% unscheduled care, new payment rules, with complex care, dentures and discretionary payments still to follow later in 2026 (search summary) |
| https://www.england.nhs.uk/primary-care/dentistry/dental-commissioning/dental-contract-reform/ | 2026-11-24 | The reform pages (search listing; details not read) |
| https://www.nhsbsa.nhs.uk/sites/default/files/2026-09/Guide%20for%20viewing%20contract%20reform%20changes%20activity%20information_0.pdf | 2026-11-24 | NHSBSA published a September 2026 guide on viewing reform activity, so the activity view is still changing (title only) |
| https://www.dentally.com/en-gb/integrations | 2026-11-24 | Fetched. Marketplace categories include Reporting, Workflows and Compliance and Payments and Finance; no UDA or NHS-contract app listed (only referral tools, My Practice Cloud analytics, AI phone agents) |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| NHSBSA eDEN dashboard and Compass (free) | free | Show delivery as a share of contract; no explanation of mismatch with the practice system and no forecast (NHSBSA eDEN guidance, 2019 document) |
| Dentally NHS reporting (https://www.dentally.com/en-gb/solutions/nhs) | bundled | Marketing says real-time contract reporting and claim resubmission; not shown to explain Compass mismatches or forecast the 8.2% duty. Page not fetched; check |
| CareStack NHS reporting (https://carestack.com/en-GB/dental-software/features/nhs-reporting) | not shown | Advertises claim-level UDA reconciliation; a rival practice system, not a Dentally add-on |
| Dental accountant, Zmartly | from £129 a month (financial statements and corporation tax only) | Proxy only: it is not contract management. No published price for an NHS contract consultant found |

## Why AI is essential (and the moat)
The core forecast is arithmetic (low AI). AI earns its place in three parts: reading Compass pay-statement PDFs and rejection reasons, matching mismatched lines to causes (completion-date versus scheduled-date, band changes, carry-forward), and drafting the practice's action list in plain English. The moat is the NHS rules knowledge and the regulatory churn: the rules for complex care, dentures and discretionary payments are still to be published, which vendors must keep re-implementing. Honest doubt: Dentally can add a reconciliation view.

## Rough build plan and Azure cost
- Demo from synthetic data: a generated Compass-style schedule and Dentally-style claims export built from the public Guide to monthly pay statements (https://cms.nhsbsa.nhs.uk/sites/default/files/2024-10/Guide%20to%20monthly%20pay%20statements.pdf). No patient data is needed: only claim counts, bands and dates.
- Data route: Dentally API is restricted to approved partners (https://help.dentally.com/en/articles/15956843-dentally-partner-api-faq-s). Application is free to submit but needs Vishal's OK; a read-only practice-issued token is a workaround from a 2025 thread, unconfirmed. Fallback: CSV and PDF upload, which also works for any practice system and avoids dependence on the API.
- Compass has no public API; practices download files. No scraping.
- Azure: small (Container Apps, Postgres, one LLM call per document). Estimated under £30 a month for a pilot; estimate, not measured.

## Risks, and what would prove this wrong
- Pay: no public price for the job; practices may see it as a part of the manager's day. Kill test: no practice-manager job advert or consultancy page that prices contract monitoring.
- Reach: Dentally says only verified partners may list. Marketplace listing is a hurdle, not a blocker. Dentally's UK practice count not checked.
- Competition: Dentally native reporting not verified; BSA or Dentally may add a forecast.
- Scope: stay on administration. No treatment, coding or clinical recommendation (medical-advice red line).
- Data: files contain patient identifiers; the product should read only counts and claim references, and the design must prove it.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 13 | 5 | 5 | 5 | 9 | 3 | 7 | **47** |

### Validator checks (T-47, 2026-11-24, all accessed 2026-11-24)
| Check | Source | Finding |
|---|---|---|
| Dentally native NHS reporting (fetched) | https://www.dentally.com/en-gb/solutions/nhs | "track UDAs, and stay on top of contracts", "real-time contract reporting", "from UDA progress to contract tracking and outstanding claims". No Compass, forecast or unscheduled-care feature on the page |
| Dentally is building the core (fetched) | https://community.dentally.com/practice-management-58/calling-nhs-practices-help-shape-new-contract-performance-reporting-719 | 27 May 2026, a Dentally product designer: building "clear reporting on how you're tracking against your NHS contract" (ACV/UDA targets, per-clinician, "where the gaps are"), starting with Wales; recruiting practices for design calls. No date |
| Pain is real but is a platform-feature request (fetched) | https://community.dentally.com/practice-management-58/urgent-improvement-needed-uda-tracking-reporting-564 | 19 Jan 2026: "Robust UDA tracking is not a nice to have"; a "major downgrade from EXACT". 70 views, 1 like. Dentally staff: logged on the internal board |
| Rival PMS already ship it (fetched) | https://carestack.com/en-GB/dental-software/features/nhs-reporting | "Track confirmed versus claimed UDAs", "Spot completed NHS treatments awaiting submission", "Support reporting across Unscheduled Care, updated treatment mappings, fee changes", daily action lists. No forecast |
| Forecasting already exists (search summary; SoE help page returned 403) | https://help.softwareofexcellence.com/hc/en-gb/articles/4991378416788-NHS-UDA-Manager | EXACT has an NHS UDA Manager (achieved versus confirmed gap flags rejected claims) and a Predictive UDA Manager. Dentally users ask for an "EXACT-style" tracker, so it is the market's reference feature |
| Free official monitoring (search summary) | https://www.nhsbsa.nhs.uk/sites/default/files/2026-09/Guide%20for%20viewing%20contract%20reform%20changes%20activity%20information_0.pdf | NHSBSA names daily contract activity data in Compass as the monitoring source; eDEN has a contract performance summary dashboard |
| Pay | search "dental practice NHS contract management consultancy UDA monitoring fee" | No published price for contract monitoring found. Only proxies: Zmartly accounting £129 to £250 a month (not this job); the BDA advises members on clawback as part of membership |
| API route (fetched) | https://help.dentally.com/en/articles/15956843-dentally-partner-api-faq-s | NextGen API: apply to be a partner, sandbox demo video, then production credentials. "You'll authenticate directly with Dentally instead of practices creating and managing API tokens", so the practice-token workaround is gone. No fee stated |
| Off-limits check | CLAUDE.md section 5 | As scoped (counts, claim references, contract arithmetic) this is contract admin, not medical advice. Not a red flag. Exports carry patient identifiers, so Risk is 7 |

### Score reasons
- Pain 13: clawback is real money, and forum posts show practice managers piecing figures together by hand. But the evidence is feature requests to the platform (1 like, 70 views), and NHSBSA gives a free daily view.
- Pay 5: no price for the job anywhere. The value sits inside PMS subscriptions (Dentally, EXACT, CareStack) and BDA membership.
- AI 5: the core (delivery against target, forecast, 8.2% share) is arithmetic. Reading pay statements and drafting the action list is thin and quick to copy.
- Reach 5: the Dentally marketplace requires partner approval (needs Vishal's OK) and a sandbox demo. Practice managers can be found through BDA and practice-manager groups. Dentally's share of NHS contracts was not counted.
- Build 9: synthetic Compass-style data is possible. But the Compass views changed in September 2026, more rules are still to come, and file upload means manual exports each month.
- Competition 3: the platform owner is building the core with its users; EXACT already forecasts; CareStack already covers 2026 unscheduled care and claim exceptions.
- Risk 7: health-adjacent records with patient identifiers in the exports, though admin-only in scope.

## Verdict: KILL (first attempt, ceiling about 58)
The gap the scout found ("no UDA app on the Dentally marketplace") exists because the platform owner treats contract tracking as its own core feature. Dentally's product team has been designing contract-performance reporting with NHS practices since May 2026. EXACT already sells a predictive UDA manager, and CareStack already reports 2026 unscheduled care and claim exceptions. NHSBSA gives daily activity data in Compass and a performance dashboard in eDEN for free. What would be left for an add-on is arithmetic plus a drafted action list, with no public price, behind a partner API the studio needs approval to use. Even with a price found, Competition and AI cap it below 70.

**Lessons:** an empty marketplace category next to a forum feature request usually means the platform plans to build it, so search the vendor's community for "help shape" or "we're building" posts before writing the G0 file. Check rival PMS pages for the feature too: in a vertical market, the reference feature (EXACT's UDA Manager) sets what buyers expect to get bundled.

**What would revive it:** Dentally publicly declining to build forecasting or unscheduled-care tracking, plus a published price that practices or dental groups pay for contract monitoring (for example a consultancy retainer). Or a multi-PMS dental group segment (corporates running EXACT and Dentally side by side) with evidence that it pays for consolidated NHS reporting.

## Gate log
- 2026-11-24 round 10 scout (T-47): written at G0. Scores left for the validator.
- 2026-11-24 validator (T-47): 47/100, KILL. Dentally is building contract-performance reporting (community post, 27 May 2026); EXACT forecasts; CareStack covers 2026 unscheduled care; no price for the job. Move to `state/ideas/killed/`.
