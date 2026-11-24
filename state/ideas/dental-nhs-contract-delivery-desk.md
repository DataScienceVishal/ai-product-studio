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
| | | | | | | | |

## Gate log
- 2026-11-24 round 10 scout (T-47): written at G0. Scores left for the validator.
