# Quote price guidance for small B2B distributors and job shops

- slug: sme-quote-price-guidance
- stage: G0
- market and segment: UK trade distributors, merchants and make-to-order manufacturers with 10 to 250 staff that quote customers by hand or from ERP price lists (Sage, Xero-based, Epicor, Acumatica, simple ERPs).
- one-line pitch: Reads the firm's own quote and invoice history, learns win probability and margin by customer, product and quote size (a bandit or RL style price policy), and suggests a price band and discount limit on each new quote, with the reason shown.

## Problem and who has it

Small sellers set B2B prices by habit: cost-plus, the last price, or the salesperson's feel. Discounts leak margin and nobody sees win rate against price. Enterprise price-optimisation exists, but the entry cost excludes firms with a few hundred customers. Job: recommend a quote price per line, and show leakage (off-band quotes, stale prices after cost rises).

## Cheap kill test (done first, 2026-11-24)

Searched for a self-serve SMB tool for sell-side quote price optimisation. Found no independent affordable tool that models quote win probability for small distributors or job shops (search 2026-11-24). Found: enterprise suites, one mid-market tool at €1,490 a month, mid-market analytics vendors without public prices, quoting tools without optimisation, and a buy-side tool (not the same job). This is a weaker pass than the origin idea: the evidence is search summaries only, vendor pages for Revology, Phocas and Cavallo were not fetched, and ERP-native pricing modules were not checked.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.pricefx.com/learning-center/how-much-does-pricing-software-cost (search summary; vendor-stated) | 2026-11-24 | Pricefx subscriptions $100,000 to $3.5 million a year; implementation $100,000 to $1.5 million. Enterprise. |
| https://www.g2.com/compare/priceedge-vs-pricefx and G2 PriceEdge listing (search summary) | 2026-11-24 | PriceEdge entry plan EUR 1,490 a month; mostly mid-market reviewers. A price point above SME budgets. |
| Vendavo, Zilliant, PROS (G2 pages, search summaries) | 2026-11-24 | No published prices; G2 lists Zilliant as top-tier cost with about 7 months to implement; one review says Vendavo CPQ may be overly complex for small businesses. |
| https://www.manufacturingtomorrow.com/content.php?post=14596 (fetched; vendor-authored) | 2026-11-24 | Author's claim: price optimisation for large manufacturers costs $120K to $1.5M a year; most small manufacturers (89% under 50 staff, his figure) cannot justify it. His own product (WorkCenter, under $5,000 a year) is buy-side part pricing, not sell-side quotes. |
| https://revologyanalytics.com/industrials-overview/wholesale-and-distribution/ (search summary) | 2026-11-24 | Mid-market analytics vendor flags off-band transactions by customer and product; claims 4 to 6% of gross margin recovery for mid-market distributors (vendor claim). |
| https://www.vistaar.com/blog/pricin-software-for-wholesale-distributors (search summary) | 2026-11-24 | Vendor guide names uncontrolled discounting as a leading margin leak. Pain narrative, vendor-authored. |
| https://conga.com/customer-stories/distributor-improves-pricing-and-sales (search summary) | 2026-11-24 | Large electronics distributor claims $41M leakage tackled. Shows pain at enterprise scale only. |

Pain evidence is vendor-authored throughout. The validator should look for an independent source (trade-body survey, ONS margin data, merchant group commentary).

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Spreadsheets and Power BI on an ERP export | Power BI Pro $14 per user a month (search summary, https://www.us-food-distributors.com/blog/best-distributor-analytics-software); plus analyst hours | Shows history; gives no win-probability or recommended price |
| Pricefx, Zilliant, PROS, Vendavo | $100,000+ a year (Pricefx, vendor-stated); others on request | Enterprise scale and implementation |
| PriceEdge | EUR 1,490 a month entry (G2) | Mid-market; not SME |
| Revology, Cavallo Profit Max, Phocas (not fetched) | Not published | Analytics and exception scoring; consultative; SME self-serve not confirmed |
| Quoting and CPQ tools (Paperless Parts, PandaDoc, Katana per reviewers) | Not checked | Produce quotes, do not recommend price from win history |
| ERP built-in price lists and rules (Epicor, Acumatica, Sage) | Not checked | Hold prices; unverified whether they recommend them |

## Why AI is essential (and the moat)

The recommendation comes from a model of win probability against price by segment, trained on a small firm's sparse, noisy history (hundreds to low thousands of quotes). That needs shrinkage across segments, a cautious exploration rule so the firm does not lose key accounts, and an explanation per quote. This fits Vishal's RL and dynamic-pricing edge. Weakness: with small data, a gradient-boosted win model plus a margin rule may do as well as RL, so "RL" must be benchmarked, not assumed. LLM role: map messy quote and invoice exports, explain the recommendation in plain words, flag stale prices after supplier cost files change.

## Rough build plan and Azure cost

- Inputs: quote and invoice history CSV (customer, product, qty, price, cost, won or lost) from the firm's ERP.
- Pipeline: column mapping with an LLM, cleaning, segment model for win probability, price band and discount-limit policy under a margin floor, per-quote advice in a web form, leakage report.
- Data: only the customer's own data; no scraping, no personal data beyond business customer names.
- Demo with synthetic data: generate a synthetic distributor with a known price-elasticity structure and show recovered margin against a held-out period. This is the main proof test (write the number first: recommended-price policy beats the firm's actual policy by at least X points of margin in simulation and on a public proxy dataset if one exists). Fully demoable without paid services.
- Azure estimate: not costed; small batch training plus a web app. Likely under £40 a month at demo load.

## Risks, and what would prove this wrong

- Competition: unverified ERP-native and mid-market tools; Revology, Phocas, Cavallo pages not fetched. Proof of wrong: any tool with a public price under £300 a month that recommends quote prices from win-loss history.
- Pay: no public price an SME pays for this job today; salary-style modelling is not accepted as Pay evidence.
- Data: needs 12+ months of won and lost quotes; many small firms do not record lost quotes. This could fail the Build and Reach scores outright.
- Price recommendations can lose customers; positioning must be advice with a margin floor, and human sign-off.
- Cross-check: B2B pricing sits next to killed restaurant-margin and CPI ideas, which lost on Pay and on the arithmetic core.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Gate log
- 2026-11-24 T-49 scout round 12: written at G0. Scores left for the validator. Evidence base is thinner than the origin idea; treat the Competition pass as unconfirmed.
