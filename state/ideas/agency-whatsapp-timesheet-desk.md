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
| 11 | 10 | 7 | 7 | 10 | 3 | 5 | 53 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area. It isn't a hiring or assessment product, but its output sets people's pay.
- Synthetic data can credibly demo the value: 300 generated timesheet images with varied handwriting, a bookings CSV and the expected payroll file are enough to show hours accuracy and the exception rate. Real handwriting variety stays unproven until a pilot.
- The output route is free. Sage 50 Payroll imports timesheet payments from CSV (File > Data Import > Timesheet Payments), as TimeKeeper and Workforce document (https://help.timekeeper.co.uk/en/article/importing-into-sage50-payroll-1ni7a1f/ and https://help.workforce.com/en/articles/6992690-sage-50-uk, search summary only).
- Mock mode keeps the reading and matching but loses the in-chat chasing, which is half the pitch. Live chasing needs:
  - the WhatsApp Business Platform, which means Meta verification and approval;
  - worker opt-in;
  - paid utility templates. Since 1 October 2026, utility messages in an open window and service messages beyond 1,000 a month are charged (https://developers.facebook.com/docs/whatsapp/pricing).
- **WhatsApp rules.** The AI here is ancillary, so Meta's AI-provider ban doesn't apply.
  - Meta's terms (last modified 23 September 2026) bar using the chat data to train models except for the agency's "exclusive use" (https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform).
  - The Business Messaging Policy requires a human escalation path and opt-in (https://whatsappbusiness.com/policy/).

**Risk deductions (personal data at scale): 5/10.**
- -3 for personal data at scale: hundreds of temps' names, phone numbers, hours, pay, signatures and sometimes client sites.
- -2 because the output sets pay, and underpaying a worker is the agency's legal problem (https://www.gov.uk/employment-agencies-and-businesses/agency-workers).
- The design needs worker opt-in and a privacy notice, no ID images, short image retention and processor terms.
- Never add face matching. Zoho Workerly's photo check-in compares temps' photos with their profile photos (https://help.zoho.com/portal/en/kb/workerly/timesheets/photo-logging-for-temps/articles/zoho-workerly-photo-logging), and doing that would make this biometric data.

**Falsification findings** (all accessed 2026-11-23)
- **The dominant incumbent is building this exact product.** Bullhorn's Amplify Extract "scans timesheet images, emails, and text messages". It:
  - extracts hours, candidate, client, placement and week-ending date into a "Pending Review queue";
  - texts workers to submit their hours and accepts natural-language replies;
  - is "currently in early access" (https://www.bullhorn.com/blog/timesheet-automation/, 18 September 2026).

  Its channels are SMS and email, not WhatsApp, a gap Bullhorn could close within a month.
- **The build is routine.** Nexora Staffing (EITS) takes timesheets "from web, mobile, WhatsApp or email forward", reads handwriting and outputs payroll-ready data (https://eitserv.tech/en/staffing-timesheet-ai). Its country pages are Latin American, so it isn't a UK competitor.
- **The UK small-agency tools sell an app instead.**
  - Logezy confirms the pain: "If your agency is still collecting timesheets via WhatsApp photos, email attachments, or paper forms, you already know the problem". Its fix is a candidate app with e-signature and bulk approval. The page shows no AI, names no payroll system and gives no price (https://www.logezy.com/product/timesheets/).
  - TempBuddy uses app selfie clock-ins and e-signed timesheets (https://www.sourceforge.net/software/product/TempBuddy, search summary only).
  - Vincere's timesheets page still returns 403 (https://www.vincere.io/recruitment-timesheets), so it is unverified.
- **How common WhatsApp collection is remains unmeasured.** Every source that describes it is a vendor.
- **Reach:** REC has more than 3,000 member businesses and a public member directory listing their sectors (https://rec.uk.com/jobseekers, search summary only).

**What would change my mind (re-score on this evidence)**
1. An independent measure of how many small UK agencies collect timesheets as photos or WhatsApp messages: an REC or APSCo survey, or trade press with figures.
2. Amplify Extract's scope and price (does it take WhatsApp, and can small customers get it?), plus evidence that most small UK agencies don't use Bullhorn.
3. Logezy, Vincere and TempBuddy pages showing no photo reading and no WhatsApp intake.
4. A data-protection outline the security agent accepts before G2: opt-in, no ID images, image retention of 30 days or less, and a deletion path.

With all four I'd expect about 60.

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half). Scout's view: second weakest on competition and risk; keep only if the validator finds how common WhatsApp collection is.
- 2026-11-23 | validator | G0→G1 | REVISE 53 | The pain is real and weekly, but Bullhorn's Amplify Extract (early access, September 2026) already reads timesheet images and texts into a review queue and chases workers by text, Logezy could add WhatsApp within a month, mock mode loses the chasing that sells it, and hundreds of workers' pay data pull the risk score down to 5.
