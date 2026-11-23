# Rates 2026 bill recalculator

- slug: rates-2026-bill-recalculator
- stage: G0
- market and segment: UK (England) multi-site retail, hospitality and leisure operators, and their finance teams or accountants, who receive dozens of council rates bills a year.
- one-line pitch: Recomputes every 2026/27 business rates bill from the rateable value, the right multiplier, transitional relief, Supporting Small Business relief and other reliefs, flags the bills where the council's number differs, and drafts the query to the council.

## Problem and who has it
- From 1 April 2026 England has five multipliers (small and standard, with lower retail, hospitality and leisure (RHL) versions, plus a high-value one), transitional relief with a supplement, and a Supporting Small Business cap. RHL relief became lower multipliers that apply to occupied qualifying properties only.
- Each council bills its own properties. Harborough council says some 2026/27 bills for accounts that previously got RHL relief were issued incorrectly.
- A multi-site operator with 20 sites receives 20 bills in different layouts. Checking each against the rules is slow, so it mostly is not done.
- This is bill validation, separate from challenging the valuation (see rates-2026-valuation-check-workbench).

## Forcing function
- New multipliers, relief schemes and the transitional scheme from 1 April 2026 to March 2029. Bills run annually and instalments are being paid now. Time limit to recover overpaid rates: UNVERIFIED, the validator must find the council or regulations rule.
- Source for the scheme rules: https://www.gov.uk/government/publications/business-rates-relief-2026-supporting-small-business-relief-local-authority-guidance/business-rates-relief-2026-supporting-small-business-relief-local-authority-guidance (accessed 2026-11-23).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.harborough.gov.uk/info/20063/business_rates/622/important_information_about_your_202627_business_rates_bill | 2026-11-23 | Council admits some 2026/27 bills were issued incorrectly for accounts that had RHL relief |
| https://www.westnorthants.gov.uk/business-rates/new-business-rates-multipliers-1-april-2026 | 2026-11-23 | Council pages list multipliers; one page omits the 38.2p small RHL rate and another gives it (council inconsistency, from search summary) |
| https://www.gov.uk/government/publications/effects-of-the-business-rates-retail-hospitality-and-leisure-multipliers-and-high-value-multiplier/effects-of-the-business-rates-retail-hospitality-and-leisure-multipliers-and-high-value-multiplier | 2026-11-23 | National multipliers fell 6.7p and 7.5p at the revaluation; RHL and high-value multipliers explained |
| https://www.cornwall.gov.uk/business-trading-and-licences/get-money-off-your-business-rates/transitional-relief-and-supporting-small-business-schemes | 2026-11-23 | Relief applied automatically; business told to contact council if not shown, so errors are found by the payer |
| https://www.eddisons.com/valuations-and-advisory/business-rates/business-rating-appeals | 2026-11-23 | Rating advisers sell 'business rates audits' on a percentage of savings with no upfront fee |
| https://findajob.dwp.gov.uk/details/17741679 | 2026-11-23 | Business Rates Surveyor job at £35,000 to £40,000 plus commission, staff cost for the manual work |
| https://www.designingbuildings.co.uk/wiki/CCA_(Check,_Challenge,_Appeal) | 2026-11-23 | Background on the system (not opened; low weight) |

Pain signals so far: one council admission, relief complexity, audits sold on commission. Weak spot: no complaint volume yet. Next scout step is to look for forum or Trustpilot complaints on wrong 2026 bills.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Eddisons 'business rates audits' (https://eddisons.com/services/business-rates) | Percentage of savings, no upfront fee | A human audit; pages show no self-service tool |
| Council self-service accounts and calculators (e.g. https://www.camden.gov.uk/en/business-rates-multiplier-2026-to-2027) | Free | One authority at a time; they calculate your bill but do not audit |
| Accountant or in-house finance check | Staff time | Not systematic |
| ERP or AP tools (Dext, Xero) | Subscription | They capture the bill amount; they do not recompute it (not checked on their pages; validator to verify) |

Gap that survives (provisional): a cross-council, multi-site recalculation with a relief explanation. Not yet checked: whether property-cost software (e.g. lease and portfolio systems) already does this. The validator must check before scoring.

## Why AI is essential (and the moat)
- Councils' bill PDFs and letters differ in layout; AI extracts RV, period, multiplier, relief lines. Calculation is deterministic code against the gov.uk rules, so there are no hallucinated numbers. Moat is the rules engine, test suite and council layout library; Vishal's tax-calculation edge fits.

## Public dataset for the demo
- Multipliers, relief rules and statistics on gov.uk (OGL v3.0).
- RVs for illustration: VO public search (VO terms limit use to NDR purposes; see the workbench idea for licence doubts: https://www.tax.service.gov.uk/view-my-valuation/terms-and-conditions).
- Demo uses synthetic bills for 15 sites across 6 invented councils, with deliberately seeded errors. No customer data needed.

## How the selling partner could reach buyers
- Finance directors and accountants of hospitality and retail groups, trade bodies (UKHospitality, BII for pubs), franchise networks. Named channel to be confirmed by Vishal's friend.

## Rough build plan and Azure cost
- Bill extraction, rules engine for 2026/27 (and 2023 to 2025 history for look-back), exceptions list, council query letters. About 3 to 4 weeks. Azure about £15 to £35 per month (estimate).

## Risks, and what would prove this wrong
- Biggest: errors may be rare. Test: gather 30 public examples of wrong bills or council notices; if error incidence looks below a few percent per bill, the value is mostly peace of mind.
- Councils do apply relief automatically, so the commercial case may be a small compliance tool, not a money finder.
- Thin willingness to pay for a pure checker. A bundle with idea 1 could carry it.
- Not tax advice: it recalculates published rules; the owner or accountant decides.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 9 | 10 | 7 | 6 | 11 | 2 | 9 | 54 |

## Validator notes (2026-11-23)

**Verdict: REVISE, 54.** A firm score from a lighter pass, as briefed.

**Main reason: Paddl already sells this to multi-site hospitality**, at £69 per location per month or £703.80 a year (own page, fetched). It:
- reads uploaded bills (PDF or photo) with AI, extracting the RV, multiplier, reliefs and net payable;
- checks six relief types: the retail, hospitality and leisure (RHL) multiplier, Small Business Rate Relief, the pubs and live music discount, Supporting Small Business, transitional relief, and valuation accuracy;
- cross-checks the RV against the VO list;
- gives a red, amber or green verdict per site, with portfolio totals and an April re-check reminder.

**Red-flag check: none.** Business data, public rules and synthetic bills. It recalculates published rules and the owner or accountant decides, so it is not tax advice.

**Other findings**
- More free or cheap substitutes:
  - Rightly Rated sells a £29 relief claim pack and has a free 2026/27 calculator (fetched).
  - BusinessRateChecker shows an estimated 2026/27 bill per property (MCP listing, fetched).
  - Councils' own calculators are free.
- **Pain evidence** is still one council admission (Harborough) plus the complexity of the rules. Councils apply relief automatically and refund credit balances routinely (gov.uk refund guidance and council pages, search summaries). How often bills are wrong is unknown, so the scout's own test is still the right next step: 30 public examples of wrong 2026/27 bills.
- **Refund time limit** (the file's open item): not found. Searches found no statutory limit for England. The Local Government Ombudsman has treated very late refund complaints as out of time (search summary). Treat it as UNVERIFIED.
- **Bundle with the valuation workbench:** 54, so no stronger; see that file.

**Scoring rationale**
- **Pain 9.** No complaint volume, and errors are probably rare.
- **Pay 10.** Paddl shows someone charges for this; there are also audits paid as a share of savings.
- **AI 7.** Extraction across council bill layouts, which Paddl already does.
- **Reach 6.**
- **Build 11.** The rules are public and finite, and the demo can use synthetic bills.
- **Competition 2.** Paddl covers the core for hospitality. Multi-site retail is a thin remaining gap.
- **Risk 9.**

**What would change my mind:**
1. Evidence that bill errors are common: 30 or more public cases or council notices of wrong 2026/27 bills.
2. A segment Paddl doesn't serve, such as multi-site retail or leisure, with a published price someone pays for bill checks.

Otherwise park.

**Sources** (all accessed 2026-11-23)
- https://paddl-ai.co/features/business-rates (fetched)
- https://rightlyrated.uk/ (fetched)
- https://glama.ai/mcp/connectors/com.businessratechecker/mcp (fetched)
- https://www.gov.uk/get-rebate-refund-business-rates (search summary)
- https://www.lgo.org.uk/decisions/benefits-and-tax/other/19-002-878 (search summary)

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted. Pain evidence thin (one council admission); flagged for validator.
- 2026-11-23 | validator | G0→G1 | REVISE 54 | Paddl already reads bills with AI and checks the 2026 reliefs and the RV against the VO list for multi-site hospitality, at £69 per location per month. How often bills are wrong is unproven. Park.
