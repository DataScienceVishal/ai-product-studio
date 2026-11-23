# Agency WhatsApp timesheet desk

- slug: agency-whatsapp-timesheet-desk
- stage: G0
- market and segment: UK small temporary staffing agencies and contract cleaning or hospitality labour suppliers (5 to 50 office staff, hundreds of temps) whose workers send timesheets as WhatsApp photos and whose payroll runs in a desktop product (for example Sage payroll)
- one-line pitch: Read each WhatsApp timesheet photo, match it to the booking and the client's approved hours, chase gaps in the same chat, and produce a payroll-ready and invoice-ready hours file for the payroll clerk to approve.

## Problem and who has it

Temps often lack the patience or phone setup for an agency app, so they send a photo of a paper timesheet. Office staff chase missing ones, correct errors, and re-key hours into payroll and client invoices. Errors mean underpaying workers, which agencies must avoid under GOV.UK rules, or billing clients wrongly.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.logezy.com/product/timesheets/ | 2026-11-23 | Logezy (competitor) describes agencies "still collecting timesheets via WhatsApp photos, email attachments, or paper forms" and the pain of chasing, correcting and re-keying into payroll. Its own fix is a candidate app with e-signature. Page names no payroll system, no price, no AI, no WhatsApp submission. |
| https://www.findapprenticeship.service.gov.uk/apprenticeship/VAC2000048244 | 2026-11-23 | Apprentice Timesheet and Compliance Administrator, recruitment operations: a role that exists for this work. |
| https://findajob.dwp.gov.uk/details/17983432 and https://www.robertwalters.co.uk/accountancyfinance/jobs/accountant/1897918-payroll-administrator.html | 2026-11-23 | Payroll administrator roles surfaced by search (Proactive Personnel Telford £26,000 to £27,500, posted 11 May 2026; Robert Half payroll clerk £32,000 to £37,000 using Sage payroll and MSP timesheet platforms). Salaries as reported by search summary; confirm on pages. |
| https://jobs.co.uk/job/3-month-temp-timesheet-administrator-in-guildford-office-angels--630b07f7-0184-4c26-b1d9-8e6c374a5871 | 2026-11-23 | Temp Timesheet Administrator, £13 to £14 an hour, closed July 2026. Staff-cost signal. |
| https://www.gov.uk/employment-agencies-and-businesses/agency-workers | 2026-11-23 | Agencies must make sure workers are paid for all the work they do. Source of risk if hours are mis-keyed. |

Pain signals: one vendor description plus job ads; no independent measure of how many agencies collect by WhatsApp. G1 needs a source for how common this is.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Logezy timesheets (page above) | Not published; demo and trial | Needs candidate app adoption; page shows no WhatsApp intake or photo reading. |
| Zoho Workerly photo logging (https://help.zoho.com/portal/en/kb/workerly/timesheets/photo-logging-for-temps/articles/zoho-workerly-photo-logging) | Not captured | Photos are taken at check-in and compared with a profile photo; no timesheet OCR, no WhatsApp. Different feature, uses face matching. |
| Vincere online timesheets (https://www.vincere.io/recruitment-timesheets) | Not captured | Page returned 403; not verified. Search summary says reminders and push notifications for online timesheets. |
| Timesheet or payroll administrator | £26k to £37k a year, or £13 to £14 an hour (ads above) | The cost being cut. |

Gap claimed: no-app intake via WhatsApp, matching to bookings and client approvals, output into a desktop payroll. Not month-proof: Logezy could add a WhatsApp number quickly; the barrier is per-agency payroll and booking exports and agency trust.

## Why AI is essential (and the moat)

Handwritten hours, breaks and client signatures on photos, matched against messy booking records with name variants. AI reads and proposes; the payroll clerk approves. Moat: exceptions model and payroll adapters; modest.

## Rough build plan and Azure cost

- Intake adapter: mock mode uses a folder of images; live needs WhatsApp Business Platform (paid, approval) with opt-in and a privacy notice for workers.
- Reader, matcher to a bookings CSV, auto-reply for missing or unreadable sheets (templated), approval screen.
- Output: hours CSV for payroll import and client invoice lines.
- Azure: Container Apps scale-to-zero, blob with short retention, Postgres burstable; under about £25 a month.
- Demo with synthetic data: 300 synthetic timesheet images with varied handwriting, plus bookings CSV and expected payroll file. Measure hours accuracy and exception rate.

## Risks, and what would prove this wrong

- Worker personal data (names, hours, sometimes ID) at scale; employment data; UK GDPR processor terms; retention limits. Risk score will be lower.
- Hours errors affect pay; human approval is mandatory and liability stays with the agency.
- Meta's WhatsApp rules for AI chatbots must be checked before design is fixed.
- Wrong if: Logezy, Vincere or Zoho show WhatsApp or photo-OCR timesheet capture on their own pages, or agencies say timesheet chasing is a small fraction of payroll work.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| pending | pending | pending | pending | pending | pending | pending | pending |

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half). Scout's view: second weakest on competition and risk; keep only if the validator finds how common WhatsApp collection is.
