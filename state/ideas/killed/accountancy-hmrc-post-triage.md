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
| 10 | 4 | 7 | 6 | 11 | 4 | 5 | **47** |

### Validator checks (T-47, 2026-11-24, all accessed 2026-11-24)
| Check | Source | Finding |
|---|---|---|
| Karbon AI triage (fetched) | https://karbonhq.com/en-GB/solution/email-management/ | Karbon AI "applies labels like High Priority... Client Query", can draft a reply or assign it, "attach it to a client or job, or start a new project", and AI suggests who to assign. Shared inbox costs "a small monthly fee per inbox". Attachment reading is not stated |
| Karbon Kai (search summary) | https://www.cpapracticeadvisor.com/2026/06/03/karbon-introduces-ai-coworker-kai/184484/ | June 2026 "AI coworker" with email triage that categorises, routes and surfaces critical items (early access) |
| TaxDome AI (search summary; page returned 403) | https://taxdome.com/en-int/taxdome-ai | AI names and files every client document on arrival; the Atlas agent follows up with approval. Sold as an add-on |
| Free HMRC letter reader (fetched) | https://www.taxfly.co.uk/hmrc-letter-decoder | Upload a photo or PDF and get a plain-English type (P800, SA250, SA326, P2, SA316, PA302, penalty) and next steps. Free and embeddable. Consumer-facing, but it is the core reading step |
| Channel is moving (fetched) | https://www.which.co.uk/news/article/hmrc-to-phase-out-paper-letters-heres-what-you-need-to-know-awwka3c23Mom | Dec 2025: from April 2026 HMRC is "digital by default". Letters go to the taxpayer's HMRC account with an email alert; the target is 90% digital by 2028-29. Agents are not covered, so the practice's post-room input shrinks and moves behind client logins |
| Search "AI reads HMRC letters accountants" | web search | No agent-side HMRC-letter product found. The gap is real but narrow: a classification layer over inbox triage that practice systems already ship |
| Volume and Pay | scout's sources plus search | Still one commenter's "20 letters a day". No outsourced price, survey count or job advert for the task. Pay is staff time only, which is modelled |
| Off-limits check | CLAUDE.md section 5 | Not lending, insurance or legal advice. Drafted replies to HMRC are tax-agent work the practice signs off. Not a red flag, but taxpayer personal data in every document |

### Score reasons
- Pain 10: plausible daily admin and real penalty risk, but only one volume figure (a comment) and no job adverts or surveys.
- Pay 4: no public price; staff time only.
- AI 7: reading and classifying varied letters is a real LLM job. But it is now a commodity (a free decoder does it), and the HMRC rules layer is a lookup table.
- Reach 6: many practices and clear channels (Xero App Store, AccountingWEB, ICAEW and AAT communities). Xero partner certification was not read.
- Build 11: synthetic letters from gov.uk templates are easy, and a mailbox or PDF input avoids the API.
- Competition 4: no HMRC-specific agent tool, but Karbon and TaxDome already sell AI triage that classifies, attaches to the client and creates tasks, and a free reader exists. Either can add HMRC labels in weeks.
- Risk 5: personal data on every page (names, UTRs, NI numbers, tax amounts), and errors carry penalty consequences.

## Verdict: KILL (first attempt, ceiling about 58)
The job is real, but the product is a thin HMRC classification layer on inbox triage that practice platforms already sell with AI. Karbon labels, attaches to the client and creates tasks; Kai (June 2026) adds categorise-and-route; TaxDome files every document on arrival. A free tool already decodes HMRC letter types from a photo. The input channel is also shrinking: HMRC went digital by default from April 2026, so letters move into the taxpayer's online account rather than the practice's post. There is no price for the job and only one volume figure. With personal data on every page, even good Pay evidence would not lift it past about 58.

**Lessons:** "reads documents and creates a task in the practice system" is the practice-management vendors' own AI roadmap (Karbon 2023 and 2026, TaxDome). Check the inbox and triage feature pages of the system the add-on sits on, not only the marketplace. And check whether the document channel itself is going digital (HMRC digital by default) before building on its volume.

**What would revive it:** HMRC giving agents a structured feed or API of client notices (an agent-services inbox) that the practice tools don't yet read, plus a survey count of notices per practice and a price that practices pay for handling them (an outsourced back office per notice, for example).

## Gate log
- 2026-11-24 round 10 scout (T-47): written at G0. Competitor check was one search only; scores left for the validator.
- 2026-11-24 validator (T-47): 47/100, KILL. Karbon and TaxDome already sell AI inbox triage with client matching and task creation; a free HMRC letter decoder exists; HMRC has been digital by default since April 2026; no price for the job. Move to `state/ideas/killed/`.
