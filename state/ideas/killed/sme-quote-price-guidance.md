# Quote price guidance for small B2B distributors and job shops

- slug: sme-quote-price-guidance
- stage: killed (T-49 validator, 2026-11-24, score 50, data red flag; the Studio Lead should git mv this file to killed/)
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
| 8 | 7 | 9 | 6 | 7 | 4 | 9 | 50 |

## Validator, round 12 (T-49, 2026-11-24)

**Verdict: KILL (50/100, first attempt, red flag: the core value can't be shown without real customer data the studio can't get). Ceiling about 60.**

| Line | Score | Why |
|---|---|---|
| Pain /20 | 8 | Margin leakage from discounting is a real theme, but every source is vendor-authored (Vistaar, Revology, Conga, ManufacturingTomorrow). The only semi-independent data is a Phocas survey (2026, 100+ distributors). It shows 34% don't measure new-business win rates, which is a measurement gap, not a cost or a complaint. There is no UK merchant source and no job ads for a pricing analyst at SME scale. |
| Pay /20 | 7 | The only prices found are mid-market and enterprise: PriceEdge €1,490 a month (G2), BlackCurve from €599 a month (aggregator, unverified, retail-focused) and Pricefx at $100k+ a year (vendor-stated). Cavallo, Phocas and Revology are all quote or demo only. No SME price for the job was found, and no modelled salary was accepted. |
| AI /15 | 9 | Win-probability modelling on sparse data is real ML and fits Vishal's edge. But the scout admits that a gradient-boosted model plus a margin floor may match RL, and margin-floor alerts capture most of the leakage value without any model. |
| Reach /10 | 6 | Trade bodies (Builders Merchants Federation, Electrical Distributors' Association, NMBS) are findable. But the buyer is the owner or sales director, the sale needs ERP data access, and a two-person business would struggle with onboarding. |
| Build /15 | 7 | The web app and model are easy. The proof is not. Synthetic data with a known elasticity structure only recovers the structure the studio put in (circular), and there is no public B2B quote-outcome dataset. Lost quotes are often not recorded: 34% and 32% of distributors don't measure win rates (Phocas), and verbal quotes aren't captured in the system (MDM). Without loss data there is no win-probability model, only a margin-history report. |
| Competition /10 | 4 | ERP-native pricing exists: Sage 200 Price Book (price bands, limited prices, discount groups, price checks with exception reports). Phocas sells margin floors with automated alerts and live margin for reps before a negotiation. Cavallo Profit Scan is free on Business Central and flags low-margin orders, and Profit Max adds AI. PriceEdge, Revology and Pricefx sit above. No one sells self-serve quote win-probability to SMEs, but the leakage half is served or free. |
| Risk /10 | 9 | Business data only, with human sign-off. A small risk of lost accounts if the advice is followed blindly. |

**Why killed.** The idea's value is "our recommended price beats your own policy". That can only be shown on a firm's real won-and-lost quote history. The studio can't get one before selling is unlocked, and the evidence suggests many small distributors don't record lost quotes at all, so the input often doesn't exist. Without win-loss data the product falls back to margin-leakage reporting. That half is already covered by ERP price books (Sage 200), Phocas margin-floor alerts and Cavallo's free Profit Scan, so the down-market gap is narrow and unpriced. The Pain evidence is vendor-authored and there is no SME price, so Pay and Pain are both weak even before the data problem.

**Lessons.** For any "learns from your history" product, confirm first that SMEs actually hold the label the model needs (here, lost quotes), using an independent survey. A synthetic dataset can show the pipeline works but cannot prove uplift. Check the free ERP-marketplace tier (Cavallo Profit Scan on AppSource) before calling a job enterprise-only.

**What would revive it.** A licensed or public B2B quote dataset with won and lost outcomes. Or a quoting system that records losses by design, such as a job-shop CPQ like Paperless Parts or a merchant trade-counter system that exposes quote status, as the channel. Plus an independent UK source on discount leakage in merchants or wholesalers. Then re-score as an add-on to that system.

Evidence, all accessed 2026-11-24:
- https://www.phocassoftware.com/industries/wholesale-distribution/pricing-strategy (fetched: margin floors with automated alerts, live margin for reps; demo only; no price recommendations or win rate).
- https://www.marketscale.com/industries/software-and-technology/phocas-finds-39-of-distributors-dont-measure-sales-forecast-accuracy (search summary: 34% don't measure new-business win rates, 32% don't measure existing-account win rates).
- https://www.mdm.com/?p=9635 (search summary: lost follow-up, verbal quotes not captured, systems can't track project quotes).
- https://desktophelp.sage.co.uk/sage200/professional/Content/PB/Manage_Pricing.htm and https://desktophelp.sage.co.uk/sage200/professional/Content/PB/Prepare_pricing_reports.htm (search summaries: Sage 200 price bands, limited prices, discounts, price checks and exception reports; no win-rate or recommendation feature).
- https://www.cavallo.com/profit-scan/ and https://appsource.microsoft.com/en-us/product/dynamics-365-business-central/PUBID.salespadllcdbacavallosolutions1644863490847%7CAID.cavallo_profit_scan%7CPAPPID.3ef0e9b2-aa85-4f7d-a902-e99d78c2d049 (search summaries: free Profit Scan flags low-margin orders; Business Central only).
- https://www.g2.com/products/cavallo/pricing (search summary: Profit Max custom quote by seats, volume and modules).
- https://www.softwareadvice.com/pricing-optimization/black-curve-profile/ (search summary: BlackCurve from €599 a month, retail integrations; unverified).
- https://www.g2.com/compare/priceedge-vs-pricefx (scout: PriceEdge €1,490 a month).
- Unleashed and Cin7: Capterra lists Unleashed at $399 a month and Cin7 Core from $349 a month (https://www.capterra.com/compare/126644-133038/Unleashed-vs-Cin7-Core, search summary). No quote price-recommendation feature was found for either, so this is unconfirmed rather than ruled out.
- Revology: consultancy-led, no SME price (https://revologyanalytics.com/industrials-overview/wholesale-and-distribution/, search summary via a mirror).

## Gate log
- 2026-11-24 T-49 scout round 12: written at G0. Scores left for the validator. Evidence base is thinner than the origin idea; treat the Competition pass as unconfirmed.
- 2026-11-24 T-49 validator: KILL, 50/100 (Pain 8, Pay 7, AI 9, Reach 6, Build 7, Competition 4, Risk 9), with the data red flag: uplift can't be shown without real won and lost quote histories, which many SMEs don't record. The leakage half is served by Sage 200 Price Book, Phocas margin floors and the free Cavallo Profit Scan. Ceiling about 60.
