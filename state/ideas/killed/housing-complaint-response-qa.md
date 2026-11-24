# Social-landlord complaint response checker (Housing Ombudsman benchmarks)

- slug: housing-complaint-response-qa
- stage: KILLED at G0 (validator 57, 2026-11-24, T-36)
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
Scout draft: 60 (Pain 14, Pay 10, AI 9, Reach 5, Build 11, Competition 4, Risk 7).

Validator score, 2026-11-24 (T-36):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 14 | 9 | 9 | 5 | 11 | 3 | 6 | 57 |

**Falsification findings** (all accessed 2026-11-24; "fetched" means the page itself was read)
- An AI drafter for social-housing complaints already exists. VerseOne Tenant Voice, a "Feedback Management Solution for Social Housing" on G-Cloud, offers "Personalised AI-drafted responses for staff review", and AI that summarises complaints and pulls out the key issues and sentiment (https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/658496294786576, fetched). It doesn't say it checks against the Code or Ombudsman decisions, but it already sells the "draft, then a human reviews" step.
- The complaints systems already sell compliance with the Code:
  - MRI Customer Central "Helps comply with housing ombudsman 2 stage complaints" and uses "Active AI to summarise cases" (https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/612281534672502, fetched).
  - Crimson's Complaints Management Solution - Housing lists "Compliance aligned to the Complaint Handling Code" and predictive trend analytics (https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/662767678381583, fetched).
  - Neo Technology Housing Complaints Case Management covers Stage 1 and 2, Ombudsman escalation and SLAs, with no AI (https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/727901350443513, fetched).
  - Any of these vendors could add a "check this draft against the Code" button within a month.
- Consultants already sell "check our complaint handling against Ombudsman expectations".
  - Housemark's Complaints Service Review reviews "policies, processes, case files, and evidence" against "regulatory expectations and Ombudsman best practice" (https://www.housemark.co.uk/service-improvement-transformation/, fetched; no price).
  - HQN runs Code-compliance reviews for councils (https://www.warwickdc.gov.uk/directory_record/15904/01_complaints_handling_code_non-compliance, search result).
  - Campbell Tickell sells a complaints culture scan (https://www.consultancy.uk/news/43991/campbell-tickell-launches-culture-scan-to-boost-trust-in-social-housing, search result).
  - This proves that landlords pay for the work, but these are periodic sample reviews, and none of them publish a price.
- Pay is still unpriced. None of the four G-Cloud listings shows a price on its page (prices are in linked pricing PDFs that weren't read), and Housemark doesn't publish one. Salaries come from search summaries.
- Data licence: no licence covers the decisions.
  - The decision, guidance-on-decisions and publication-policy pages (https://www.housing-ombudsman.org.uk/guidance-on-decisions/, fetched) show only "© Housing Ombudsman Service 2026" and give no reuse terms.
  - The Ombudsman is a non-Crown body, so the OGL doesn't apply by default (National Archives licensing guidance, search result).
  - Reading a small sample of decisions by hand for the proof test is defensible. Using the decisions as a retrieval corpus in a paid product needs the Ombudsman's permission, which means contacting them (ask-first). Without the decisions, the "cites comparable decisions" moat goes, leaving the Code and guidance notes, which any vendor or chatbot can use.
- Legal-advice line (CLAUDE.md section 5): **not crossed as scoped, so no red flag.**
  - Why it's not over the line: the user is the landlord's own complaints officer, and the output checks the landlord's own letter against a statutory code and published guidance. That is compliance checking, not advice to anyone about their legal rights.
  - It would cross the line if it:
    - advised on disrepair or fitness-for-habitation claims or liability;
    - told residents what they are entitled to;
    - presented a compensation figure as what is owed in law.
  - The remedy-band suggester is the feature closest to the line. It must stay as "Ombudsman guidance band X, see note Y", never as a valuation.
  - Risk is scored 6 because of this, and because complaint files routinely contain health, disability and vulnerability details (for example damp and mould cases involving children).
- Cheapest substitute: a complaints officer with a general chatbot, the Code, the Ombudsman's free self-assessment and its free Learning Hub training.

**Scores in brief.**
- Pain 14: official, fetched figures (62% of 8,783 determinations upheld, the Ombudsman's own criticism of Stage 2), but no measure of how often responses are reworked.
- Pay 9: complaints modules and consultant reviews are bought, but no price for any of them was found.
- AI 9: the judgement over text is real, but an AI drafter already ships, and the grounding corpus has no licence.
- Reach 5: the buyer list is public, but procurement runs through G-Cloud and frameworks, and the partner's sector is unknown.
- Build 11: text-only and the rules are public.
- Competition 3: VerseOne already drafts with AI, MRI, Crimson and Neo sell Code compliance, and consultants sell reviews.
- Risk 6: resident special-category data, and close to the advice boundary.

**Verdict: KILL (first attempt; ceiling below 70).**
- The pain is official and well documented, but the job is already split between three groups:
  - complaints systems that sell Code compliance (MRI, Crimson, Neo, Aareon);
  - a social-housing vendor that already ships AI-drafted responses for staff review (VerseOne);
  - consultancies that review complaint handling against Ombudsman expectations (Housemark, HQN, Campbell Tickell).
- The one feature that would set the product apart, citing comparable Ombudsman decisions, rests on a corpus with no reuse licence. It can't be used without contacting the Ombudsman.
- Even with the best plausible evidence (Pain 16, Pay 12, AI 10, Reach 7 with a housing channel, Build 11, Competition 5, Risk 6), the score tops out at about 67.

**Lessons**
- G-Cloud listings are a fast, public way to check incumbents in public-sector niches. Four listings settled Competition here in minutes. Their pricing PDFs are public and are the next place to look for Pay.
- "Grounded in an ombudsman's decisions" is only a moat if the decisions carry a reuse licence. Check the licence before scoring AI or Competition. Non-Crown bodies (ombudsmen, regulators set up by statute) often publish without the OGL.
- Where consultants sell periodic sample reviews, the software pitch is "continuous review of every case". That needs a price per case reviewed, which is what to look for, not salaries.

**What would revive it**
- Written permission (or a published licence) from the Housing Ombudsman to reuse decisions commercially, plus a proof-test result of at least 70% recall of the Ombudsman's findings on a hand-read sample. Contacting the Ombudsman needs Vishal's OK.
- And a selling partner with access to housing associations (Q-6), plus a price for VerseOne's AI drafting or a complaints module from the G-Cloud pricing PDFs.

## Gate log
- 2026-11-24 scout round 6 (T-36): G0 drafted. The first proof test (labelled-decision recall) is the one thing that can move this above 60.
- 2026-11-24 | validator | G0→G1 | KILL 57 | VerseOne already sells AI-drafted social-housing complaint responses, complaints systems (MRI, Crimson, Neo) sell Code compliance, Housemark and HQN sell complaint-handling reviews, and the Ombudsman decisions that would set the product apart carry no reuse licence; ceiling about 67. Not a legal-advice product as scoped (landlord-side QA, no claim valuation).
