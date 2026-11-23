# Site-specific RAMS drafting for subcontractors

- slug: subcontractor-rams-drafting
- stage: G0
- market and segment: UK specialist trade subcontractors with roughly 5 to 50 staff (for example drylining, roofing, groundworks, scaffolding, flooring) who must submit risk assessments and method statements (RAMS) to principal contractors before every job. Electricians are a weaker sub-segment because the ECA gives members a free tool.
- one-line pitch: Turn the principal contractor's site pack and a short voice or text description of the job into a site-specific RAMS in the contractor's required format, with risk assessment and method statement kept consistent, so it gets accepted first time.

## Problem and who has it

Principal contractors commonly withhold site access until a subcontractor's RAMS have been reviewed and accepted. Rejections are common for predictable reasons: generic text left over from other jobs, missing site details (address, supervisor, first aider, assembly point), hazards in the risk assessment that have no matching control in the method statement, and conflicts with the construction phase plan or site rules. A rejected RAMS delays the start on site while it is rewritten. Small firms do this per job, usually by editing old Word templates, paying a consultant, or using RAMS software. Employers with 5 or more staff must record their risk assessments.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.designingbuildings.co.uk/wiki/RAMS_review_and_approval | 2026-11-23 | "Rejected RAMS delay start on site while documents are revised and resubmitted"; "site access is commonly withheld until RAMS have been reviewed and accepted"; lists six common rejection causes (generic content, missing site info, RA/MS mismatch, weak high-risk arrangements, conflict with site plan, unreadable length). |
| https://www.constructionline.co.uk/?p=36349 (Constructionline blog, undated, © 2026) | 2026-11-23 | Generic or vague RAMS "often face rejection"; principal contractors often require RAMS before site access, and clients assess them during tendering. |
| https://eca.co.uk/downloads/erams/erams-brochure-rev-0622 (ECA eRAMS brochure, rev 06/22) | 2026-11-23 | 1,450+ ECA member firms using eRAMS and 65,000+ eRAMS risk assessments completed, showing high recurring volume in one trade alone; also states that employers with 5 or more employees must record risk assessments. |
| https://tilersforums.com/goto/post?id=960383 (search snippet only; page returned 403) | 2026-11-23 | A sole-trader tiler reports main contractors now demanding RAMS, implying no RAMS means no contracts. Unverified beyond the snippet. |
| Fiverr listings for UK RAMS writing (for example https://www.fiverr.com/zmarakehs/prepare-health-and-safety-method), seen in search results | 2026-11-23 | Many sellers offer UK RAMS writing, one cited at $200 to $400 per gig (search summary, not fetched). Indicates people pay per document. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| HandsHQ RAMS software (https://handshq.com/pricing) | Small from £275/month (up to 10 users), Medium from £550, Large from £750, billed annually plus set-up fee | Priced for firms with a safety team; template-driven, still manual tailoring per site. |
| ECA eRAMS (brochure above) | Free to ECA members | Electricians only; template tool, not drafting from the site pack. |
| RamsBox (https://www.capterra.co.uk/software/1325744/RamsBox, seen in search results; page returned 403) | £7 per tailored RAMS (search snippet, unverified) | Shows a cheap AI-style competitor already exists; quality and acceptance rate unknown. |
| QuickRAMS consultant service (quickrams.pages.dev, seen in search results; host not reachable from this session) | From £295 for full RAMS, £445 "rejection rescue" (search snippet, unverified) | Expensive per job and slow turnaround. |
| Office staff editing old Word templates | Staff time; not measured | Source of the generic-content rejections. |

## Why AI is essential (and the moat)

The work is reading the principal contractor's site-specific documents (construction phase plan, site rules, permit systems, required format) and writing a tailored, internally consistent document from a short description of the task. Templates can't do the tailoring and the RA-to-MS consistency check; a language model with a structured hazard library can, and can also check a draft against the principal contractor's own rejection reasons.

Moat: a growing library of accepted RAMS by trade and by principal contractor format, an evaluation set built from published rejection criteria, and per-firm memory of plant, people and training records. The cheap competitors show the writing itself is easy to copy, so the moat must be the "accepted first time" quality and the PC-format fit.

## Rough build plan and Azure cost

1. Firm profile: trades, plant, competent people, training records (company data, minimal personal data).
2. Job intake: upload site pack PDFs plus a short job description.
3. Draft RA and MS in the PC's format, with a hazard-to-control cross-check and a "missing site info" list.
4. Pre-submission review against common rejection reasons; export to Word/PDF.
5. Library of past accepted RAMS for reuse.

Azure (estimate, method: scale-to-zero container app, small database on free or lowest tier, blob storage, pay-per-token Azure OpenAI at demo volume): likely under $15 a month in build. Architect to confirm in `state/BUDGET.md`.

## Risks, and what would prove this wrong

- Safety-critical output: a wrong method statement could contribute to harm. The product drafts; a competent person must review and sign. Must not be marketed as replacing a competent person.
- Crowding: cheap tools (£7 per RAMS) and template software already exist, pushing prices down.
- Trade bodies give free tools to members (ECA), which may spread to other trades.
- Proven wrong if: subcontractors report their RAMS are rarely rejected, or they are content with old templates, or they won't pay more than a few pounds per document.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
