# Haulier WhatsApp POD matcher

- slug: haulier-whatsapp-pod-matcher
- stage: G0
- market and segment: UK small hauliers, pallet and general freight subcontractors, and courier fleets (5 to 50 vehicles) that invoice from Sage 50 or spreadsheets and have no transport management system (TMS)
- one-line pitch: Drivers keep photographing proof-of-delivery notes into WhatsApp; the AI reads each photo, matches it to the right job and invoice, flags missing or unsigned PODs, and hands the office a ready-to-send invoice pack.

## Problem and who has it

Customers often will not pay a haulage invoice without a signed POD. Drivers send photos (or paper later) and the office chases, renames, matches to jobs and attaches to invoices. Dedicated haulage systems solve this with their own driver app and TMS, which a small operator on Sage 50 and WhatsApp has not adopted.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://jobalert.ie/job/pod-administrator-dfds-uk-ireland | 2026-11-23 | A POD Administrator ad (employer shown as McBurney Transport Group in the search summary; confirm on the page) whose duties are chasing outstanding PODs from drivers, depots and subcontractors and attaching them to invoices. Job-ad signal for the manual task. |
| https://findajob.dwp.gov.uk/details/14360524 | 2026-11-23 | Sales ledger role requiring Sage 50, £36,000 to £40,000 (posted April 2024 per summary; dated). Staff cost and Sage 50 dependence. |
| Suffolk haulage accounts assistant ad requiring Sage 50 and freight invoicing (seen in a search summary; URL not captured, re-find) | 2026-11-23 | Haulage firms still hire for Sage 50 freight invoicing. Unverified URL. |
| https://peakflo.co/blog/proof-of-delivery-capture-billing-evidence-chain | 2026-11-23 | Blog: missing PODs delay billing more than late deliveries. Vendor blog; weak. |
| https://www.softomatesolutions.com/blog/ai-process-automation-uk-logistics-companies-2026/ | 2026-11-23 | Services-firm blog describing the manual loop of reconciling the POD against the booking record. Weak. |
| https://www.mandata.co.uk/proof-of-delivery-invoicing-accounts | 2026-11-23 | Mandata testimonial (vendor) that invoicing straight after POD improved cash flow by four to five days. Gives a value anchor for faster invoicing, not independent. |

Pain signals: three, all weak or vendor. G1 needs an independent source on POD disputes or days-to-invoice.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Mandata TMS plus Manifests app (https://www.mandata.co.uk/proof-of-delivery-invoicing-accounts) | Not published ("flexible pricing") | Driver app syncs POD to its own TMS; page does not mention WhatsApp; Sage not named (a Xero logo appears). Requires adopting the TMS. |
| Klippa POD OCR (https://www.klippa.com/en/ocr/logistics-documents/proofs-of-delivery/) and V7 Go POD verification (https://www.v7labs.com/automations/proof-of-delivery-verification) | Not published | Developer or enterprise tools; no WhatsApp intake or Sage 50 hand-off packaged for a small haulier. Pages not read in depth. |
| Back-office clerk | £28k to £40k a year per the ads above | The cost being cut. |

Gap claimed: WhatsApp intake plus matching to Sage 50 or spreadsheet job lists, for operators without a TMS. Weakest point: an OCR vendor or Mandata could add a WhatsApp intake easily; not a gap a competitor cannot close in a month. The only durable barrier is the per-firm Sage 50 and spreadsheet plumbing.

## Why AI is essential (and the moat)

Photos are skewed, handwritten, multi-page and signed in varying ways. Matching needs fuzzy references (customer ref, consignee, date) against messy job lists, and judging whether a signature, name and date are present. A human reviews every exception. The moat is thin: adapters and exception rules per firm.

## Rough build plan and Azure cost

- WhatsApp intake behind an adapter: mock mode reads a folder of images; live mode needs WhatsApp Business Platform (paid, approval) or drivers email to a shared mailbox as fallback.
- Document reader (vision model) to fields; matcher to a job list CSV exported from Sage 50 or Excel; exception queue.
- Output: PDF pack per invoice, plus a Sage 50 import-ready CSV for sales invoices (route to be validated).
- Azure: Container Apps scale-to-zero, blob, small Postgres; under about £25 a month for a demo.
- Demo with synthetic data: generate 200 synthetic POD images (varied handwriting fonts, rotations, missing signatures) and a synthetic job list; measure match rate and exception precision.

## Risks, and what would prove this wrong

- Weak differentiation and low switching cost; WhatsApp terms for AI bots need checking.
- Drivers send photos of poor quality; legal weight of a WhatsApp photo POD in disputes is untested.
- Small hauliers may only need a free workaround.
- Wrong if: a haulier-facing WhatsApp POD feature appears on Mandata, Klippa or a TMS vendor's own page, or the benchmark match rate is poor.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| pending | pending | pending | pending | pending | pending | pending | pending |

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half). Scout's own view: weakest of the five on competition; keep only if the validator finds a stronger pain source.
