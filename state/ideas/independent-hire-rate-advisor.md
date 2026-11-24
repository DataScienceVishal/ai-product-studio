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
| | | | | | | | |

## Gate log
- 2026-11-24 round 14 scout (T-51): G0 written. Not validated.
