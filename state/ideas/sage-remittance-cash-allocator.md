# Remittance cash allocator for Sage and QuickBooks users

- slug: sage-remittance-cash-allocator
- stage: G0
- market and segment: UK wholesalers, distributors and contractors with 10 to 100 staff that invoice trade customers and are paid by multi-invoice bank transfers with a remittance advice (PDF, Excel, email), and that keep their ledger in Sage 50, Sage 200 or QuickBooks (not Xero)
- one-line pitch: Reads each customer remittance advice, matches every line to open invoices (short-pays, credit notes, discounts, one payment across dozens of invoices) and produces an allocation file for the Sage or QuickBooks ledger, with a review screen and a log of every exception.

## Problem and who has it
Sales-ledger staff open each remittance, find the bank receipt, then allocate it invoice by invoice. Large retail and trade customers pay in lump sums with a remittance listing 20 to 200 invoices, often with deductions that do not match the ledger. The role is a clearly costed job: "cash allocation clerk" posts at roughly £22k to £27k.

Starting search order for this round: the job first (a priced staff role), then the software. The software check found a close product, which is why the idea is weak on Competition (see below).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.robertwalters.co.uk/accountancyfinance/jobs/accountsreceivablecreditcontrol/1879682-cash-allocation-clerk.html (search summary) | 2026-11-24 | Cash allocation clerk, Leicestershire, up to £27,000, posted March 2026 |
| https://www.roberthalf.com/gb/en/job/datchet-berkshire/cash-allocation-administrator/06660-0013323895-uken (search summary) | 2026-11-24 | Cash allocation administrator, £25,000 to £26,000 |
| https://careers.rentokil-initial.com/job/cash-allocation-administrator-in-dudley-england-united-kingdom-jid-31361 (search summary) | 2026-11-24 | Basic £23,992, OTE £25,432: a shared-service team does this job full time |
| https://findajob.dwp.gov.uk/details/17048192 (search summary) | 2026-11-24 | Cash allocation post at £26,000 |
| https://apps.xero.com/uk/app/remitclear (fetched) | 2026-11-24 | RemitClear reads PDF, Word, Excel, CSV and forwarded-email remittances and posts to Xero. Only Xero is named; no price shown, "fixed monthly quote" on volume, demo required |
| https://www.sage.com/en-gb/products/sage-50-accounts/features/invoice-payments/ and .../bank-feeds/ (search summary only, not fetched) | 2026-11-24 | Sage 50 advertises matching payments to invoices and bank-feed matching; neither snippet mentions remittance advice |
| https://communityhub.sage.com/gb/sage-50-accounts/f/general-discussion-uk/214126/auto-upload-of-sales-receipts-from-bank-and-allocation-in-sales-ledger (search summary) | 2026-11-24 | A Sage user asks how to automate receipt allocation; a third-party add-on (Adept Tools) is suggested, not verified |

Pain signals so far: (1) a standing salaried role in several employers' job ads; (2) a Sage user forum thread asking for it; (3) at least one AI vendor (RemitClear) built a whole product on it for Xero. The third is a pain signal and a competitor at once. No customer-count or time-per-remittance figure was found; do not assume one.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| In-house cash allocation clerk | £22k to £27k a year (job ads above) | The cost to beat; many SMEs split it with other duties, so the true saving is a fraction of a salary |
| RemitClear (Xero app) | Not published; quote by volume | Xero only on its own page; the studio's gap is the ledger, and RemitClear can add Sage or QuickBooks |
| Sage 50 invoice payments and bank-feed matching | Included in Sage 50 | Matches bank lines, not a remittance listing (snippet only; confirm on Sage's help pages) |
| Adept Tools allocation add-on | Not checked | Unverified; may be a rules import, not document reading |
| Enterprise cash application (HighRadius, Billtrust, Rimilia) | Not checked; enterprise quotes | Out of SME reach (assumption, not verified) |
| Hand-off to credit control outsourcers | Not found | No public price found |

## Why AI is essential (and the moat)
Remittances arrive in dozens of customer-specific layouts, with scans, partial payments and "ours vs yours" invoice numbers. Rules cannot read these; a language and vision model can. The moat is thin: reading is a feature RemitClear already sells. Only the Sage and QuickBooks route (and the review and exception log) is the studio's gap, and that is a channel an incumbent can add in weeks. Honest rating: low.

## Rough build plan and Azure cost
Intake mailbox and upload, extraction with a vision-capable model, matching engine against a CSV export of open invoices (no live Sage API needed for the first version), review screen, and an allocation import file. Model cost per remittance is small (estimate; benchmark before G1). Azure about £30 to £60 a month at pilot scale (estimate, not costed).

Demo with synthetic data: generate 50 open invoices and 20 synthetic remittances in different layouts with planted short-pays. No paid service needed, so the whole demo survives without any live Sage connection.

## Risks, and what would prove this wrong
- RemitClear or Sage adds the other ledgers: the gap closes.
- Sage 50 desktop has no open API; import files only. The earlier wholesale-email-order idea hit the same Sage test-route problem.
- Cost to beat is only a fraction of a clerk's £25k, so a subscription of about £150 to £300 a month may be hard to justify (estimate).
- What would prove this wrong: a RemitClear quote under £100 a month plus a Sage import on its roadmap; or Sage's help pages showing remittance-based allocation.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Gate log
- 2026-11-24 T-44 scout round 8: G0 written. Pre-write search found RemitClear (Xero); survives only on the Sage and QuickBooks channel. Biggest doubt: Competition.
