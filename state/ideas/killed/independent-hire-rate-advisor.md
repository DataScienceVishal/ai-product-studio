# Independent hire rate advisor (tool and plant hire)

- slug: independent-hire-rate-advisor
- stage: G0
- market and segment: UK independent tool, plant and equipment hire shops (1 to 10 depots) running a hire management system (HireHop, Klipboard, Point of Rental, inspHire and similar)
- one-line pitch: Reads the shop's own hire history and utilisation export, then recommends rate-card changes and per-customer discount limits each week, with the working shown, for the owner to approve.

WEAK G0. Written because it was the only niche in round 14 where no SMB-priced AI pricing tool was found. It fails three of the five survivor tests (see Risks). Treat as a candidate for a quick validator kill, not a recommendation.

## Problem and who has it
Rates for each item are set from a list price, then reps vary them by volume, length and season. Trade press describes plant, tool and skip hire as "historically manual" and early in AI pricing. Zilliant says smaller rental firms have discount mechanisms inside invoicing that neither reps nor customers can see, and that discounts come from long spreadsheets. The shop's own data is in its hire system (bookings, rates charged, off-hire dates, asset list, so utilisation by item and week can be computed).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://internationalrentalnews.com/news/setting-the-right-rates-pros-and-cons-of-dynamic-pricing/8050009.article (fetched) | 2026-11-24 | A vendor (easyHire, not verified as a company) calls skip, tool and plant hire "historically manual". HSS keeps a list price per item and lets branches vary it within guidelines. No uplift figure given. Wynne RentalMan uses Rouse data feeds (enterprise) |
| https://www.khl.com/news/how-dynamic-pricing-is-being-used-in-equipment-rental/8025507.article (fetched) | 2026-11-24 | Kiloutou runs Pricemoov (min/max range per machine plus occupancy, recommended prices to branches). No UK small firm named; no uplift percentage |
| https://www.khl.com/news/broadening-reach/104845.article (search summary, not fetched) | 2026-11-24 | Zilliant MarginMax Ramp aimed at smaller rental firms; hidden invoice discounts; dated to about 2014; no current price |
| https://www.hae.org.uk/about/faqs/ (search summary) | 2026-11-24 | HAE EHA has over 700 member companies (UK and Europe, all sizes) and an Independent Hirers Committee. Not a count of UK independents |
| https://www.capterra.co.uk/software/155333/hirehop (search summary) | 2026-11-24 | HireHop £23-£33 per user per month; no AI pricing feature seen in results |

Independent pain evidence is thin: the "manual" claim comes from a vendor quote in trade press. No survey of hire shops was found.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Hire management systems (HireHop £23-£33 per user a month; HireYard about $89; Booqable from $29; Current RMS $62-$71 per user) via Capterra UK | £23 to about £70 per user per month | Rate tables only; no recommendation seen in results (feature pages not read) |
| Point of Rental AI Insights / MCS AI Insights | not published (https://www.point-of-rental.com/gb/rental-intelligence/rental-intelligence-suite/, search summary) | Nightly review for hire decisions; pricing recommendation not confirmed. MCS says pricing AI is on its roadmap. The system vendors can ship this |
| Pricemoov, Zilliant, Vendavo, Wynne+Rouse | enterprise, unpriced | Not SMB |
| Spreadsheet and owner's judgement | staff time | Status quo |

## Why AI is essential (and the moat)
Weak. A demand curve per item class and weekly recommendations is ML (elasticity and utilisation forecasting, bandit-style price tests), which fits Vishal's RL edge. The moat is cross-system export work and trust, not data. Incumbent system vendors hold the data and can ship the feature.

## Rough build plan and Azure cost
CSV or API import from HireHop (public API) and one more system; item-class utilisation model; weekly recommendation sheet with working shown; approve and export rate changes. Small Azure footprint (one container app, Postgres, nightly job), estimate under £30 a month. Not costed in detail.

## Risks, and what would prove this wrong
- Data red flag: uplift can only be shown on real hire histories. Synthetic test possible (simulate item classes with a known price-demand curve, compare a static rate card, a rule-based discount policy and the learned policy over 52 simulated weeks), but it proves the method, not uplift. A real shop's export is needed and the studio has none.
- Pay: no price an independent hire shop pays for pricing help; no revenue-share consultant found.
- Reach: no count of UK independents (HAE 700+ members is all sizes and countries). Check HAE Independent Hirers Committee, CPA and Companies House SIC 77320 and 77390 for a count.
- Competition: Point of Rental and MCS already market AI Insights; HireHop, Klipboard and inspHire could add rate suggestions. Not read on their own feature pages. Capterra lists could hide a small AI pricing tool.
- Inelastic demand: plant hire is often won on availability and relationship; rate rises may not stick.
- Kill quickly if: any hire system's own feature page shows "rate suggestions" or "utilisation-based pricing", or no shop will share a 12-month export.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 6 | 4 | 7 | 5 | 8 | 4 | 9 | **43** |

Validator checks (T-51, 2026-11-24, all accessed that day; search summaries unless marked fetched):
- **Pain 6/20.** All three signals come from vendors (easyHire in IRN, Zilliant via KHL in about 2014, Pricemoov case study at Kiloutou, an enterprise firm). There are no hire-shop complaints, no job ads for a pricing analyst at an independent, and no survey. inspHire's own blog (https://blog.insphire.com/dynamic-pricing-in-equipment-rentals, fetched) says hire firms "prefer to set their own prices" and that "it's up to our customers to define these prices". That is a vendor reading its buyers as not wanting recommendations.
- **Pay 4/20.** There is no SMB price for rate advice, no consultant price and no revenue-share offer. The only priced items are hire systems at £23-£70 per user a month, which bundle rate tables. Rouse Rental Insights (Ritchie Bros/RB Global) gives UK contributors a benchmark of their rates and utilisation against the local market from actual invoices. About 80 UK firms contributed by 2023 (https://www.internationalrentalnews.com/news/rouse-brings-rental-benchmarking-to-europe/8031644.article; https://rbglobal.com/insights/rouse-rental-insights/). Historically the summary tier was free, with paid detail; there is no current UK price. Rouse sets the price anchor near zero for the comparison half.
- **AI 7/15.** Elasticity per item class from one shop's history is a real ML problem. But the data is sparse: a 1 to 10 depot shop has few units per class, and rates are negotiated per customer, so the price signal is confounded with the customer. Utilisation-threshold rules (raise the rate when utilisation is above X%) are the cheap substitute, and MCS already ships rule-based peak pricing.
- **Reach 5/10.** HAE/EHA has 700+ members across all sizes and countries (https://www.hae.org.uk/about/faqs/), with an Independent Hirers Committee. There is no public count of UK independents: Barbour ABI's operator count by turnover band is paywalled (https://store.barbour-abi.com/report/plant-hire-market-report-uk). The market is fragmented (IBISWorld £8.8bn for 2026, https://www.ibisworld.com/united-kingdom/industry/construction-equipment-rental-leasing/4120/), so buyers exist, but they are split across at least six hire systems.
- **Build 8/15.** The model and app fit the stack and budget. Import is the problem. No public HireHop API documentation was found in two searches (the file's "public API" claim is unverified), and inspHire, MCS and Point of Rental APIs are customer or partner access. Each system needs its own CSV mapping.
- **Competition 4/10.**
  - Point of Rental's Rental Intelligence Suite (UK site, launched at the ARA Show on 2 March) includes AI Insights. It runs nightly on underused equipment and seasonal patterns and gives recommendations with the reasoning shown. Vendor examples include "Where am I under-pricing relative to demand?" and "Which customer segments are paying below market?" (https://www.point-of-rental.com/gb/rental-intelligence-suite-is-here/, fetched; https://www.point-of-rental.com/fr/webinar-recap-ai-rental-intelligence-suite/). That is this idea's pitch, inside the system of record. It is Elite-tier, not SMB.
  - MCS added flexible and dynamic peak pricing in July 2024 (https://mcsrentalsoftware.com/us/company/news-and-events/mcs-rental-software-announces-flexible-pricing-feature) and says pricing AI is on its roadmap.
  - inspHire has ROI dashboards and demand forecasting.
  - Rouse benchmarks rates for about 80 UK firms.
  - The only open gap is SMB systems (HireHop, Booqable), whose vendors can copy a utilisation-based rate hint quickly.
- **Risk 9/10.** Business data only. There is a minor competition-law caution if the product is ever pooled across shops (shared pricing recommendations between competitors).

**Red flag: core value can't be shown without real customer data.** The claim is rate uplift on a shop's own hire history. A synthetic simulation with a known demand curve proves only that the method recovers the curve the studio planted. The studio has no hire export and can't ask a shop for one while selling is locked. This is the same failure as homestay-rate-copilot-india, bali-villa-rate-copilot and sme-quote-price-guidance.

**Verdict: KILL (43, data red flag).**

Reason: the product's value is a measured revenue uplift from rate changes, and that can only be demonstrated on real hire histories that the studio cannot get. Even setting the data aside, the evidence is weak on every commercial axis. Pain comes only from pricing vendors, and inspHire publicly reads its buyers as wanting control rather than recommendations. Nobody publishes a price that an independent pays for rate advice. Point of Rental already markets AI under-pricing questions with the working shown, and Rouse gives UK contributors invoice-based rate benchmarks. The small-shop gap that is left (HireHop and Booqable users) is the one where the data is sparsest and the host vendor can add a utilisation-based rate hint cheaply. Ceiling about 55 even with a data partner.

Lessons:
- "Learns from your own transaction history to set prices" has now failed the data red flag four times: homestay, Bali villas, SME quotes and hire rates. Stop scouting pricing-uplift ideas until a data partner is in hand (that needs `unlock selling`, or Vishal providing a dataset).
- Check for the sector's benchmark service (Rouse in equipment rental) before claiming SMB firms have no pricing data. Benchmarks often give contributors the summary free.
- Verify a "public API" claim on the vendor's developer pages before scoring Build.

What would revive it:
- a UK independent hire firm lawfully sharing 12+ months of hire history, with a backtest showing that recommended rates would have lifted revenue per asset without losing utilisation; and
- a published price (or a firm's written willingness to pay) for rate advice at SMB level; and
- evidence that HireHop and Klipboard have no rate-suggestion feature on their roadmaps.

## Gate log
- 2026-11-24 round 14 scout (T-51): G0 written. Not validated.
- 2026-11-24 validator (T-51): scored 43/100. **KILL** on the data red flag (uplift needs real hire histories), with Point of Rental AI Insights and Rouse UK benchmarks covering the pitch. Ceiling about 55.
