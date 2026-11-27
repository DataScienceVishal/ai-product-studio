# SPEC: SME council tender drafting (T-183)

## 0. Honesty note (read first)
- This idea scored **60 at G1** (verdict REVISE, parked as a kill candidate; `state/ideas/sme-council-tender-drafting.md`). The studio's bar for build is 70. Vishal answered Q-18 with C: build the best parked idea anyway as a **portfolio demo**, knowing it scores below 70.
- So this is **not a validated product**. No buyer has been spoken to. The validator found no wedge: the closest competitor, CleanTender, already sells the same job at £99 a month (Competition scored 1 of 10). Passing the acceptance bars in section 5 shows the build works. It does not show anyone will pay, and it does not change the 60.
- Scope is a demo: public data and made-up firm evidence only. Selling is locked until `unlock selling`. Nothing here is a price commitment.
- **Target stage:** a private demo with the core flow working end to end (G3-equivalent). It does not aim for G4 Sellable, and the idea stays at G0 (REVISE 60) in `state/ideas/RANKING.md`. Moving past the demo needs a new G1 score of 70 or more. (Added by validator, T-183.)
- Evidence below comes from the idea file (accessed 2026-11-23 to 24) and `state/ideas/Q18-CANDIDATE.md` (CleanTender re-read 2026-11-26). Competitor facts are from the vendors' own pages and are not independently confirmed.

## 1. Customer profile
- **Business:** UK service SMEs, roughly 10 to 150 staff, with no in-house bid team. Examples: commercial cleaning, security, grounds, facilities and training providers, bidding for local-authority and NHS-estate contracts under the Procurement Act 2023.
- **Who buys:** the owner or managing director. **Who uses it:** an operations or contracts manager who writes bids on top of a day job. **Who signs off:** the same owner, before every submission. The tool never submits.
- **Triggers:** a tender notice that fits the firm; a deadline in two to four weeks; losing a bid with no useful feedback (the FSB reports only one in 20 bidders gets "comprehensive and actionable feedback", SME Web, 15 Dec 2025, sample size not stated); the cost of a freelance bid writer (median £500 a day, ITJobsWatch, 6 months to 23 Nov 2026, IT-skewed).
- **Pain evidence, thin:** the FSB says 35% of small firms "repeatedly waste time submitting the same information for each new bid" (same source). techUK's 2023 survey of 100 tech members found 76% call social value an administrative burden; that sample was tech firms, not service SMEs. Bids per firm per year is **unknown**.

## 2. Job to be done and core flow
Job: "Give me a first draft of every answer in this tender, in the firm's own words, within the word limits, with proof for every claim, so I edit instead of starting from a blank page."

The demo must nail these seven steps:
1. **Upload the tender pack** (PDF and Word files: ITT, specification, pricing and SQ forms).
2. **Extract the checklist:** every question, its word or page limit, its marks or scoring weight, mandatory pass/fail requirements and the deadline. Each item links to the source page. The user confirms or corrects the list.
3. **Retrieve evidence:** for each question, find passages in the firm's evidence library (policies, past bids, case studies, accreditations, social value commitments, staff and turnover facts). Show what was found. If nothing is found, say so.
4. **Draft answers** inside the word limit, written only from the retrieved evidence. Every claim carries a citation `[E-12]` to a library passage. Where evidence is missing, the draft inserts a visible gap marker ("NEEDS FIRM INPUT: no case study found for X"), never an invented one.
5. **Claim check:** a separate pass splits each draft into claims (numbers, named clients, accreditations, dates, commitments) and checks each against its cited evidence. Each claim is marked supported, unsupported or contradicted. Any draft with an unsupported claim is blocked from export until a person fixes or removes it.
6. **Coverage check:** a table showing every question answered, within limit, mandatory items covered, gaps still open. It is a checklist, never a statement that the bid is "compliant" (see Won't). A named reviewer signs off with a timestamp. The sign-off screen states that the firm remains responsible for every statement in the bid.
7. **Export** to Word (answers in question order, limits shown, citations as inline `[E-n]` markers) plus an evidence appendix listing every claim and its source. True Word footnotes are a Should (python-docx has no footnote API, so they need low-level XML work). The export header says "Draft prepared with AI assistance; reviewed by [name]" to line up with the disclosure that PPN 017 suggests buyers may ask for, and the footer repeats that the firm is responsible for every statement.

## 3. Reuse and architecture
Start from a copy of `products/_starter` (sign-in, tenant isolation, billing in test mode, AI adapter with per-customer cap, logs, health check, deploy design; see its README). Replace the `Note` object with: `TenderPack`, `Requirement`, `EvidenceItem`, `Draft`, `Claim`, `SignOff`. Keep `_scoped()` so every query filters by `tenant_id`, and copy the tenancy tests for each new object.

New work beyond the starter: PDF and DOCX text extraction with page references; chunking and retrieval over the firm's evidence (Postgres full-text only in this build; embeddings are a Should); extraction, drafting and claim-check prompts with structured output; the Word export; the review screens.

**AI cost is the constraint.** The starter caps AI at about $6.10 a month and 98,000 tokens a day (starter README). A tender pack is long. The demo therefore uses short, public packs (under about 40 pages), caches extraction results, and runs the live model only for the scripted demo. FakeAI with recorded outputs covers tests and offline demos. Any larger model spend is ask-first (Q-16 style); the architect confirms cost in `state/BUDGET.md`.

**The evaluation needs live tokens too** (added by validator, T-183). FakeAI cannot produce the section 6 numbers. Rough estimate, method stated, for the architect to replace with a measured figure: a 40-page pack is about 30k input tokens to extract; drafting about 15 questions at about 5k tokens each (evidence, answer, reasoning) is about 75k; the claim check is about 45k. That is about 150k tokens a pack, so all 9 held-out packs run end to end would be about 1.35M tokens. That is about 14 days of the 98,000-a-day cap and about $2.70 of the $6.10 a month at a $2.00 per million blend, before any tuning. Therefore:
- A1 to A3 (extraction) run on all 9 held-out packs. A4 to A8 (drafting and claim check) run on the 30-question trap set plus **3** of the held-out packs, chosen by a fixed rule (the first of each sector in `demo-data/SOURCES.md` order) before any run.
- The run configuration is fixed in `EVAL.md` before the first scored run: model and deployment, reasoning effort, output-token cap per call, and the truncation rule (one retry at a larger cap, then the item is scored as failed). Long packs are chunked, because a single 30k-token call does not fit the starter's per-call reservations (starter README, "Sizing the daily AI cap"). Output tokens per call are logged.
- The architect's estimate must show the eval plus tuning plus the scripted demo fitting inside the $6.10 a month and the daily cap across the two weeks. If it doesn't, cut the held-out drafting packs to 2 or ask Vishal for a one-off eval budget (ask-first). Never raise the cap without his yes.

## 4. MVP scope (about two weeks of runs)
**Must**
- Starter copy, with product objects and migration; billing, plans and prices switched off (no price shown in the app or demo).
- Pack upload, text extraction with page references, and the requirement checklist with user edit.
- Evidence library upload (DOCX, PDF, text), chunked and searchable, with item IDs.
- Cited drafting with word-limit enforcement and gap markers.
- Claim check with the block-on-unsupported rule, and a visible claims table.
- Coverage check, reviewer sign-off with the firm-responsibility statement, Word export with inline citations and the evidence appendix.
- Demo seed: one made-up firm, three tender packs loaded, the evidence library loaded.
- Evaluation harness that produces the numbers in section 5, committed as a script with its results file.
- End-to-end browser test of the seven steps with FakeAI.

**Should**
- A bid/no-bid fit summary from the mandatory requirements (CleanTender has a scored version; keep this simple).
- Scoring-weight-aware drafting (spend words where marks are).
- Re-use of an approved answer as evidence for the next bid (the answer library that grows).
- PDF export.
- Embeddings for retrieval; true Word footnotes.
- Should items start only after every Must is done and A6 has passed.

**Won't (this build)**
- OCR of scanned or image-only PDFs. Packs with image-only pages are dropped at selection.
- Real customer data, real firm documents, or any live tender submission.
- Logging in to supplier portals (ProContract, In-Tend and similar): needs accounts and may breach their terms.
- Scraping. Packs come only from official APIs or downloads, or are hand-picked from public notices.
- Live tender alerts or search, framework tracking, pricing and cost-model sheets, Selection Questionnaire autofill from a firm profile, team workflow beyond one reviewer.
- Live payments, outreach, price commitments, any public launch.
- Any statement that a bid is "compliant", "will score well" or "legally sound".

## 5. Demo data plan
**Tender packs (public, no personal data).**
- Source: notices and attached documents published on Contracts Finder or Find a Tender, which publish under the Open Government Licence (the validator confirmed OGL and the public APIs: https://www.find-tender.service.gov.uk/Developer/Documentation, https://www.contractsfinder.service.gov.uk/apidocumentation). Document attachments can carry their own terms, so for each pack the builder records the notice URL, access date and the licence line shown on that notice in `demo-data/SOURCES.md`, and drops any pack whose terms are unclear.
- Choose 12 packs: 4 each for cleaning, security and grounds or facilities, from council or NHS buyers, with different layouts (tables, forms, narrative PDFs, Word question sheets). Three go into the live demo; nine are held out for the evaluation, to keep the numbers honest.
- Download by hand or with the official API at a polite rate. No supplier-portal logins. If a notice's documents sit behind a portal login, skip it.
- Before use, check each pack for named individuals (contact names, personal email addresses, direct phone numbers, signatures). Remove or skip them. Company-level text only.
- If the official APIs need a key or account to download attachments, stop and ask first; hand download from the public notice page is the default.

**Firm evidence (invented).**
- A fictional firm, name "Harrowmere Facilities Ltd (fictional)" (chosen at D2 on 2026-11-27 after the Companies House check in `demo-data/SOURCES.md`; the earlier placeholder "Brackenmoor" sat one letter from a live company, Brackenmore Ltd) (made-up, 102 staff, three **fictional** councils as clients). Not "Northgate": several real Northgate companies exist, including suppliers to councils. Before writing any document, the builder searches the Companies House register for the chosen name, logs the result in `demo-data/SOURCES.md`, and picks another name if a live company matches. About 20 to 40 documents written by the studio: health and safety policy, environmental policy, modern slavery statement, training matrix, six case studies with invented figures, social value commitments, accreditation list (invented numbers), turnover bands.
- Every fact in them is fictional and marked so in a footer. No real company or council names as clients, no real accreditation numbers, no personal data (staff in case studies are roles, not names).
- A deliberate **trap set**: 30 questions where the evidence is missing or only partly supports an answer (for example, a question asks for a case study in a sector the firm never served; a question asks for ISO 14001 when only ISO 9001 is in the library). These test the gap markers and the claim check.

## 6. What the demo must prove (acceptance bars)
The strategist proposed these bars and the validator accepted them at T-183. **Pre-registration:** the bars below, the hand-made answer keys for the 9 held-out packs, the trap set with its 40 seeded false claims, and the run configuration (section 3) are committed to `main` before any scored model run, and `EVAL.md` records that commit hash. After that, any change is a dated amendment in this file with its reason; it never silently replaces the old bar. Drafting tuning uses only the 3 demo packs, never the held-out ones. QA writes the harness. Results go in `products/sme-council-tender-drafting/EVAL.md` with the commit and model used. The numbers are for the demo, not evidence of market demand. Extraction bars (A1 to A3) run on all 9 held-out packs; drafting bars (A4 to A8) run on the trap set plus 3 held-out packs (section 3).

| # | Bar | Target | How measured |
|---|---|---|---|
| A1 | Question extraction recall | at least 90% of questions found (recall), and at least 90% precision | A person lists the questions in each of 9 packs once, before any model run; compare |
| A2 | Limits and weights | at least 90% of word limits and marks captured correctly where the pack states them | same hand-made key |
| A3 | Mandatory requirements | at least 85% of pass/fail items found; none shown as optional | same key |
| A4 | Traceability | at least 95% of claims in drafts carry a citation that resolves to a real library passage | script resolves every `[E-n]` |
| A5 | Support | at least 90% of cited claims judged supported by a human reading the cited passage, on a random sample of 100 claims (fixed seed recorded in `EVAL.md`; all claims if fewer than 100) | human review; noted as a self-assessment |
| A6a | Claim check catches seeded false claims | at least **38 of 40** (95%) seeded false claims marked unsupported or contradicted. Every miss is listed in `EVAL.md` by type | the 40 false claims (wrong numbers, invented clients, accreditations not held, wrong dates) are inserted into fixed fixture drafts written before the run, so the checker is tested on its own, apart from drafting |
| A6b | Export gate | **100%** of drafts with any claim flagged unsupported or contradicted are blocked from export | deterministic test, no model needed |
| A6c | Nothing unsupported in exports | **0** unsupported or contradicted claims found by a human in the exported drafts from the A4 to A8 run (the 100-claim A5 sample is drawn from these) | human review; the miss rate from A6a is stated next to it, never "zero risk" |
| A7 | Word limits | 100% of drafts at or under the stated limit | script |
| A8 | Gaps honest | on the trap questions, at least 90% show a gap marker instead of an invented fact | script plus human check |
| A9 | Speed | one pack from upload to reviewed draft in under 15 minutes of user time on the seed firm | stopwatch |

A6 (a, b and c) is the headline. If any part of A6 fails, the demo is not shown. A5 and A6 rely on a model checking a model, so a human reads a sample, and the limits of that are stated in `EVAL.md`.

## 7. Positioning
- **One sentence:** For UK service SMEs without a bid team, a tender assistant that reads the pack, drafts every answer from your own evidence, and refuses to let an unsupported claim reach the export.
- **Alternative it replaces:** the blank Word document plus copy-paste from old bids; a freelance bid writer at about £500 a day; or ChatGPT or Copilot with a folder of past answers.
- **Honest comparison.**

| | This demo | CleanTender (https://cleantender.co.uk/, re-read 2026-11-26) |
|---|---|---|
| Price | not set; untested hypothesis £59 to £249 a month (section 8) | £99 a month or £990 a year, a free plan, 7-day trial |
| Sector | any service SME (demo seeded with cleaning, security, grounds) | soft FM only: cleaning, security, grounds, waste and hygiene, catering |
| Pack scan and requirement extraction | yes | yes, with a 0 to 100 fit score and bid/no-bid verdict |
| Draft from your evidence | yes, with per-claim citations | yes, SQ response generated against your profile |
| Claim check | yes; blocks export | **yes, one-click claim check on every answer** |
| Compliance vault | no | yes |
| Product maturity | demo, unproven | live, with customers |

Also on the market: BidWriter (free to £799 a month, word-limit and marks-aware, SME-focused), Stotles (free Bid Studio tier), Thornton & Lowe (from £2,750 + VAT a year), per-bid SwiftBid (£149 to £749). Prices from the idea file; some listings were unverified.

- **Where this is equal or weaker:** on paper (CleanTender's output has not been tested; a trial needs a card, so it is ask-first) equal on extraction, drafting from evidence and a claim check; **weaker** on sector depth, fit scoring, compliance vault, maturity and price. We have no wedge the validator could evidence.
- **Differentiators that are true (and small):**
  1. Export is **blocked** until every claim is supported or removed, and the evidence appendix lists each claim's source. (CleanTender's claim check exists; whether it blocks export is not confirmed, so treat this as a design choice, not a proven edge.)
  2. Every draft claim cites a library item and shows its source passage side by side.
  3. Measured, documented bars (section 6) on public packs, shown in the private demo so a reader can check them (nothing is published). Competitors' pages publish no such figures that we found.

## 8. Indicative pricing (not a commitment; selling is locked)
Method: anchor on what firms pay now. Not tested with any buyer.
- **Anchors:** freelance bid writer median £500 a day; CleanTender £99 a month; BidWriter £49, £149, £279 and £799 a month; Thornton & Lowe £2,750 + VAT a year for one user (sources in section 7 and the idea file).
- **Hypothesis, per month ex VAT:** **Solo £59** (3 live tenders, 1 user); **Team £99** (10 live tenders, 3 users); **Firm £249** (unlimited, 10 users, shared answer library). At a £500 day rate, one saved writer day a quarter covers Team.
- **Free trial:** one tender pack drafted on the firm's own evidence, 14 days. **First customers:** first 3 pilots free for 3 months, then 50% off for 6 months, for feedback. The starter has EARLY50 (50% off for 3 months); the pilot offer differs.
- This is parity with CleanTender, not cheaper. Price is not a reason to buy. Nothing is loaded into `app/billing.py`, and no price appears in the demo.

## 9. Pilot success metrics (only if selling is unlocked and a friend's firm agrees)
- **Activation:** at least 3 of 5 pilot firms upload a real tender pack and an evidence library and reach an exported draft within 14 days; at most 10% of extracted requirements need manual correction.
- **Weekly use:** at least 2 of those return for a second tender within 6 weeks (bid volume per firm is unknown; this is the real test of a subscription).
- **Time or money saved:** self-reported drafting hours per tender at least halved (the target to check against is a firm's own baseline, not an assumed figure); at least one case where the claim check caught a real error.

## 10. Risks and open questions
- **Procurement Act exclusion from invented claims.** Schedule 7 para 13 lists "providing information that is incomplete, inaccurate or misleading" as an example of acting improperly, a discretionary exclusion ground (https://www.legislation.gov.uk/ukpga/2023/54/schedule/7/paragraph/13). An invented case study or statistic in a bid could therefore hurt the customer. **Addressed by design, not guaranteed:** drafting from retrieved evidence only; gap markers instead of invention; claim check that splits claims and verifies each against its cited source; export blocked on any unsupported claim; named human sign-off; evidence appendix. **Residual risk:** the checker is a model and can miss a claim, or the evidence itself may be wrong or out of date. The product must say plainly that the firm remains responsible for every statement. Measured by A5 and A6a to A6c; a miss rate is stated, never "zero risk". The firm-responsibility statement appears on the sign-off screen and in the export footer (section 2, steps 6 and 7).
- **AI disclosure:** PPN 017 says suppliers' AI use "is not prohibited" but suggests buyers ask for disclosure and confirmation that outputs were checked; it formally covers central government, other authorities "may wish to apply" it (https://www.gov.uk/government/publications/ppn-017-improving-transparency-of-ai-use-in-procurement/ppn-017-improving-transparency-of-ai-use-in-procurement-html). Export header supports this. Buyer rules may change.
- **No wedge, crowded market:** same job sold at £99 or less by CleanTender, BidWriter and Stotles. A demo that works may still be a commodity. Proven wrong if target firms already use a £20 to £50 tool and are content, or bid only a few times a year.
- **Thin pain evidence:** FSB sample size unknown; techUK sample was tech firms.
- **Pack variety and licence:** layouts differ and scans may be images; documents on notices may carry terms beyond the notice's OGL line. Mitigation: hand-picked packs, source log, drop any unclear one.
- **AI budget:** long packs against a $6.10 a month cap. Mitigation: short packs, caching, recorded outputs; larger spend is ask-first.
- **Self-graded evaluation:** the same studio writes the firm, the traps and the checker. Mitigation: key made before model runs, held-out packs, human sample, and the limit stated.
- **Open:** whether a friend's firm bids often enough to matter (Q-4, unknown partner sector); the demo may earn contact points but cannot raise Competition.
