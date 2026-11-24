# Accountancy HMRC post and notice triage (Xero Practice Manager add-on)

- slug: accountancy-hmrc-post-triage
- stage: G0
- market and segment: small UK accountancy and bookkeeping practices (2 to 15 staff) that use Xero Practice Manager or Xero HQ
- one-line pitch: Reads the HMRC letters, emails and agent-services notices that reach a practice, identifies the client and the tax, extracts the deadline and the action, flags nudge letters versus formal enquiries, and files a draft task and reply for the manager to approve.

## Problem and who has it
HMRC sends about 130m letters a year, mostly automated and templated. Practices receive many each day, and an AccountingWEB commenter put it at about 20 letters a day for a practice (one view, not measured). HMRC has increased one-to-many nudge letters, some sent to agents, which are not formal s9A enquiries and need a different response. Missing a deadline in a letter costs the client a penalty and costs the practice a complaint. Someone in the practice reads, matches to the client, logs and allocates each one every day.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.accountingweb.co.uk/node/215297 | 2026-11-24 | Pain signal 1: commenter says accountants might get 20 such letters a day and must check them manually (search summary; single view) |
| https://www.cipp.org.uk/resourceLibrary/nudge-tactics-the-rise-of-hmrc-s.html | 2026-11-24 | Pain signal 2: rise of HMRC one-to-many nudge letters, not formal enquiries (search summary) |
| https://www.accountingweb.co.uk/community/industry-insights/hmrc-assist-prompts-are-landing-is-your-ai-catching-errors-before-the | 2026-11-24 | Pain signal 3: practitioner discussion of HMRC prompts landing on practices (title only; read before G1) |
| https://www.icas.com/news-insights-events/news/tax/hmrc-s-plans-for-ai | 2026-11-24 | HMRC will use AI to draft letters and in compliance work, so volume and variety of letters is likely to rise (search summary) |
| https://www.gov.uk/algorithmic-transparency-records/hmt-correspondence-triage-automation-tool | 2026-11-24 | Precedent: a government department uses AI to summarise, allocate and identify standard replies to post. Shows feasibility, not a market |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| A staff member or the manager opening and logging post | Salary only; a modelled cost, no public price for the job | This is the Pay problem: no outsourced fee found |
| Practice management tools (Xero Practice Manager, Karbon, TaxDome, Senta) | Not checked | One search found nothing on HMRC correspondence handling in Xero Practice Manager or Karbon. Not proof. Check each product's help pages for email triage and AI features before G1 |
| Mail-scanning services | Not checked | They digitise; they do not read the content (unverified) |

## Why AI is essential (and the moat)
Letters are free text and templates with varied layouts; the job is to read, classify (nudge, penalty, enquiry, coding notice, SA reminder), match to the client and tax reference, extract dates, and draft the right reply. That is judgement over unstructured text, not a deterministic rule. Moat is thin on the reading alone (practice systems can add it); the stronger part is the HMRC knowledge: what each notice type needs, response windows, and the agent-authorisation check. Liability: the practice approves every action.

## Rough build plan and Azure cost
- Demo with synthetic letters: HMRC letter templates and public examples from gov.uk guidance, plus invented clients. No real taxpayer data.
- Data route: Xero Practice Manager API (public developer docs at developer.xero.com; check the app-partner programme and any certification fee, a hurdle not a blocker). Input is a forwarded mailbox or a scanned-PDF folder, so the reading works without the API.
- Azure: one LLM vision call per page; estimate under £30 a month for a pilot (not measured).

## Risks, and what would prove this wrong
- Personal data: letters name individuals. The product must process within the practice's tenancy; this is a Risk-score issue.
- Pay: no public number for the job. A staff-time estimate will have to be marked as such.
- Competition: practice-management vendors, Dext and Karbon may add letter reading; unverified either way. Kill test: Xero Practice Manager, Karbon, TaxDome, Senta and Dext help pages and a "HMRC letters AI" search.
- Reach: Xero App Store certification and listing; Xero's partner programme terms not read.
- Volume: the 20-a-day figure is one commenter; kill test is a real count from a trade-body survey.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-24 round 10 scout (T-47): written at G0. Competitor check was one search only; scores left for the validator.
