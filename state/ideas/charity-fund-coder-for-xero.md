# Charity fund coder for Xero

- slug: charity-fund-coder-for-xero
- stage: G0
- market and segment: UK small and mid-size charities (and the bookkeepers or accountants who serve them) that keep books in Xero and need restricted and unrestricted fund accounting and a Statement of Financial Activities (SOFA) under SORP.
- one-line pitch: Reads grant agreements and donor letters, turns the restrictions into fund-coding rules, tags every Xero transaction to a fund, and produces fund balances and a draft SOFA with the working shown for the bookkeeper to approve.
- found by: incumbent-refusal method (T-27)

## The refusal (quoted)
Xero's Product Ideas board. Three related requests:
1. "Reports: Support for charity reporting", 51 votes, status "submitted", posted 20 October 2022. The request: no charity report templates, "Profit (Loss)" cannot be renamed Surplus/Deficit, no restricted and unrestricted funds. A commenter (Neal Trup, 22 May 2026) says he has asked Xero repeatedly for a charity chart of accounts and "it seems a low priority." https://productideas.xero.com/forums/967127-practice-tools/suggestions/45838657-reports-support-for-charity-reporting (read, accessed 2026-11-23).
2. "Organisation settings - Charity mode", about 103 votes. A Xero team reply is reported by the search tool as "not currently on our roadmap but it is a suggestion we will continue to monitor while the team looks at report development." I could not open this page (404 on fetch), so this quote is second-hand from a search summary. Verify at https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/44960911-organisation-settings-charity-mode (accessed 2026-11-23, unverified).
3. "Xero Tax (UK) | CiC" and "CT600E for charities" ideas show the same gap on the filing side (https://productideas.xero.com/forums/967127-practice-tools/suggestions/46904683-xero-tax-uk-cic, read, accessed 2026-11-23; 28 votes, "Gaining Support", Xero admin 14 September 2026 gives no timeline).

## Problem and who has it
Xero has no fund accounting. Charities use tracking categories (only on the profit and loss, not the balance sheet, per a user request at https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/48637475-allow-for-charity-funds-in-balance-sheet, search result only). Every grant has conditions, and someone has to read the agreement, decide which fund each cost belongs to, and rebuild the SOFA in Excel or pay an accountant to convert Xero reports. SORP 2026 applies to accounting periods starting on or after 1 January 2026 (gov.uk, via search summary; ICAEW says 31 December 2026 year-ends are the first affected), so the work is changing this year.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://productideas.xero.com/forums/967127-practice-tools/suggestions/45838657-reports-support-for-charity-reporting | 2026-11-23 | 15 comments. Karen Tonks (11 January 2024) pays an accountant to convert Xero reports into Scout and Charity Commission formats. Neal Trup (22 May 2026) built a SoFA with Xero report writing and tracking-category prefixes. Elaine Tierney (21 May 2026) keeps a detailed SoFA in Excel mapped by hand. Jaspreet Lally (21 March 2025): clients on Sage Funds are blocked from moving to Xero. Emily McEwan (9 March 2025) uses another provider for SORP accounts. |
| https://productideas.xero.com/forums/967127-practice-tools/suggestions/46904683-xero-tax-uk-cic | 2026-11-23 | Practices say they will move clients to TaxCalc; Abi Aiyegbayo (9 January 2026) says Xero cannot meet CIC and charity needs. |
| https://www.icaew.com/insights/viewpoints-on-the-news/2026/sep-2026/charities-need-to-get-ready-for-sorp-2026 | 2026-11-23 | Search result only (title): ICAEW says charities need to get ready for SORP 2026. Not read in full. |
| https://www.gov.uk/guidance/changes-to-charity-accounting-and-reporting | 2026-11-23 | Search result only (title). Government guidance on the SORP and threshold changes. Not read in full. |
| https://www.xero.com/uk/guides/non-profit-accounting/ | 2026-11-23 | Xero's own guide (search result) says tracking categories can tag restricted funds; it does not claim SORP reports. |

Independent pain signals: (1) the Xero thread's accountant-conversion and Excel workarounds; (2) practices leaving Xero for TaxCalc or Sage Funds (lost clients); (3) the SORP 2026 change date. A cost figure for a charity bookkeeper or independent examiner is still missing; needs a UK fee source.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| TaxCalc Charity Accounts (add-on to Accounts Production; imports a Xero trial balance; allocates postings to funds; SOFA; iXBRL filing). https://www.taxcalc.com/products/charity-accounts (search result, accessed 2026-11-23) | Price not read | Year-end accountant tool. Needs a TaxCalc Accounts Production licence. It starts from a trial balance, so it does not code transactions to funds during the year from grant terms. This is the main threat to the idea. |
| Cheetah (custom report service, Xero listing https://apps.xero.com/uk/function/reporting/app/cheetah) | "Price guide" on the vendor site; an implementation fee, waived for charities per its founder's comment; no amount found | Custom build; no SOFA template mentioned on the listing |
| XO Report (Excel add-in) | USD 9.90 / 14.90 / 29.90 / 49.90 per month (Malaysia listing, via search result) | No SOFA template mentioned |
| Access Financials and specialist charity ledgers (Liberty Accounts, Iplicit, Pegasus per a search result) | Not read | Means leaving Xero; vendor claims of native SORP reporting |
| Accountant converting reports by hand | Karen Tonks pays an outside accountant; no fee given | Per-year manual cost |

## Add-on search result (required check)
Searches run 2026-11-23: "Xero charity fund accounting add-on app restricted unrestricted funds SORP statement of financial activities 2026", "apps.xero.com uk charity OR not-for-profit fund accounting SOFA app Xero marketplace", "Cheetah Xero charity SOFA report Excel app pricing", "TaxCalc charities module charity accounts SORP SOFA Xero 2026". I read the Xero "Not for profit" marketplace page for the UK (https://apps.xero.com/uk/industry/not-for-profit, 24 apps, accessed 2026-11-23). None of the 24 mentions SOFA, SORP or fund reporting. Calxa lists "Not-for-Profit Reporting" with no detail (check before G1). infoodle and Beacon are charity CRMs (Gift Aid, donations). TaxCalc does cover the year-end SOFA from a Xero trial balance, so the idea is only open if it targets in-year fund coding from grant documents and bookkeepers, not the year-end accounts. If Calxa or another app already does fund coding, KILL.

## Why AI is essential (and the moat)
Fund coding needs reading free-text grant agreements, award letters and donor emails ("to be spent on the youth programme in 2027 only"), then applying those conditions to bank lines and bills with reasons. Rules-only tools cannot read the documents. Xero has said charity reporting is not on its roadmap, and TaxCalc starts after the books are done. Moat: a library of restriction patterns and a reviewer-friendly audit trail (every coding decision linked to the sentence in the agreement). Doubt: a bookkeeper can do this in an afternoon for a small charity; the saving only matters at roughly 10+ funds or multi-charity bookkeepers.

## Rough build plan and Azure cost
- Inputs: Xero transactions through the API, grant agreements (PDF, Word).
- Pipeline: extract restrictions into a structured fund register (amount, purpose, dates, conditions) -> propose a fund and activity tag for each transaction with a cited reason -> reviewer approves -> write tracking categories back to Xero -> report: fund balances, restricted fund movements, draft SOFA, and a "restriction breach" list.
- Demo on synthetic data: yes. Write 8 fictional grant agreements for a fictional charity and a Xero demo company with 12 months of transactions. All public or synthetic; no paid service in the loop.
- Azure estimate (not yet costed): small web app and Azure OpenAI; expected tens of pounds per month at demo scale. Architect to confirm.

## Risks, and what would prove this wrong
- TaxCalc, Sage or Access add in-year fund coding (a month-scale move for them).
- Accountants say the saving is too small, or that a Xero-only practice is rare (many charity accountants already use Sage or specialist ledgers).
- Charity accounts are regulated: the tool drafts only, with a named human sign-off. No legal advice.
- Reach: the idea page quotes "over 160,000 charities in England and Wales" (Nigel Kay comment; unverified). The share on Xero is unknown. Do not size from this without the Charity Commission register.
- Sector: a UK partner who sells to charity bookkeepers or accountants is unknown.

## Injection notes
A comment in the Xero thread (Jarvin Ong, 11 November 2026) promotes his own product (Cheetah). It is marketing, not an instruction; not followed. No instruction-like text seen.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 11 | 6 | 7 | 6 | 10 | 5 | 7 | **52** |

## Validator notes (2026-11-23)

**Verdict: REVISE (park).** The gap is real. Calxa (Xero UK listing) says nothing about funds, SOFA, SORP or restricted funds, and TaxCalc Charity Accounts works at year end (funds and activities, "SORP-compliant", from £87 a year, but it needs Accounts Production). So no in-year tool that codes transactions to funds from grant terms was found. But the idea fails on Pay and on how essential the AI is:
- Small charities on Xero are the most price-sensitive buyers the studio has scored. Xero itself is discounted for charities, and the year-end tool costs from £87 a year.
- Charities with many restricted grants, the ones the saving matters to, tend to buy dedicated fund ledgers such as Access Financials (from £139 per user a month, minimum five users) and leave Xero.
- The hard part of fund allocation is splitting salaries and shared costs across funds. That depends on timesheets and board decisions, not on anything written in the grant agreement or the bank line. Reading 5 to 20 grant letters a year is a short job.
- A practitioner guide already shows a bookkeeper how to do this with a general chatbot: give it the fund list and grant terms, and it proposes a fund and a reason for each bank line.

How each score was reached:
- **Pain 11/20.** The charity-reporting thread has 51 votes and is still "Submitted" (status page 17 March 2023). Workarounds: Excel SoFA, tracking-category prefixes, paying an accountant to convert reports (thread re-read 2026-11-23). SORP 2026 applies from 1 January 2026 periods. But the pain sits mainly at year end, where TaxCalc already plays. The "charity mode" refusal quote (about 103 votes) is still unverified: the page returned 404 again on 2026-11-23.
- **Pay 6/20.** Anchors: TaxCalc Charity Accounts from £87 a year (an accountant tool). Generic bookkeeper rates are £20 to £50 an hour or £100 to £500 a month (Xero UK guide, via search; not charity-specific). Access Financials from £139 per user a month, minimum five users (Access Group, via search). No charity paying for in-year fund coding was found.
- **AI 7/15.** Turning free-text grant conditions into a fund register is real LLM work. The rest is not: coding transactions can mostly be done with Xero bank rules and tracking categories once the register exists, and Xero JAX auto-reconciliation (beta; a paid AI add-on on UK Simple and Ignite plans) already predicts coding. Substitutes: a general chatbot used with the grant terms, or Cheetah custom reports.
- **Reach 6/10.** Buyers are findable through the Charity Commission register (171,885 charities at end of September 2026), the ICAEW charity community, Charity Digital and the Xero App Store. The real buyer is the charity accountant or bookkeeper, and the studio's partner sector is unknown. Many charity accountants use TaxCalc or Sage already.
- **Build 10/15.** The Xero API, tracking categories and a demo company are free. But Xero tracking does not cover the balance sheet, so fund balances and carried-forward reserves must be computed outside Xero and kept reconciled. A SORP 2026 SOFA template plus fund rollforward in four weeks is tight.
- **Competition 5/10.** TaxCalc (year end), Calxa (programme budgets and tracking-category reports, 4.98 from 145 reviews, nothing on funds), Cheetah (custom reports), dedicated ledgers (Access, Liberty, Iplicit, Pegasus), and general chatbots. The in-year, grant-driven slot is open but narrow. TaxCalc or Calxa could add rules-based in-year fund tagging in about a month.
- **Risk 7/10.** Charity accounts are regulated, and a wrong restriction causes a breach of trust and audit findings, so the tool must draft only with a named human sign-off. This is accounting, not legal advice, although interpreting grant conditions is close to contract reading. Donor names in bank lines and Gift Aid data mean moderate personal data.

How I tried to kill it:
- Read the Calxa and Calxa Xero UK listings and the TaxCalc page on their own sites.
- Re-read the Xero idea thread.
- Searched for AI fund-coding tools and Xero JAX.
- No direct competitor was found, which is why this is REVISE, not KILL.

What would move it to 70+ (all needed):
1. Pay: three or more published fees from UK charity bookkeepers or independent examiners that price restricted-fund allocation or SOFA preparation separately, at £300 a year or more per charity. Or a vendor charging £30 a month or more for in-year fund tracking on Xero.
2. AI: a desk sample of 10 public UK grant agreements (National Lottery Community Fund, council grants, trusts) showing that the restriction terms are varied and hard to parse, and that applying them changes how transactions are coded beyond simple project tags.
3. Segment: evidence that a practice-side buyer (a bookkeeper with 10 or more Xero charity clients) exists in numbers, for example from Xero advisor directory filters or ICAEW charity community membership.
4. A repeat check that TaxCalc, Calxa and Xero JAX have not added fund tagging.

Without these, the ceiling is about 60. If the second attempt fails, kill it.

Sources (all accessed 2026-11-23):
- TaxCalc Charity Accounts, own page: https://www.taxcalc.com/products/charity-accounts (from £87 a year; add-on to Accounts Production; unlimited funds and activities; "SORP-compliant")
- Calxa, Xero UK listing: https://apps.xero.com/uk/app/calxa (Not-for-Profit Reporting tag; tracking-category reports; no funds, SORP or SOFA; 30-day trial; no GBP price)
- Calxa's own not-for-profit page: https://www.calxa.com/not-for-profit-reporting (returned 404)
- Xero charity-reporting idea, re-read: https://productideas.xero.com/forums/967127-practice-tools/suggestions/45838657-reports-support-for-charity-reporting
- Xero "charity mode" idea (returned 404 again): https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/44960911-organisation-settings-charity-mode
- Access Financials pricing, via search summary: https://www.theaccessgroup.com/en-gb/finance/sectors/charities-not-for-profit/best-accounting-software-for-charities/
- Xero UK bookkeeper rates guide, via search summary: https://www.xero.com/uk/resources/small-business-guides/bookkeeping/hire-bookkeeper/
- Practitioner guide to the AI fund-coding substitute (search result): https://sagnikbhattacharya.com/blog/nonprofit-ai-bookkeeping-restricted-funds
- Xero JAX auto bank reconciliation, UK: https://www.xero.com/uk/campaign/auto-bank-reconciliation/
- Charity Commission, July to September 2026 data (171,885 charities): https://www.gov.uk/government/publications/charity-commission-casework-and-registrations-data-2026-to-2027/casework-and-registrations-data-july-to-september-2026
- Not checked: the Charity Commission income-band page returned 403, so the count of charities under £100k is unknown, and Sage and QuickBooks marketplaces were not browsed for fund add-ons.

## Gate log
- 2026-11-23: G0 written by scout (T-27). Add-on check run; TaxCalc covers year-end SOFA, in-year fund coding from grant terms not found.
- 2026-11-23: Validator (T-28) scored 52/100. REVISE (park): the in-year gap holds (Calxa has no fund features, TaxCalc works at year end from £87 a year), but Pay is weak, the AI is mostly one-off reading of grant terms, and a general chatbot is a working substitute. A second failure kills it.
