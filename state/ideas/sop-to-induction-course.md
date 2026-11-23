# SOP-to-induction course builder

- slug: sop-to-induction-course
- stage: G0
- market and segment: UK SMEs with 20 to 250 staff and frequent new starters (warehousing and logistics, light manufacturing, multi-site retail, facilities and cleaning contractors), where an office or ops manager, not an L&D team, owns onboarding
- one-line pitch: Upload your own handbook, SOPs and site rules. Get back short, mobile-friendly induction modules with scenario questions, each answer traced to the source paragraph, plus a sign-off record showing who completed what. Courses update automatically when a policy document changes.

## Problem and who has it

UK employers must give workers "clear instructions and information, as well as adequate training", and must pay particular attention to new recruits and people changing jobs (HSE). Off-the-shelf compliance libraries cover generic topics (fire safety, GDPR, manual handling) but not "how we do it here": our forklift exclusion zones, our returns process, our lone-working rule. SMEs without L&D staff either hand new starters a PDF and a signature sheet, or pay a freelance e-learning developer by the day. CIPD's survey finds lack of time and limited budget are the top barriers to delivering learning. Existing AI course generators make polished output fast, but practitioners criticise them as "content delivery" with a quiz bolted on, with assessments that don't match objectives and weak review controls.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.hse.gov.uk/simple-health-safety/training/index.htm | 2026-11-23 | UK regulator. Employers must give "clear instructions and information, as well as adequate training and supervision". New recruits and people changing jobs need particular attention. This makes site-specific induction an obligation, not a nice-to-have. |
| https://www.cipd.org/en/about/press-releases/learning-skills-report-2020 | 2026-11-23 | CIPD and Accenture Learning and Skills at Work 2020. Top barriers to delivering learning: lack of learning time (41%), limited budgets (40%), lack of management time or support (29%). Figures are from the search-result snippet; the page returned 403 on fetch, and the data is from 2020. |
| https://elearningindustry.com/why-todays-ai-course-creation-tools-still-fall-short-and-what-theyre-missing | 2026-11-23 | Practitioner critique. Current AI tools (Articulate AI Assistant, Easygenerator, iSpring, Coursebox, Elucidat and others) are "production-first". They skip checking that assessments match objectives, rarely act as a critic, and have weak governance and human sign-off. This shows the quality gap in incumbents. |
| https://drphilippahardman.substack.com/p/ai-can-build-your-course-but-can | 2026-11-23 | Learning-science commentator on the same gap: AI builds courses but does not design the learning. Seen in search results; the full article was not fetched. |
| https://www.itjobswatch.co.uk/contracts/england/e-learning%20developer.do | 2026-11-23 | Substitute cost: median e-learning developer contract day rate in England was £375 (2024 period, only 6 rates quoted; no current-period data). Small sample, so it is an indicator only. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| iHasco off-the-shelf compliance e-learning (https://www.ihasco.co.uk/pricing, accessed 2026-11-23) | about £5.85 to £7.30 per learner per month (shown for 30 learners), 250+ courses | Generic library. The page doesn't say whether courses can be adapted to a company's own policies. |
| Articulate 360 AI (https://access.articulate.com/support/article/Articulate-360-Pricing-Options, accessed 2026-11-23 via search snippet) | $1,449 per user per year (Personal), $1,749 (Teams) | Needs a skilled author. Overkill for an ops manager. |
| Mindsmith AI authoring (https://www.mindsmith.ai/pricing, accessed 2026-11-23) | Free; Professional $39/mo per author ($468/yr); Business $65/mo ($780/yr); SCORM export | Cheap, general-purpose AI authoring. Not built around SOP change tracking, source-traced questions or sign-off records for UK SMEs. |
| Coursebox (https://coursebox.ai/pricing, accessed 2026-11-23 via search snippet) | from A$50/mo (Creator) to A$150/mo (Plus); sources conflict | Same gap as Mindsmith. |
| Freelance e-learning developer (ITJobsWatch, above) | about £375/day median (small sample) | Slow and expensive per module, and goes out of date when SOPs change. |

## Why AI is essential (and the moat)

- Turning long, messy SOPs into short learning units with scenario questions grounded in the source text is a language task. Without AI it takes an instructional designer's days.
- Traceability: every question and answer links to the source paragraph. Quality checks flag questions not supported by the document (hallucination guard) and objectives with no assessment.
- Change-awareness: when an SOP version changes, the tool finds the affected modules and redrafts them for the manager to approve.
- Moat (moderate to low): the evaluation harness for grounding and assessment alignment, and a UK SME workflow (sign-off audit trail useful for HSE and insurer conversations, simple manager approval). The generation itself is easy to copy. The review-and-governance workflow is the defensible part, and it is exactly what the critique above says incumbents lack.

## Rough build plan and Azure cost

- Week 1: document ingest (PDF, DOCX), chunking, an outline generator that respects the source, and module drafting with citations.
- Week 2: scenario question generator plus a checker (grounding, answer uniqueness, objective coverage), and a manager approval screen.
- Week 3: learner view (mobile web, no app), completion and sign-off records, CSV export, SCORM 1.2 export.
- Week 4: SOP-change diff and redraft flow, GDPR controls, and a demo built from a fictional warehouse handbook.
- Azure (estimate): Container Apps scale-to-zero (about $0 to $5/mo), Azure OpenAI (about $5 to $15/mo for demo generation runs; generation is token-heavy but infrequent), Blob Storage plus small Postgres (about $1 to $15/mo). Projected total about $6 to $30/mo.

## Risks, and what would prove this wrong

- Very crowded: cheap AI authoring tools exist (Mindsmith from $39/mo), and Articulate and iSpring are adding AI. Differentiation rests on workflow, not technology.
- SME buyers may see induction as "sign the PDF". Willingness to pay for better induction is assumed, not shown. The price signals come from adjacent products, not from SMEs paying for SOP courses specifically.
- If the product is framed as "compliance proof", wrong or missing safety content creates liability. The manager must approve everything, and the output must never be presented as legal or H&S advice.
- Learner completion data is employee personal data. It is used for training records, not hiring decisions, so risk is low to moderate.
- Proved wrong if: ops managers in target sectors say they already use iHasco plus a toolbox talk and see no gap; or a test shows a generic tool (Mindsmith or ChatGPT) produces equally grounded modules with no extra review effort.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 8 | 11 | 6 | 6 | 13 | 2 | 8 | 54 |

## Validator notes (2026-11-23)

**Red-flag check: none.** Not an off-limits area, as long as the output is never presented as health-and-safety or legal advice. No paid services are needed. Synthetic data can credibly demo the value: a fictional warehouse handbook is enough to show grounded modules, questions linked to their source and redrafts when a policy changes.

**Falsification findings** (all accessed 2026-11-23)
- Strongest competitor: Mitti by SafetyCulture (formerly SC Training and EdApp). It already does the core job: "Upload a PDF, PowerPoint or Word file and let AI turn it into a structured course", "Build a quiz in seconds with AI", completion tracking and certificates. It is "Always free up to 10 users" (https://mitti.com/team-train/). Premium is $24 per seat per month billed annually, or a per-site price with unlimited users (https://mitti.com/pricing). SafetyCulture is already used in UK frontline operations, the scout's exact segment.
- Waybook covers the governance gap the scout counts on as the moat:
  - tests and assessments (Core plan);
  - formal approval before publishing, and policy acknowledgements with an audit trail (Pro plan);
  - word-level version comparison (both plans).
  Core is $139/mo and Pro $229/mo billed annually, for 10 seats, in USD (https://www.waybook.com/pricing.md).
- Other cheap options: Trainual generates quizzes from content (https://trainual.com/, search summary only). Connecteam's training hub is free for up to 10 users and has a prompt-based AI course creator (https://connecteam.com/employee-training-software/, search summary only).
- Cheapest substitute: what the scout describes as today's practice, a PDF plus a signature sheet, or ChatGPT plus a Microsoft Forms quiz. HSE requires "adequate training" but its page says nothing about keeping records (https://www.hse.gov.uk/simple-health-safety/training/index.htm), so no regulation pushes buyers towards a paid tool.
- Pain evidence is weak. The CIPD figures are from 2020 and cover learning in general. The practitioner critiques are about tool quality, not buyer pain. There are no job ads, no complaints from SMEs, and, as the scout notes, no evidence that SMEs pay for SOP-specific courses.
- Copy risk: generating a course from a document is already a free feature. Questions traced to their source and change diffs are features an incumbent could ship in a month.

**What would change my mind (re-score on this evidence)**
1. Evidence that UK SMEs pay for site-specific induction content. Examples: agency or freelance offers priced for bespoke SME inductions, public tenders, or job ads for induction or training coordinators at firms with 20 to 250 staff in the target sectors.
2. A head-to-head desk test on a public sample SOP. It would need to show that Mitti, Mindsmith or Trainual produce unsupported or wrong questions that need heavy editing, and that a grounding checker measurably fixes this.
3. A narrower wedge with a legal forcing function and a buyer who already pays. Construction site inductions are one example; verify the legal duty and who pays.

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 54 | SafetyCulture's Mitti already turns PDF, Word and PowerPoint files into AI courses with quizzes and tracking, free for up to 10 users, Waybook already covers approvals, acknowledgements and version history, and there is no evidence that SMEs pay for SOP-specific induction.
