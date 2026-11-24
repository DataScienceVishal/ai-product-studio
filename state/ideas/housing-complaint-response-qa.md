# Social-landlord complaint response checker (Housing Ombudsman benchmarks)

- slug: housing-complaint-response-qa
- stage: G0
- market and segment: England social landlords (housing associations and council landlords) with roughly 1,000 to 30,000 homes. Their complaints team handles Stage 1 and Stage 2 responses under the statutory Complaint Handling Code. Larger groups already have in-house tooling, so the sweet spot is small and mid-size associations.
- one-line pitch: Takes a draft Stage 1 or Stage 2 complaint response plus the case file, checks it against the Complaint Handling Code and the Housing Ombudsman's own remedies and compensation guidance, and flags what the Ombudsman has ordered in similar published cases, so the complaints officer fixes the response before it goes out.

## Problem and who has it
- Since 1 April 2024 the Complaint Handling Code has been statutory for member landlords (Ombudsman remedies page via search summary; to be re-read by the validator). Each response has to meet set timescales, define the complaint, address every point raised, and offer a proportionate remedy.
- The Ombudsman's own monitoring report (28 July 2026) says Stage 2 is where it goes wrong: "The Code allows for double the time to handle, but too often the review is inadequate." It also lists recurring policy gaps: complaints not defined at acknowledgement, extensions not explained, no escalation offered, and exclusions applied unfairly (fetched).
- Outcomes cost money and reputation: in 2025-26 the Ombudsman made 8,783 determinations, upheld 62% of complaints (down from 71%) and ordered about £4.8m compensation, averaging £703 per upheld case (Local Government Lawyer report of the Annual Complaints Review, fetched).
- Who does the work now: complaints officers and investigators, salaried staff (see price points).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.housing-ombudsman.org.uk/2026/07/28/new-ombudsman-report-identifies-lessons-from-monitoring-the-complaint-handling-code/ | 2026-11-24 | Fetched. Stage 2 reviews "too often ... inadequate"; list of common policy weaknesses; "room for improvement". No numbers on response quality. |
| https://localgovernmentlawyer.co.uk/housing-law/397-housing-news/101683-housing-ombudsman-hails-real-progress-as-annual-review-reveals-lower-proportion-of-complaints-being-upheld | 2026-11-24 | Fetched. 8,783 determinations; 62% upheld (71% the year before); about £4.8m compensation, average £703 per upheld case; 99% of orders complied with on time. Number of landlords not stated. |
| https://www.housing-ombudsman.org.uk/landlords-info/guidance-notes/compensation-guidance/ | 2026-11-24 | Fetched. Published compensation bands (up to £50, £100, £250 for complaint-handling failures; up to £100, £600, £600+, £1,000+ for other failings; £15 a day for loss of heating or hot water; rent-based loss-of-use percentages). "Guidelines and not prescriptive." |
| https://www.housing-ombudsman.org.uk/landlords-info/guidance-notes/ | 2026-11-24 | Fetched. 18 guidance notes (remedies policy, apologies, outcomes, hazards, offsetting, unacceptable behaviour, and others). This is the rule set a checker would encode. |
| https://www.housing-ombudsman.org.uk/decisions/ | 2026-11-24 | Fetched. Published decision reports from December 2020, listing spans 1,834 pages, filters by landlord, category, outcome and orders; residents anonymised, landlords named. Reuse terms not stated. |
| https://jobsearch.yourhousinggroup.co.uk/jobs/job/Senior-Customer-Resolution-Officer/2563 | 2026-11-24 | Search summary only. Senior Customer Resolution Officer, £34,000 to £36,000, manages complex Stage 2 complaints, asks for knowledge of the Code. |
| https://careers.stonewater.org/jobs/7827410-specialist-resolution-caseworker-complaints | 2026-11-24 | Search result title only: Specialist Resolution Caseworker (Complaints) at a large association. Salary not read. |
| https://findajob.dwp.gov.uk/details/17706415 (and the related DWP listings in the same search) | 2026-11-24 | Search summary only. 2026 complaints roles at £27.8k to £48.3k (for example a Senior Complaints Investigator at £43,481 to £48,314). Salaries and closing dates not checked on employers' pages. |
| https://www.housing-technology.com/aspirations-for-ai-in-housing/ | 2026-11-24 | Search summary only. Sector press describes AI that categorises and routes complaints. That is triage, not response checking. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Complaints officers and investigators (salaried) | £34,000 to £36,000 (Senior Customer Resolution Officer); up to £48,314 (Senior Complaints Investigator). Source above, search summaries | The staff cost is the budget the product would sit against. A tool does not replace them; it cuts rework and Ombudsman exposure |
| Complaints modules in housing systems. Aareon HomeMaster and ActiveH Web: "structured, policy-led complaint handling", "templates and guidance supporting consistent, professional resident communications" (page fetched: https://www.aareon.co.uk/housing-ombudsman-2026-27-business-plan-impact-on-social-housing-landlords-aareon) | Bundled, no price published | Workflow, deadlines, KPIs and templates. The page says nothing on AI drafting or checking, and nothing on benchmarking against Ombudsman determinations |
| NEC Housing, Civica, Mobysoft | Not published | Search found no AI complaint-drafting feature (search summaries only; product pages not read). NEC writes about AI call summaries (https://www.necsws.com/article/housing/reimagining-housing-customer-care-for-residents-where-ai-is-making-an-impact) |
| Ombudsman's free Code self-assessment and example response letter | Free | A checklist and a template, not a check of a specific draft |
| General chatbots (a complaints officer pasting the draft into one) | £0 to about £20 a month per seat (estimate; no source) | No grounding in the Ombudsman's published decisions, no audit trail. This is the real substitute and the biggest threat |
| Cost of getting it wrong | £703 average compensation per upheld case, plus the Ombudsman's findings in the public record | Frames the value of a pre-send check |

## Why AI is essential (and the moat)
- The job is judgement over messy text: does this response address each issue the resident raised, does the evidence in the case file support what the response claims, is the remedy proportionate against the Ombudsman's bands and orders in comparable cases? Rules alone cannot do that.
- Honest limit: "AI reads documents and drafts" is not a gap, and the system vendors could add a draft button within months. The defensible parts are (1) retrieval over the Ombudsman's published decisions and guidance so every flag cites a real decision or guidance note, (2) a system-agnostic second opinion that works across Aareon, NEC and Civica customers and spreadsheets, and (3) an audit trail a Board can show the regulator.
- Moat is the evaluation set: published decisions labelled by failure type (late response, missed issue, no apology, remedy too low, no Stage 2 escalation).

## Public data the studio would use to prove the gap and build the demo
- Housing Ombudsman decision reports (public web pages, see doubts on reuse), guidance notes and Code text.
- Annual Complaints Review figures and quarterly landlord performance data (published by the Ombudsman).
- Proof test the studio can run itself: take 100 published decisions, strip the Ombudsman's finding, give the model only the landlord's account and the complaint, and measure how often it spots the failure the Ombudsman found and the remedy band it ordered. If recall of the Ombudsman's findings is below about 70%, kill the idea.
- Demo data: synthetic complaint cases written from public decision patterns (no real resident data); synthetic draft responses with seeded defects. Mock mode loses nothing because no paid telephony or messaging is needed.

## Add-on check (does the incumbent already do it?)
- Read: Aareon's page (complaints = workflow, templates, KPIs; AI named only for repairs). Searched: NEC, Civica, Mobysoft, Housing Partners (nothing found on AI response checking). Not read: product pages of NEC, Civica and Mobysoft; the validator should read them.
- The Ombudsman has its own AI tool for residents (search summary: https://www.housing-ombudsman.org.uk/?p=124400), but it helps residents make complaints, not landlords draft responses.
- Free practitioner tools: nothing found in two searches. Check the Housing Ombudsman Service's and trade bodies' (for example Housemark and the National Housing Federation) resource pages before scoring.

## How the selling partner could reach buyers
- Complaints and customer-experience leads at housing associations; housing technology press (Housing Technology magazine) and procurement via G-Cloud. Channel unknown: Q-6 asks Vishal for the partner's sector. If the friend has no housing contacts, Reach drops to 3.

## Rough build plan and Azure cost
- Corpus of guidance and decisions (about 300 labelled cases for evaluation), checker for the Code's timescales and content rules, remedy-band suggester, response review UI with citations, audit log. About 4 weeks. Azure: about £15 to £30 a month (estimate, scale-to-zero plus the shared Postgres). Model cost depends on Q-7.

## Risks, and what would prove this wrong
- Reuse of decision reports: the Ombudsman's pages show "© Housing Ombudsman Service 2026" and no reuse licence (fetched). Bulk copying could breach terms; the studio must not scrape. Safer path: use guidance notes and the Code (quote briefly), use a small manually read sample of decisions for tests, and ask the Ombudsman about a data export (contacting anyone needs Vishal's OK). If decisions cannot be used, the retrieval moat shrinks.
- Resident personal data in real complaints: pseudonymise before processing; no personal data for the demo.
- Regulated-adjacent: the tool must never say a response is "compliant" or advise on legal claims (disrepair claims are legal advice territory); it flags issues and cites guidance, and the landlord decides.
- Vendors ship "draft and check" inside the complaints module. Test: read NEC and Civica pages and release notes; if found, Competition falls to 2.
- A large landlord's in-house team may already use chatbots; the tool must beat a chatbot on grounded citations.

## Score (validator)
Draft self-score by the scout (validator to re-score):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 14 | 10 | 9 | 5 | 11 | 4 | 7 | 60 |

Rationale in one line each: Pain 14 (official upheld rate, Ombudsman's own Stage 2 criticism, statutory Code); Pay 10 (salary and compensation figures but no software price for this job); AI 9 (judgement and retrieval, but drafting is commoditised); Reach 5 (channel unknown); Build 11 (text only, rules are public); Competition 4 (no AI response checker found, but system vendors can add one); Risk 7 (pseudonymisation needed, advice boundary).

## Gate log
- 2026-11-24 scout round 6 (T-36): G0 drafted. The first proof test (labelled-decision recall) is the one thing that can move this above 60.
