# Restaurant margin copilot

- slug: restaurant-margin-copilot
- stage: G0
- market and segment: UK independent restaurants, gastropubs and cafés with 1 to 3 sites, where the owner or head chef does the costing on spreadsheets or not at all. Too small for Nory, Apicbase or MarketMan contracts.
- one-line pitch: Photograph or forward each supplier invoice. The copilot reads every line, matches it to your recipes, recalculates each dish's gross profit, and sends you a weekly message along the lines of "beef up 12%, your burger GP fell from 68% to 61%; here are three fixes".

## Problem and who has it

UK restaurant margins are being squeezed. The UK's Top 100 restaurant groups saw combined profits fall 44% even as turnover rose, with food inflation (olive oil, beef, chocolate, coffee, eggs, pasta) named among the drivers. In a joint trade-body survey, 88% of hospitality respondents named food and drink cost inflation as their top non-tax concern. Independents notice price rises late: a recipe-costing spreadsheet holds the price someone typed, not what the supplier charged this week, so every dish using that ingredient is understated until someone updates it by hand. The software that fixes this (inventory and recipe-costing suites) costs about €/$199 to €/$249 a month and takes weeks to set up, and reviews report invoice-scanning bugs. This wedge was chosen over a generic "all-in-one restaurant manager" because invoice-to-dish-margin is the job where AI changes the work (reading messy invoices, fuzzy-matching supplier SKUs to ingredients, converting units). POS, rotas and bookings are already crowded markets where AI adds little.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.restaurantonline.co.uk/Article/2026/08/24/the-uks-top-100-restaurant-groups-see-profits-fall-by-nearly-half/ | 2026-11-23 | UHY Hacker Young analysis. Combined profits of the Top 100 UK restaurant groups fell 44% (£365m to £204m) while turnover rose (£12.9bn to £13.3bn). Food inflation (olive oil, beef, chocolate, coffee, eggs, pasta) is among the cost drivers. |
| https://www.restaurantonline.co.uk/Article/2026/10/23/strong-hospitality-summer-trading-fails-to-improve-profitability-trade-bodies-warn/ | 2026-11-23 | Joint UKHospitality, BBPA, BII and Hospitality Ulster member survey (sample size not stated). Food and drink cost inflation is the top non-tax concern (88%). Inflation "remains stubbornly high". Strong sales are not the same as healthy profits. |
| https://www.capterra.com/reviews/136439/Marketman-Restaurant-Inventory | 2026-11-23 | Reviews of the leading incumbent, as summarised in search results (page not fetched). Setup is "very tedious and takes a LOT of work" and took "weeks". A G2 user said invoice scanning "did not work 50% of the time" (https://www.g2.com/products/marketman/reviews). The incumbent is costly and slow to adopt. |
| https://supy.io/en-au/blog/learn-spreadsheet-recipe-costing-vs-software | 2026-11-23 | Vendor article (Supy), seen in search results: a spreadsheet stores the ingredient cost you typed, not today's supplier price, so recipes are understated until updated by hand. This is the core manual task. Vendor source, so treat it as a description of the workflow rather than proof of pain. |
| https://businesscloud.co.uk/news/nory-raises-27m-as-it-doubles-down-on-building-ai-assistants/ | 2026-11-23 | Nory (London and Dublin, AI restaurant back office) raised a $37m (£27.1m) Series B in Sept 2025 and serves multi-site groups. It claims 100+ admin hours saved per site per month (company claim). This shows investor-validated demand at the top of the market, while independents are under-served. Details from search results. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Apicbase (https://www.capterra.co.uk/software/171584/apicbase-restaurant-management, accessed 2026-11-23 via search snippet) | from €249/month (per feature) | Built for groups. Heavy setup. |
| MarketMan (https://www.capterra.com/p/136439/Marketman-Restaurant-Inventory, accessed 2026-11-23 via search snippet) | about $199 to $249/month (aggregators disagree) | US-centred. Setup takes weeks. Scanning bugs reported. |
| Kitchen Porter Tech recipe costing (https://www.capterra.co.uk/software/112109/kitchen-porter-tech, accessed 2026-11-23 via search snippet) | US$25 per location per month | Cheap, but manual price entry. No invoice-reading AI found in the listing. |
| Recipe Cost Calculator (https://www.capterra.co.uk/software/207446/recipe-cost-calculator, accessed 2026-11-23 via search snippet) | €15/month flat | Manual entry. |
| Nory (search results above) | No public price; sells to multi-site operators | Not aimed at 1 to 3 site independents. |
| Owner's or chef's own time on a spreadsheet | Not quantified. No independent time study found. | Prices go stale. Margin erosion goes unseen for weeks. |

## Why AI is essential (and the moat)

- Reading invoices: varied supplier layouts, phone photos, credit notes, pack sizes ("12x1L", "5kg case") turned into a cost per gram or ml. Vision-language models make this workable without per-supplier templates.
- Matching: mapping "BEEF MINCE 20% 5KG" from one wholesaler and "Minced beef 80VL" from another to one recipe ingredient, with confidence scores and a quick confirm step.
- Recipe capture from a menu PDF or a chef's voice note or rough text, turned into a structured recipe with portion weights. A human confirms it.
- Plain-English weekly brief with suggested fixes (re-price, swap supplier, adjust portion), sent by email or WhatsApp.
- Moat (moderate): a growing UK supplier-SKU mapping dataset (Brakes, Bidfood, Booker, local butchers and greengrocers), an evaluation set of real-format invoices, and very low setup effort as the wedge against the incumbents' weeks-long onboarding.

## Rough build plan and Azure cost

- Week 1: invoice upload (photo or PDF, plus email-in through an adapter), line extraction to structured JSON, an evaluation set of about 50 synthetic and anonymised-format invoices.
- Week 2: ingredient catalogue, SKU-to-ingredient fuzzy matching with confirm UI, unit and pack conversion.
- Week 3: recipe builder (import from menu text), dish GP calculation, price-change detection and weekly brief.
- Week 4: polish, GDPR (minimal personal data, mostly business data), demo café with fictional invoices.
- Azure (estimate): Container Apps scale-to-zero (about $0 to $5/mo). Azure OpenAI vision-capable small model for extraction (about $3 to $10/mo at demo volume of a few hundred invoice pages); Azure AI Document Intelligence free tier as a fallback. Postgres or SQLite on storage (about $0 to $15/mo). Projected total about $5 to $30/mo.

## Risks, and what would prove this wrong

- Independents are price-sensitive and churn often. They may not pay even £30 to £50/month. No direct survey of independents' willingness to pay was found.
- Setup still needs recipes. If owners won't enter or confirm recipes, the GP figures never appear. The product has to work from invoices alone first (price-change alerts) and add recipes over time.
- Extraction accuracy on crumpled photos must be high. Wrong prices destroy trust.
- Several pain signals come from chains or vendors, not independents.
- Low regulatory risk: business documents, little personal data.
- Proved wrong if: 10 independent owners say their supplier already emails price-change lists and they re-price twice a year anyway; or extraction accuracy on real-format invoices stays below about 95% line accuracy after two weeks; or a cheap incumbent (for example Kitchen Porter Tech) turns out to already offer AI invoice reading.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 13 | 14 | 9 | 7 | 11 | 3 | 9 | 66 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area. Email-in and WhatsApp sit behind adapters.
- The free tools look sufficient. Document Intelligence's free tier gives 500 pages a month, though only the first 2 pages of each request are read (https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits, search summary only). The Azure AI Foundry catalog lists gpt-5-mini as taking image input (https://ai.azure.com/catalog/models/gpt-5-mini, search summary only).
- Synthetic data can credibly demo the value: fictional invoices in realistic UK wholesaler layouts plus a fictional café menu are enough to show a price rise flowing through to dish GP. Accuracy on real crumpled photos stays unproven until a pilot.

**Falsification findings** (all accessed 2026-11-23)
- Strongest competitor: Jelly, which faces the UK market and is priced for independents.
  - Capterra UK lists a flat price from £129 (search summary only; the page returns 403).
  - Epos Now's UK app store describes it this way: "Upload invoices or link Jelly directly to suppliers and enjoy real-time updates on pricing and costs". It also lists recipe costing and claims an average of 36 hours saved a month; that figure is the vendor's own (https://www.eposnow.com/uk/store/software/apps/jelly/).
  - It also integrates with Lightspeed, Square and Xero (https://www.lightspeedhq.com/uk/integrations/jelly/, search summary only).
  - This largely falsifies the scout's gap of "€/$199 to €/$249 and weeks of setup".
- Other AI invoice-to-margin tools show up in listings: Profito, KitchenIQ and PrepSheet Plus (GetApp and Slashdot, search summary only, unverified), plus Syrve (AI invoice scanning since October 2025) and Supy. meez's Scale plan, which includes invoice processing, is $179/mo billed annually (https://getmeez.com/pricing, search summary only). MarketMan is $239 per location per month on G2 (search summary only).
- A free substitute from suppliers: Bidfood's MyRecipes and Menu Planning tools are "free for Bidfood customers" and "reflect your actual real time food costs" (https://www.bidfood.co.uk/?p=1310586, blog dated 4 May 2023). Brakes' Virtual Chef lets customers add their own products (https://www.brake.co.uk/why-brakes/natashas-law/virtual-chef). An independent that buys mostly from one wholesaler already gets much of this job free. The gap left is independents who buy from several suppliers.
- The pain evidence is broad, not about independents. UHY's 44% profit fall covers only the Top 100 groups and doesn't mention independents. The 88% trade-body figure comes from member surveys with no sample size and no split for independents; energy came second at 80%. Both checked on the source pages.
- Copy risk: Jelly or Kitchen CUT could launch a cheaper "invoices only" tier within a month. The remaining wedge is a price well under £129, plus price-change alerts that need no setup and work before any recipes are entered.

**What would change my mind (re-score on this evidence)**
1. Jelly, Profito and KitchenIQ pricing and features checked on their own vendor pages, showing a real gap: minimum terms, onboarding fees, human-review delays, per-invoice limits or poor accuracy reviews.
2. Evidence that independents with 1 to 3 sites won't pay £129 but would pay about £30 to £50. That could be public complaints from owners about price, or a cheap competitor with visible traction.
3. Evidence on how many UK independents buy from several suppliers (butcher, greengrocer and wholesaler), which would show the free single-supplier tools don't cover them.
4. A desk benchmark on about 50 synthetic invoices in realistic UK layouts, including phone-photo distortion, reaching at least 95% line accuracy (the scout's own bar) at a cost per page that fits the Azure budget.

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 66 | AI is essential and operators clearly pay, but Jelly already sells AI invoice capture, recipe costing and margin alerts to UK independents from about £129 and Bidfood gives its customers free real-time recipe costing, so the gap the scout claimed is largely filled.
