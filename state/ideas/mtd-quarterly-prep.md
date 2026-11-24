# MTD quarterly prep for small practices

- slug: mtd-quarterly-prep
- stage: G0
- market and segment: UK small accountancy and bookkeeping practices (sole practitioners to about 10 staff) with many sole-trader clients brought into Making Tax Digital for Income Tax (from April 2026 above £50k qualifying income; £30k from April 2027; £20k from April 2028), especially clients who are "non-digital" and send paper, PDFs or spreadsheets
- one-line pitch: Clients send bank statements, receipt photos and spreadsheets however they like. The tool extracts and categorises every transaction into HMRC self-employment categories, raises queries back to the client in plain English, and gives the accountant a reviewed, export-ready quarterly update to file through the practice's existing MTD software.

## Problem and who has it

MTD for Income Tax turns one annual self-assessment job per sole trader into four quarterly updates plus a final declaration. Many clients keep poor records and deliver them late. Agents expect much more work, with deadlines that all land at once. Practices are repricing, dropping low-fee sole traders, or considering leaving that market. The filing software itself is cheap (bridging software at about £20 to £60 a year). What costs money is the accountant's time turning messy records into categorised figures each quarter. This is the owner's finance and tax domain.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/publications/research-into-agents-preparedness-for-making-tax-digital-for-income-tax-headline-findings/research-into-agents-preparedness-for-making-tax-digital-for-income-tax-headline-findings-report | 2026-11-23 | HMRC agent research (506 agents in Dec 2024, 502 in Jul 2025). 86% of agents expect to take on additional tasks to support client MTD compliance. 73% have already helped clients with digital record keeping. 27% worry about the extra time needed. |
| https://www.aatcomment.org.uk/audience/members/how-are-members-repricing-their-services-to-reflect-incoming-mtd-changes/ | 2026-11-23 | AAT member accounts. Firms expect 20 to 25% more work once embedded, rising to 30 to 50% during transition. One expects 2 to 3 times the workload ("we'd have to quadruple our fees"). One says about 90% of clients supply tax information at the last minute in January. Firms are considering dropping sole traders. Quarterly deadlines can't be staggered the way VAT can. |
| https://www.icaew.com/insights/tax-news/2025/nov-2025/most-businesses-and-agents-see-no-benefits-to-mtd-income-tax | 2026-11-23 | ABAB 2025 survey reported by ICAEW (3,146 responses, 23% agents). 40.8% expect a significant cost increase from quarterly updates, and 40.7% from digital record keeping. 65.2% see no benefits. |
| https://www.wolterskluwer.com/en-gb/expert-insights/non-digitalised-clients-key-challenges-mtd-income-tax | 2026-11-23 | Wolters Kluwer research (as summarised in search results; page returned 403 on fetch). 59% of accountants say at least half their income tax clients are still non-digitalised. Data quality and reconciliation (47%) and client onboarding (44%) are the top hurdles. Not verified on the page itself. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Dext Solo, receipt and bank capture for MTD sole traders (https://dext.com/uk/partner/pricing, accessed 2026-11-23) | from £2.50 per client per month ex VAT, minimum 5 clients. AI Assist add-on £5 per client. | Strong capture tool, but assumes the client uses an app and the practice uses a full ledger. Weaker on clients who send messy spreadsheets or paper bank statements, and on the query loop with the client. |
| Spreadsheet bridging software, e.g. TaxCalc MTD Quarterly Filer, 123 Sheets (https://www.taxcalc.com/individual-mtdqf, accessed 2026-11-23; prices from a search summary) | about £20 to £60 a year (TaxCalc listed at £24/yr ex VAT; 123 Sheets £19.75/yr first-year discount) | Files numbers that are already categorised. Does nothing about the messy input. |
| Accountant's manual work, priced to the client: £40 to £120 per quarter, or £15 to £60/month extra, per accountancy-firm guides (https://www.accountingfirms.co.uk/?p=161988, accessed 2026-11-23 via search snippet; not fetched) | Substitute cost the practice absorbs or passes on | This labour is what the product cuts. Margin is squeezed for low-fee clients. |
| Full ledger software for the client (Xero, FreeAgent, QuickBooks) | Monthly subscriptions (not priced here) | Many older or non-digital clients won't adopt them (AAT accounts above). |

## Why AI is essential (and the moat)

- The inputs are unstructured: scanned bank statements from many UK banks, receipt photos, owner-made spreadsheets with free-text descriptions. Extracting and categorising them into HMRC self-employment categories (and spotting personal versus business spend, capital items, possible disallowables) needs language and vision models, not rules.
- Query generation: the tool writes plain-English questions to the client ("What was the £420 to B&Q on 3 June: materials for a job, or personal?") and folds the answers back in. This replaces the accountant's chasing emails.
- Confidence scoring: the accountant reviews only low-confidence lines. This is where time is saved.
- Moat (moderate to strong): an evaluation set of UK bank-statement formats and categorisation decisions, built with the owner's tax domain knowledge; a practice-first workflow (bulk client queue for each quarterly deadline); and export formats for the common MTD bridging tools. Big ledgers target app-using clients. This targets the non-digital tail that practices find hardest.

## Rough build plan and Azure cost

- Week 1: upload portal (per-client link), extraction for PDF and CSV bank statements and receipt photos, normalised transaction table, synthetic evaluation set (fictional statements).
- Week 2: categorisation to HMRC self-employment categories with confidence scores and an accountant review UI.
- Week 3: client query loop (email or portal through an adapter, mock by default), quarter totals, CSV export in a bridging-software-friendly layout. No direct HMRC API submission in MVP, so HMRC software recognition is not needed at first.
- Week 4: practice deadline dashboard, audit trail, UK GDPR controls (retention, deletion, processor list), demo with three fictional sole traders.
- Azure (estimate): Container Apps scale-to-zero (about $0 to $5/mo), Azure OpenAI small model plus vision for extraction and categorisation (about $5 to $15/mo at demo volume), Postgres (about $0 to $15/mo), Blob Storage (about $1/mo). Projected total about $6 to $35/mo.

## Risks, and what would prove this wrong

- Financial personal data at scale (bank statements of individuals). This needs strong security, UK GDPR processor terms, and probably UK data residency. Risk is moderate.
- Must not present categorisation as tax advice. The accountant stays the decision-maker and the tool's output is a draft for professional review.
- Policy risk: HMRC thresholds, timelines and quarterly-update rules have already shifted. A further delay or simplification would shrink demand.
- Strong incumbents (Dext, Xero, IRIS, TaxCalc) could add the same messy-input features. Dext's £2.50 per client sets a low price anchor.
- Synthetic test data may not reflect real bank-statement chaos, and real client data is not available to the studio (check this against the red-flag rule).
- Proved wrong if: practice owners say most MTD clients already use an app (Dext or a ledger) and the messy-input tail is small; or extraction and categorisation on realistic statement formats can't reach accuracy high enough to cut review time by about half; or practices refuse to upload client bank data to a new vendor.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 15 | 13 | 10 | 8 | 11 | 3 | 5 | 65 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Tax preparation for accountants is not an off-limits area (it is not lending, insurance, medical or legal advice), provided every output is a draft that the accountant reviews.
- The MVP doesn't use the HMRC API, and emails to clients go through a mock adapter.
- Synthetic data can credibly demo the value. Fictional sole traders, with statements in the main UK bank layouts, receipt photos and messy spreadsheets, are enough to show extraction, HMRC categories, review by confidence score and client queries.
- Real-world accuracy and the time saved stay unproven until practices trial it with their own data. That is a gap in the evidence, not a red flag.

**Falsification findings** (all accessed 2026-11-23)
- Strongest competitor: Dext Solo, from £2.50 per client per month with a 5-client minimum, built for MTD sole traders and landlords (https://dext.com/uk/partner/pricing).
  - Dext's own write-up, published 12 Feb 2026, lists: PDF statement upload with auto-extraction; receipts by app, email or WhatsApp; rules; categories mapped to return boxes; prompts sent to the client's phone about a specific transaction; and direct submission to HMRC (https://dext.com/uk/blog/single/mtd-it-made-simple-how-solo-automates-the-hard-work-for-firms-and-client).
  - That falsifies most of the gap the scout claimed (messy PDFs and the query loop).
  - Three things that page doesn't describe are still open: AI categorisation (Dext describes rules, with AI Assist as a £5-per-client add-on), plain-English questions and answers about a transaction, and one deadline queue across all of a practice's clients.
- Other incumbents and substitutes:
  - Xero's AI capture reads receipts, invoices and rental statements (not bank statements) at no extra cost, since March 2026 (https://www.xero.com/uk/media-releases/major-transformation-to-document-management-capabilities/).
  - AutoEntry reads bank statements at 3 credits a page (https://www.sage.com/en-gb/products/autoentry/, search summary only).
  - FreeAgent claims its "Guess" feature explains over 80% of transactions with over 90% accuracy; that is the vendor's own figure (https://www.freeagent.com/blog/haunted-by-mtd-how-freeagent-uses-ai/, search summary only).
  - Generic AI PDF-to-CSV converters such as DocuClipper and Statement Desk are the cheapest substitute.
- The pain is confirmed and current:
  - HMRC and Verian surveyed 506 and then 502 agents. 86% expect extra tasks and 27% worry about the extra time. Only 19% cite clients' lack of digital skills (https://www.gov.uk/government/publications/research-into-agents-preparedness-for-making-tax-digital-for-income-tax-headline-findings/research-into-agents-preparedness-for-making-tax-digital-for-income-tax-headline-findings-report).
  - The ABAB survey reported by ICAEW (3,146 responses, 23% from agents) found 40.8% expect a significant cost increase from quarterly updates. Checked on the page.
  - The AAT quotes come from five members at four firms, published 8 May 2025. Checked on the page.
  - By 12 Aug 2026, 436,000 people had sent a first update and 570,000 had signed up (https://www.gov.uk/government/news/436000-sole-traders-and-landlords-make-their-tax-digital). That compares with 864,000 in scope (https://www.gov.uk/government/news/act-now-864000-sole-traders-and-landlords-face-new-tax-rules-in-two-months).
- What softens the urgency:
  - There are no penalty points for late quarterly updates in 2026/27; points start on 6 Apr 2027 (same HMRC release).
  - The Wolters Kluwer "59% non-digitalised" claim is still unverified (its page returns 403). HMRC's 19% figure suggests the non-digital tail may be smaller than the file implies.
- Risk is scored 5 for three reasons:
  - At scale, individuals' bank statements can reveal special-category data by inference (health, religion, union subscriptions).
  - Practices will expect strong security assurances from a new vendor.
  - The Azure for Students subscription can't hold real client data long term.

**What would change my mind (re-score on this evidence)**
1. Public Dext, AutoEntry and Xero help docs confirming the gap: no AI categorisation into HMRC categories for clients without a ledger, no free-text query loop with the client, and no bulk quarterly queue. A sharper option is an add-on that sits beside Dext or Xero instead of replacing them.
2. The size of the non-digital tail verified (Wolters Kluwer's 59% on its own page, or an equivalent survey). Also, evidence that practices pay outsourced bookkeepers more than £2.50 per client a month for MTD prep, such as published UK bookkeeping or outsourcing price lists.
3. A desk benchmark on synthetic statements in the five largest UK banks' layouts. It must show extraction and categorisation accurate enough to cut review time by about half, the scout's own test.
4. A data-protection design that the security agent signs off: UK region, retention, deletion, a processor list and a DPIA outline. That would lift the Risk score.

## Evidence pass T-10 (2026-11-23)

All pages accessed 2026-11-23. "Fetched" means the page was read via fetch (a summarising fetch tool, so wording is paraphrase unless quoted). "Snippet" means seen only in a search result. "403" means the page blocked the fetch and I did not guess its content.

### 1. Competitor matrix

Questions: (a) categorises a non-ledger client's transactions into HMRC self-employment categories; (b) free-text query loop with the client about uncategorised items; (c) bulk quarterly queue for a practice's MTD clients.

| Tool | a. Categorise non-ledger client | b. Client query loop | c. Bulk quarterly queue | Source |
|---|---|---|---|---|
| Dext Solo | YES (largely). Solo is for clients not on Xero/QuickBooks. Bank-statement lines are "read, extracted and categorised" into income/expense categories, mapped to return boxes, PDF statements auto-extracted. Categorising is by rules and manual coding; AI Assist (£5/client) is a separate add-on. Spreadsheet import not mentioned. | PARTIAL. A "contextual prompt" lands on the client's phone about a transaction (marketing blog). Free-text plain-English Q&A not documented. Help article on quarterly prep and the Solo features page mention no client query feature. A help article "How to enable client submissions" exists but I could not read its content. | PARTIAL. An MTD IT obligations dashboard lists all of the practice's Solo clients with Overdue/Due/Submitted filters. No bulk actions and no client reminders. Each quarterly update is submitted per income source. | https://dext.com/uk/mtd-it/solo-mtd-software ; https://dext.com/uk/blog/single/mtd-it-made-simple-how-solo-automates-the-hard-work-for-firms-and-client ; https://help.dext.com/en/articles/724414-how-to-prepare-and-submit-quarterly-hmrc-updates-in-dext-solo ; https://help.dext.com/en/articles/522845-using-the-mtd-it-obligations-dashboard ; https://help.dext.com/en/articles/377060-getting-started-with-dext-solo |
| Dext "Prepare" | Not a plan on the UK partner pricing page. Plans shown: Solo (from £2.50/client/month, 5-client min), Essentials and Advanced (10-client min). On the page, the Solo column does not clearly show bank statement extraction. Essentials/Advanced list bank feeds, rental statement extraction and credits for heavier extraction. | Not described on the pricing page. | Not described. | https://dext.com/uk/partner/pricing |
| AutoEntry (Sage) | Extraction YES: 600+ banks' ePDFs read directly; scans and photos go through OCR and verification (up to about 4h). Categorisation into HMRC categories: NOT DOCUMENTED in anything I could read. | No evidence. | No evidence. | https://intercom.help/autoentry/en/articles/4851159-epdf-bank-statements ; Sage product pages returned 403 (https://www.sage.com/en-gb/products/autoentry/, https://sage.com/en-gb/accountants/products/autoentry) |
| Xero (MTD IT for agents and sole traders) | NO for non-ledger clients. Quarterly totals come from transactions in the Xero ledger; HMRC category follows each account code's mapping. AI capture (from March 2026, no extra cost) reads receipts, invoices and rental statements, not bank statements. | UNCONFIRMED. Xero "Ask" exists but I found no Xero help page on it. The only evidence is product-idea forum posts (snippet) asking for attachments and for uncoded-line reports to be sendable via Ask. | NOT CONFIRMED. The MTD IT FAQ and partner campaign page do not mention bulk views. Practice Manager is pitched as a deadline tracker (snippet only). | https://www.xero.com/uk/programme/making-tax-digital/it-faqs/ ; https://www.xero.com/uk/media-releases/major-transformation-to-document-management-capabilities/ ; https://www.xero.com/uk/campaign/partner/making-tax-digital-for-income-tax/ ; https://productideas.xero.com/forums/967136-banking-chart-of-accounts (snippet) |
| FreeAgent | Ledger only. "Guess" suggests explanations for bank-feed transactions (vendor claim: over 80% explained at over 90% accuracy, no date). AI rental-statement reading is for FreeAgent for Landlords. No bank-statement PDF extraction described. | NO. The page says AI handles no client queries. | YES. Bulk quarterly approval requests to clients, and bulk filing for practice partners. The blog says batches of up to 100; a search snippet said 25. The help page itself returned 403, so the limit is unresolved. | https://www.freeagent.com/blog/haunted-by-mtd-how-freeagent-uses-ai/ (29 Oct 2026) ; https://www.freeagent.com/blog/new-features-mtd/ ; https://support.freeagent.com/hc/en-gb/articles/34419697730450 (403) |
| QuickBooks (Intuit) | Ledger only. Sole Trader Plus uses AI to map bank transactions and expenses to categories. "Income Tax AI" is a validation tool (snippet). | Not mentioned. | Not mentioned. | https://quickbooks.intuit.com/uk/press/intuit-launches-time-saving-tools-for-sole-traders-to-tackle-making-tax-digital (5 Mar 2026) |
| Sage (MTD for Income Tax Agent in Sage for Accountants) | NOT STATED. It reviews incoming data and flags anomalies; categorisation is not mentioned. It is unclear whether non-Sage data is accepted. | PARTIAL, CLOSEST NEW COMPETITOR. The agent "requests missing items" and can chase missing records by email, WhatsApp or in-app notification. It is not stated whether this is free-text per-transaction Q&A. | PARTIAL. It flags in-scope sole traders, sets up quarterly reporting jobs in advance, and keeps the workflow in one hub (live now, May 2026 release). Bulk handling is not stated explicitly. | https://www.sage.com/en-gb/blog/agentic-ai-in-practice-how-sage-is-reshaping-the-future-of-accounting-with-mtd/ ; https://www.sage.com/en-gb/blog/mtd-income-tax-accountant-practice-plan-2026-2027/ ; Sage press release and newsroom pages returned 403 |
| IRIS (Personal Tax, Elements) | NOT YET. From 2026 Personal Tax accepts quarterly figures only by CSV import (headers A/c No., Description, Amount, Date). It auto-allocates dated postings to quarters and remembers category choices. PDF bank statement import is "coming soon". | NOT YET. An AI assistant that drafts chasing emails is "coming soon". | PARTIAL. Elements has an MTD client list tool and an obligations widget with colour-coded status. | https://www.iris.co.uk/support/knowledgebase/kb/mtd-quarters-how-to-import-data-per-quarter/ (snippet) ; https://www.iris.co.uk/blog/accountancy/the-true-cost-of-mtd-and-how-the-latest-tech-can-help-you/ |
| TaxCalc MTD Quarterly Filer | NO. Reads summary totals from a spreadsheet and is not bookkeeping software. From £24/yr. | No. | Not for this product. A separate "Batch Filer" add-on exists; I did not read it. | https://www.taxcalc.com/individual-mtdqf |
| Capium | Bulk upload of bank statements (PDF or CSV) exists. Categorisation and MTD IT flow not found. | Not found. | Not found. | https://capium.freshdesk.com/support/solutions/articles/9000271586-capium-365-adding-bank-statements-via-csv-or-pdf (snippet) |
| BTCSoftware | Nothing found in search. Not checked further. | Not found. | Not found. | n/a |
| Bots for That "MTD Command Centre" (launched 11 Mar 2026) | NO. It is an oversight dashboard, not a bookkeeping tool. | NO. | YES for monitoring only: all clients' obligations from HMRC data. It does not file. Vendor claims only. | https://www.accountingweb.co.uk/node/229265 (snippet) |
| Other 2026 AI-native names (Briefcase, Apron "William") | Not verified. Briefcase is a general ledger and Apron's article returned 403. Neither is confirmed as MTD IT with bank-statement categorisation. | n/a | n/a | https://www.accountingweb.co.uk/tech/accounting-software/apron-unwraps-bookkeeping-agent-william (403) |

Reading of the matrix:
- (a) is not a clean gap. Dext Solo already serves clients with no ledger and extracts and categorises PDF bank statements into HMRC boxes, at £2.50. The scout's original gap on this point is gone.
- (b) is partly closed. Dext sends contextual phone prompts and Sage's agent chases missing records. I found nothing that generates plain-English per-transaction questions and folds the free-text answers back in. "Not found in public docs" does not prove "does not exist", and both vendors are shipping AI features fast.
- (c) is partly closed. Dext, Sage, IRIS, FreeAgent and Bots for That each have some form of multi-client view. FreeAgent has true bulk approve-and-file, but only for FreeAgent clients.
- No tool I could verify takes messy inputs (scanned or photographed statements, owner-built spreadsheets, mixed paper) from heterogeneous clients and produces reviewed, categorised quarter totals that drop into any bridging tool. That is a narrower gap than the original pitch.

### 2. Wedge recommendation

Best supported by the evidence: **the non-digital tail, delivered as a vendor-neutral add-on that outputs to the practice's existing filing tool.** Scope it to scanned and photographed statements, spreadsheets and mixed paper from sole traders who will not adopt an app or ledger. Output is reviewed, categorised quarter totals as CSV in the formats that bridging tools take. IRIS is the concrete example: its Personal Tax module accepts quarterly figures only by CSV import with documented headers, and remembers category choices (snippet).

Why this wedge:
- Spreadsheets are where the verified gaps are. TaxCalc's quarterly filer reads spreadsheet totals but does no categorisation. IRIS wants clean CSVs. Dext's docs mention no spreadsheet import. AutoEntry's OCR path covers scans but its categorisation is undocumented.
- It sits beside Dext, Sage, IRIS and TaxCalc, and doesn't ask the practice to switch ledger.

Why not the others:
- **Practice-side deadline batching:** Crowded. Dext's obligations dashboard, FreeAgent's bulk approve-and-file, Sage's quarterly job creation, IRIS's obligations widget and Bots for That all exist. It is weak as a standalone wedge, though a queue is needed inside the product.
- **Landlords versus sole traders:** Property income does enter MTD ITSA. But Dext Solo handles rental statements (SA105), FreeAgent for Landlords has AI rental-statement reading, and Xero's AI capture reads rental statements. No gap found. It overlaps with no other studio idea (as the board asked me to note), but that is not a competitive advantage.
- **Query loop:** The loop alone is not defensible, since Dext and Sage already ship partial versions. It only matters if tied to messy inputs.

What would break the wedge: Dext Solo adding spreadsheet and scan handling with AI categorisation (it is already part way), or practices telling us the tail is small (see size below).

### 3. Size and price evidence

**Who is in scope (HMRC)**
- April 2026 (income over £50,000): 864,000 people. About 75% had an authorised agent, so about 648,000 (my arithmetic). April 2027 (£30,000.01 to £50,000): 1,077,000, about 63% with an agent, so about 679,000 (my arithmetic). April 2028 (£20,000.01 to £30,000): 975,000, about 59% with an agent, so about 575,000 (my arithmetic). Based on 2023/24 data, published 13 Aug 2025. Source (fetched): https://www.gov.uk/government/statistics/making-tax-digital-for-income-tax-business-population-statistics/making-tax-digital-for-income-tax-business-population-statistics-commentary
- HMRC release of 5 Oct 2026 confirms about 1,077,000 more from April 2027, from 2024/25 returns (fetched): https://www.gov.uk/government/news/sole-traders-and-landlords-earning-more-than-30000-urged-to-act-now
- Earlier HMRC pre-launch estimates were about 780,000 and about 970,000 (snippet). So the in-scope numbers have been revised upward, which supports reach. The 13 Aug 2025 data gives about 1.3 million in agent-using accounts for April 2026 plus April 2027 combined (648k + 679k, my arithmetic).
- Uptake caveat from the file: by 12 Aug 2026, 436,000 had sent a first update and 570,000 had signed up (https://www.gov.uk/government/news/436000-sole-traders-and-landlords-make-their-tax-digital). I did not re-fetch it in this pass.

**Size of the non-digital tail**
- The Wolters Kluwer "59% of accountants say at least half their income tax clients are non-digitalised" figure is **still not verified on its own page**. https://www.wolterskluwer.com/en-gb/expert-insights/non-digitalised-clients-key-challenges-mtd-income-tax returned 403 again, as did the March 2026 WK report page. The 59% figure appears in a search snippet attributed to a WK piece dated 15 April 2026, with the sample described as 100 UK accountants (snippet only, unverified).
- What is verified on a page is a secondary report of the same March 2026 WK survey: half of respondents put 50% to 69% of their income tax clients in the non-digitalised group; sample size and survey date are not stated; the article is dated 31 Mar 2026 (fetched, https://www.accountex.co.uk/insight/?p=13123). The same snippet set shows earlier WK figures of 47% (Sept 2025) and 42% (press release), so the number has moved between surveys.
- Treat it as a vendor-run survey of a small, self-selected sample. "Non-digitalised" also does not mean "can't use Dext's app".
- Counterweight: the HMRC agent research found only 19% of agents cite clients' lack of digital skills as a worry (as quoted in the validator notes).
- No ICAEW, AAT, ACCA, ATT, CIOT or HMRC figure on the share of non-digital clients found in this pass. This remains the weakest part of the evidence.

**Prices practices charge or pay**
- One UK accountancy firm lists MTD Income Tax quarterly updates from £35.00 per month ex VAT as an add-on, prepared from records the client supplies (fetched): https://theaccountancy.co.uk/making-tax-digital-income-tax . That is about £105 a quarter (my arithmetic), against Dext Solo's £7.50 a quarter per client. It is a client-facing fee, not an outsourcing price, and a single firm.
- Sage's illustrative tiers for practices: Bronze £35 to £50/month, Silver £65 to £85, Gold £100 to £150, ex VAT and software. Labelled in the article as an example, not market data (fetched): https://www.sage.com/en-gb/blog/pricing-for-mtd-how-to-charge-more-and-prove-why-it-s-worth-it/
- IRIS: "one to two hours per client per quarter, assuming the data arrives clean"; fees expected to rise 15 to 25%, some practices considering 50 to 75% (fetched): https://www.iris.co.uk/blog/accountancy/the-true-cost-of-mtd-and-how-the-latest-tech-can-help-you/
- Outsourced bookkeeping for sole traders, £100 to £250 per quarter in one cost guide (snippet only, vendor blog): https://www.vjmglobal.com/feeds/blog/outsourced-bookkeeping-rates-uk
- **Honest gap:** I found no published price list for outsourced MTD quarterly prep per client. The "practices pay more than £2.50" claim rests on the above client-facing fees and the IRIS time estimate, not on direct outsourcing rates. Method for a rough ceiling (estimate): if a practice charges about £35/month and spends 1 to 2 hours a quarter on clean data (more on messy data), a tool priced at £5 to £10 per client per month would be 14% to 29% of that fee. Whether practices would pay that depends on real time saved, which is item 3.

### 4. Risks that make it worse

- **Incumbents are moving fast on AI for MTD.** Sage's MTD IT Agent (live, expanded May 2026); Dext AI Assist (March 2026, snippet) and an AI Agent beta (Dec 2025, article does not mention MTD or categorisation); Xero AI expansion (Aug 2026, snippet); Intuit Accountant Suite and Income Tax AI (2026). None is confirmed to be exactly this feature, but any could add scan/spreadsheet handling.
- **Free tools:** HMRC says it does not provide software and I found no announcement of an HMRC free tool. Free third-party options exist (Sage Sole Trader and Landlord, Pandle, Zoho Books, snippet), which affect clients' choices but not the practice's labour.
- **Price anchor:** Dext at £2.50 per client is hard to undercut for any practice that already uses it.
- **Timing:** no late-submission penalty points for quarterly updates until 6 April 2027 (per the validator's note of the same HMRC release), so practices may defer buying.
- **Evidence quality:** WK 59% unverified; sample sizes small; most competitor claims are vendor marketing; four key pages (Sage newsroom, FreeAgent help, AutoEntry product, Apron) returned 403.
- **Kill rule:** pipeline.md says an idea that fails a gate twice is killed. A second REVISE at G1 would end it.

### 5. Items 3 and 4 (not done here)

- **Item 3, desk benchmark.** Build synthetic statements in the layouts of the five largest UK retail banks (clean ePDF, scanned/photographed, CSV export), a few owner-made spreadsheets with free-text descriptions, and about 200 labelled transactions per client persona. Measure extraction accuracy (field-level), HMRC-category accuracy, and the share of lines routed to review at a confidence threshold. Success is review time cut by about half versus a manual baseline (the scout's own test). Compare against Dext Solo and a generic PDF-to-CSV converter if a free trial is permitted (that needs approval to sign up). Real client data is not available, so the benchmark proves only the mechanics.
- **Item 4, security sign-off.** UK-region hosting, retention and deletion rules, processor and sub-processor list, DPIA outline (special-category inference from bank statements), practice-as-controller / studio-as-processor terms, and a plan for moving off the Azure for Students subscription before any real data. The security agent signs this off.

### 6. Bottom line

The evidence weakens the original pitch more than it strengthens it. Dext Solo already covers (a) for clients without a ledger, partly covers (b) with phone prompts, and its dashboard partly covers (c). Sage's MTD IT Agent chases missing records and creates quarterly jobs, FreeAgent bulk-files, and IRIS is moving toward PDF import and AI chasing. What survives is a narrower wedge: scanned, photographed and spreadsheet inputs, with plain-English per-transaction queries and vendor-neutral CSV output. The size of that tail is unproven, since the WK 59% is unverified on its own page and the HMRC 19% digital-skills figure points the other way. A re-score could plausibly move Pain by about 1 point (HMRC in-scope numbers revised up to 1,077,000 for April 2027, with 63% using agents) and Pay by 0 to 1 (a £35/month client fee and IRIS's hours estimate support willingness to pay, but no outsourcing price list was found). Competition might rise from 3 to 4, at most 5, only if the validator accepts the narrow wedge. AI, Reach, Build and Risk should not move without items 3 and 4. A plausible range is 66 to 69, and 70 is reachable only if the validator is generous on Competition and Pay and the item 3 benchmark then lifts AI or Build. I would put the chance of reaching 70 at below 50%, and the real decision for the board is whether to spend a second gate attempt on a narrowed idea, given the kill rule.

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 65 | This batch's strongest pain (HMRC and professional-body data, recurring every quarter and widening in April 2027), but Dext Solo already extracts PDF statements, prompts clients and files to HMRC from £2.50 per client, and holding clients' bank-statement data pulls the risk score down.

## T-12 pilot (run f468, 2026-11-24T03:34:02Z; branch p/mtd-quarterly-prep/T-12, qa check PASS at a776c78)
- 5 synthetic docs, 32 lines each, fictional bank. One call each to gpt-5.4-pro (default reasoning effort; "low" was rejected).
- Clean PDF, CSV export: 100% date/amount/description, 93.8% category. Messy owner sheet: 93.8% fields, 84.4% category. Scan and phone photo: failed runs (all 8,000 output tokens spent on reasoning), so no image accuracy yet.
- Review time vs manual (assumed seconds per line): 51-56% on the three working docs. With 120 s charged per wrong auto-accepted line (4 such lines, 3 the same tyres merchant), it is 70-81%: the "halves review time" test fails on this pilot.
- Tokens: 5.7k in, 27.6k out (81% reasoning), 70-150 s per doc. A full benchmark on the pro model would cost about the whole $80 credit (BUDGET.md), so it waits for a mini deployment (Q-7).
- Read: mechanics work on digital inputs, but digital inputs are what Dext already handles; the wedge (scans, photos) is untested. No second G1 attempt until images are measured.
