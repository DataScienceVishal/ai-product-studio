# Remittance cash allocator for Sage and QuickBooks users

- slug: sage-remittance-cash-allocator
- stage: killed (G0, 2026-11-24, 57)
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
| 13 | 10 | 8 | 6 | 8 | 3 | 9 | 57 |

## Validator, round 8 (T-44, 2026-11-24)

**Verdict: KILL at G0 to G1 (57; ceiling about 62).**

The scout's main gap is wrong. RemitClear's own site says it supports Xero, QuickBooks Online and Sage Accounting (cloud) through OAuth2, so it covers two of the three ledgers this idea was meant to add. RemitClear Ltd is registered in England and Wales, so it is a UK competitor going after the same buyers, not a US firm that might not bother with the UK. The only gap left is Sage 50 and Sage 200 desktop. Sage 50 add-ons already import receipts allocated to invoices (PostTrans Extras Module, Adept Tools, Excel2Sage), so the posting step is a commodity. The one piece left that needs AI is reading the remittance, and that is exactly what RemitClear, Remittance Go and the enterprise tools already sell.

Evidence (accessed 2026-11-24):
- https://www.remitclear.com/ (fetched): "Xero, QuickBooks Online, and Sage Accounting", "Priced on remittances and invoice lines, not per seat", quote after a demo; RemitClear Ltd, London, England and Wales.
- https://www.capterra.co.uk/software/1203490/RemitClear (search summary): flat-rate subscription per connected entity, price on request.
- https://apps.xero.com/au/function/accountant-tools-extras/app/remittance-go (search summary): Remittance Go, a second Xero remittance line-matcher with human review.
- https://www.posttrans.co.uk/Sage-50/Transaction-Data/Sales-Receipts (search summary): Sage 50 receipt import with automatic allocation against outstanding invoices (Extras Module).
- https://uk-marketplace.sage.com/en-gb/apps/84377/adept-tools-for-sage-50 (search summary): allocates payments, or imports them to match against outstanding invoices.
- https://communityhub.sage.com/gb/sage-200/f/general-discussion/124838/... (fetched): a Sage 200 user asks for remittance CSV import with automatic allocation. The post is over seven years old and the only reply is "one for the ideas hub". Real pain, but old.
- https://communityhub.sage.com/gb/sage-50-accounts/f/general-discussion-uk/226084/treatment-allocation-of-payments (search summary): a user allocates a £100k remittance across 200 invoices by hand in Sage 50. This is a good pain signal.
- Sage AR Automation (https://www.sage.com/en-us/products/sage-ar-automation/, search summary): US$10k to $25k a year, mid-market and US. That proves willingness to pay upmarket, not among UK SMEs on Sage 50.

How each score was reached:
- Pain 13: a salaried role is advertised at four employers, and there are three forum threads, two of them old. There is no time-per-remittance figure.
- Pay 10: the evidence is salaries, a quote-only competitor and an enterprise price. There is no SME price point.
- AI 8: AI is needed to read remittances, but incumbents already sell that.
- Reach 6: Sage 50 users can be found through the Sage marketplace and resellers, but the partner sector is unknown.
- Build 8: synthetic data is enough for the demo. A live Sage 50 or 200 posting needs a paid SDK, a connector or a licence, which is the same problem wholesale-email-order-entry-sage had.
- Competition 3: there is a UK AI incumbent on cloud ledgers, and desktop allocation importers already exist.
- Risk 9: business finance data only.

**Near-duplicate:** yes, of wholesale-email-order-entry-sage (REVISE 55). Both are "Sage 50/200 desktop AI document intake" ideas with the same buyer, the same blocker on a Sage test route, and the same risk that a cloud AI vendor adds desktop Sage. If that idea is ever revived, record remittance reading as a possible second module of it. Do not run a separate G1 attempt.

**What would revive it:** public evidence that RemitClear and its peers refuse desktop Sage (for example, a help-page statement); a count of UK Sage 50/200 firms in trade distribution that receive more than 50 multi-invoice remittances a month; and a free or cheap Sage 50/200 test route.

**Lessons:**
- Fetch the competitor's own homepage, not only its marketplace listing. RemitClear's Xero listing hid the QuickBooks and Sage support.
- For desktop ledgers, look up the existing CSV and import add-ons (PostTrans, Adept, Excel2Sage) first. They set the price of the non-AI half of the product.

## Gate log
- 2026-11-24 T-44 scout round 8: G0 written. Pre-write search found RemitClear (Xero); survives only on the Sage and QuickBooks channel. Biggest doubt: Competition.
- 2026-11-24 | validator | G0→G1 | KILL 57 | RemitClear (UK) already serves Xero, QuickBooks Online and Sage Accounting according to its own site, and Sage 50 receipt-allocation importers (PostTrans, Adept, Excel2Sage) already exist, so only desktop Sage is left as a gap. Near-duplicate of wholesale-email-order-entry-sage. The file should move to `killed/` (git mv by the lead).
