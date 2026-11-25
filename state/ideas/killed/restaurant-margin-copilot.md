# Restaurant margin copilot

- slug: restaurant-margin-copilot
- stage: KILLED (2026-11-25, T-80 proof test KILL; second failed G1 attempt)
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
- 2026-11-25 | validator | G0→G1 (second attempt, T-80 proof test) | KILL 66 | The pre-registered synthetic-invoice benchmark hit three KILL lines in `KILL-TEST.md`: overall line accuracy 82.6% (KILL below 88%), distorted photos 72.1% (KILL below 80%) and 5 silent-error invoices (KILL at 3 or more). Second failed gate, so the idea is killed. See "Kill (2026-11-25)" below.

### Re-score 2026-11-24 (T-57, Q-10 wedge rule)
Validator. Only the Competition row is re-scored, under the wedge rule in `playbooks/pipeline.md`. This is not a G1 attempt; the last attempt is still unspent.
- **Competition: 3 → 3.** No wedge is both named and evidenced.
  - *"Less product for much less money, no setup fee"* (SPEC.md: £39 to £69 against Jelly's £129 plus setup). To count as "cheaper for a segment it prices out", we need evidence that Jelly prices out 1 to 3 site independents. There is none. T-9 found no owner complaints about Jelly's price, and Jelly's own page says it serves "independent restaurants, pubs, cafés". The cheap end is also served already: Profito from €34 and KitchenIQ $89 (both unverified listings), and Kitchen Porter Tech at $25.
  - *Accountant-led channel.* Jelly's pricing page shows no partner programme (round-11 summary, fetched 2026-11-24), but no source shows that accountants resell margin tools or that independents buy through them. This is a hypothesis, not evidence.
  - *Weekly written "three fixes" message.* SPEC-CHECK.md shows that Jelly's homepage already sends daily price notifications and "margin warnings". The difference is a presentation layer Jelly could copy in weeks. It is not a measured quality gap.
  - *Multi-supplier independents* (outside Bidfood's and Brakes' free tools): unsized, and Jelly already handles several suppliers.
- **Knock-on:** none. Pain 13, Pay 14, AI 9, Reach 7, Build 11 and Risk 9 are unchanged.
- **New total: 66 (unchanged). Verdict: REVISE (parked).** No red flag. Still 4 short of 70, and Competition is held at the top of the no-wedge band.
- **The one piece of evidence that would move it:** a measured quality gap. That means the committed synthetic-invoice benchmark (about 50 UK-layout invoices with phone-photo distortion, ≥95% line accuracy within budget), run against a documented Jelly or Profito failure mode, such as review evidence of mis-reads or invoice caps. Alternatively, Vishal's partner turns out to be a hospitality accountant with clients priced out at £129. Either one could take Competition to 5 or 6, which is still only 68 to 69 without a Reach or Pay gain.

## Evidence pass T-9 (2026-11-23)

Desk research by the scout, 2026-11-23. All pages were fetched on that date. Page text is quoted as the fetch tool returned it. "Unverified" means only a third-party listing or search summary was seen, not the vendor's own page. Several vendor pages (Profito, KitchenIQ, Supy, Nory) could not be fetched (403, 503 or redirect to a domain seller), so those rows are unverified.

### 1. Competitors on their own pages (1 to 3 site independent)

| Tool | Own-page evidence | Price | Reads invoices with AI | Maps to recipes and recalculates GP | Sends fix suggestions |
|---|---|---|---|---|---|
| Jelly (London, founded 2018) | https://www.getjelly.co.uk/pricing: "£129 per location per month. That's it." "All your invoices processed (fair usage applies)." "Recipe & menu costing" included. Monthly plan: "cancel anytime". Annual: 10% discount, cannot cancel until year end. One-time setup fee per site (amount not stated) with 1-1 onboarding; "up and running the same day". POS integration pass-on fee "starting from £15 per month per location". Lightspeed's Jelly page (https://www.lightspeedhq.com/uk/integrations/jelly/): "Jelly automates invoice processing", Lightspeed sales plus invoice scanning gives an automated GP report, "price alerts" and "real-time margin insights"; works with "independent restaurants, pubs, cafés, and multi-site groups". | £129 per site per month, plus setup fee and possible £15 POS fee | Invoice scanning: yes. The word "AI" is not on the pricing page. A vendor article seen in search (unverified) says "AI Invoice Scanning". | Yes: recipe costing and GP report | Price alerts and margin insights: yes. No page text found about written fix suggestions (re-price, swap supplier). |
| MarketMan | https://marketman.com/pricing: Starter $249/month "for independent operators" with "Real-time recipe costing" and "50 AI-powered invoice scans per month". Growth $299 with "AI recipe optimization" and unlimited scanning. Enterprise from $449. No setup fee listed. UK page https://www.marketman.com/uk-restaurant-stock-control-software: "Snap a photo and AI scanning does the rest"; "AI flags price changes the moment they hit your invoices"; "calculate your gross profit in real time"; "Whether you run one kitchen or many". | $249 to $299 per month (USD, per page; not stated per location) | Yes, capped at 50 scans on Starter | Yes | Price-change flags yes; "AI recipe optimization" only on Growth |
| Access Procure Wizard Evo | https://www.theaccessgroup.com/en-gb/hospitality/software/purchase-to-pay/restaurant-invoice-management/: invoice data "flows directly into recipe costing, menu profitability and cost of sales"; price changes "flow through automatically to your recipe costs, menu GP"; price alerts on "unexpected supplier price increases". Mentions a Copilot to query purchasing data in plain language. No price. Aimed at "hospitality operators" and "a busy multi-site operation". | Not published | Page did not describe AI scanning (it describes 2-way invoice matching) | Yes | Alerts yes |
| KitchenIQ | Vendor page not reachable (503). Unverified, from Capterra and GetApp search summaries: Pro $89/month, or $799/year; Tracker plan $25/month; features "invoice scanning, automatic price tracking, real food cost calculation, price alerts, suggested pricing, and profitability insights". G2 shows one review and no price (https://www.g2.com/products/kitcheniq/pricing). | $89/month (unverified) | Yes (unverified) | Yes (unverified) | "Suggested pricing" and alerts (unverified) |
| Profito | Vendor page not reachable (redirects to a domain seller). Unverified, from GetApp and Software Advice summaries (https://www.getapp.co.uk/software/2105229/profito): Starter €34/month flat, unlimited recipes with cost and margin tracking, but only 5 invoices scanned per month; photo or email-inbox import; multi-location; French-hosted. Higher tiers not found. | from €34/month (unverified); invoice cap 5 on Starter | Yes (unverified) | Yes (unverified) | Not found |
| Marge Up, RestauMargin, Tavola, Supy | Seen only as Capterra or GetApp listings or vendor blogs in search results (https://www.capterra.co.uk/software/1100651/Marge-Up). Marge Up listing: AI analyses supplier invoices for ingredients, prices and tax. Not checked on own pages. | Unknown | Claimed | Claimed | Unknown |
| Epos Now's Jelly page | https://www.eposnow.com/uk/store/software/apps/jelly/: "Upload invoices or link Jelly directly to suppliers"; "increase your profit margin by up to 12%" (vendor claim). The page text does not mention AI or margin alerts. | No standalone price | n/a | Recipe costing yes | n/a |

Supplier-side free substitute (from the validator, not rechecked): Bidfood MyRecipes, free for Bidfood customers.

### 2. Does any gap survive?

- Plainly: **no gap survives on features.** Jelly already scans invoices, costs recipes, produces a GP report and shows price alerts at £129 per site on a monthly, cancel-anytime plan. MarketMan reads invoices with AI, costs recipes and flags price changes from $249. Profito and KitchenIQ (unverified) sell the same job at roughly €34 and $89.
- The scout's original gap (€/$199 to €/$249 and weeks of setup) is false. Jelly's own page says set-up takes about an hour to a day. This is a vendor claim, not independently checked.
- The only thing not seen on any own page is a written "here are three fixes" message (re-price, swap supplier, adjust portion). That is a feature one competitor could add in weeks, so it is not a moat. Jelly's pricing page does list a one-off setup fee (amount not stated) and "fair usage" on invoices, which is a small opening for a "no setup fee" offer, not a gap.
- A price gap exists only below the cheap tools: Profito Starter (unverified) is capped at 5 invoices a month, and KitchenIQ Pro is $89. A product at £30 to £50 would not be cheaper than Profito's entry tier, and would be at most about half of KitchenIQ. The cheap end is already served.
- Not checked: whether Jelly or Profito reviews report accuracy problems or per-invoice limits (G2 and Capterra review pages were not fetched). Item 1 in the validator's list is therefore only partly done. No evidence of poor accuracy was found.

### 3. Price sensitivity and multi-supplier buying

- No UK survey found that asks independents about willingness to pay for back-office software. Searches for subscription fatigue returned only vendor-commissioned work. Unverified for UK independents.
- Toast and Expert Market survey of 400 UK restaurant owners (vendor-commissioned): 80% feel at least "somewhat ready" to adopt new technology, and over 50% cite rising ingredient and energy costs as the biggest challenge (via search summary, https://www.expertmarket.com/uk/food-beverage/hospitality-predictions-for-2026, accessed 2026-11-23, page not fetched). It shows cost pressure but not price tolerance.
- A US piece, "Indies aren't sold on tech" (https://www.restaurantbusinessonline.com/technology/indies-arent-sold-tech-0), says independents are less convinced than chains that technology gives an advantage. Page returned 403, so this is from a search summary only, and it is US, not UK.
- Observed price ladder in the market (own pages or listings): about €34 (Profito entry, unverified), $25 (Kitchen Porter Tech), $89 (KitchenIQ, unverified), £129 (Jelly, own page), $249 (MarketMan Starter, own page). Cheap options already exist, and Jelly sells at £129, so evidence of independents refusing £129 is still missing. No public owner complaints about Jelly's price were found in this pass.
- Number of suppliers: **no figure found.** A search for UK surveys gave only indirect hints, none specific to restaurants: a 400-operator foodservice survey (care homes, pubs, fast food, school canteens) where 80% visit their wholesaler's website monthly, via a Craft Guild of Chefs summary (https://craftguildofchefs.org/news/caterers-demand-more-supply-chain-research-reveals, search summary only). The multi-supplier premise is therefore unverified. Jelly's own page markets "food ordering, costing and invoicing", which suggests it already handles several suppliers.

### 4. Summary for the re-score

- No surviving feature gap. The market has four or more AI invoice-to-GP tools from about €34 to $299 per month. Jelly alone, at £129, covers the UK independent case.
- The "£30 to £50 for independents" wedge is unsupported and sits at or below Profito's entry tier.
- Not done: the validator's item 4 (a 50-invoice synthetic accuracy benchmark). That is build work, not desk research.
- Scout's view: a re-score is unlikely to move Competition above about 3 and so unlikely to reach the pass bar. Spending the idea's last attempt looks poor value unless a new angle appears, for example a channel Jelly does not serve or an accountant-led offer. None was found.


## Proof-test kill test (T-80, pre-registered 2026-11-25, before any test run)

Full text: `products/restaurant-margin-copilot/KILL-TEST.md` (validator, run d8d4). Bars fixed before results: PASS needs line accuracy ≥95% overall, ≥90% distorted, ≥90% held-out layouts, reconciliation ≥90%, ≤1 unflagged wrong invoice, ≤$0.02/page, p95 ≤90 s, ≤2% failed pages. KILL on any of: overall <88%, distorted <80%, held-out <80%, ≥3 unflagged wrong invoices, >$0.05/page, >5% failures. A full PASS caps the score at 69 (Competition stays 3); reaching 70 also needs a measured gap vs Jelly (T-81).

## Kill (2026-11-25, validator, T-80)

**Result of the single TEST run** (branch `p/restaurant-margin-copilot/T-80`, commit 18d1470, `benchmark/results/test1/score.json`; 50 invoices, 66 pages, 684 ground-truth lines, gpt-5-mini, frozen config):

| Metric | Result | PASS bar | KILL line | Outcome |
|---|---|---|---|---|
| Overall line accuracy | 82.6% (571 / (684 + 7 hallucinated)) | ≥95% | <88% | **KILL** |
| Distorted photos (30 invoices) | 72.1% (300 / 416) | ≥90% | <80% | **KILL** |
| Held-out layouts (25) | 84.2% | ≥90% | <80% | fails PASS only |
| Clean renders (20) | 98.5% | (info) | | |
| Credit notes (10) | 97.9% | (info) | | |
| Reconciliation | 64% | ≥90% | | fails PASS |
| Silent-error invoices | 5 (TEST-004, 015, 033, 034, 039) | ≤1 | ≥3 | **KILL** (see caveat) |
| Cost per page | $0.0101 | ≤$0.02 | >$0.05 | passes |
| p95 latency | 82.9 s | ≤90 s | | passes |
| Failed pages | 0% | ≤2% | >5% | passes |

**Reason.** The idea's last G1 attempt rested on one claim: that a cheap model can read messy UK supplier invoices well enough to trust. It can read clean ones (98.5%), but on simulated phone photos, which are the product's main input, it got 28% of lines wrong. It also gave wrong numbers on 5 invoices whose totals still added up, so the product would not have flagged them. Three independent KILL lines fired, on bars fixed before the run. This is the idea's second failed G1 attempt, and Competition was already stuck at 3 against Jelly, MarketMan, Profito and KitchenIQ, so even a PASS could only have reached 69.

**Independent check of the scorer (validator, no model calls).** The totals were recomputed from `score.json`. Spot-checks against `data/test` ground truth:
- TEST-007 (broadliner A, photo): the model shifted the numbers by one row. "CREAM DBL 6X1L" got Mayo's "6 EA 9.73 … 58.38"; the truth is qty 1 at 15.41. This is a real model error.
- TEST-019 (broadliner A, photo): the model returned qty, price and total as 0 on all 10 lines, but read the invoice totals correctly. This is a real model error (calc gross 0.00 against 578.20).
- TEST-004 and TEST-034 (butcher): "DUCK BREAST X2 400G" was read as pack 2x400g where the truth is 400g, and "PORK SAUS 8S 454G" as 8x454g where the truth is 454g. TEST-033 (cash and carry): pack left blank for "BIN LINERS 200S" and "TISSUE CENTREFEED 6RL" (truth 200 and 6). Qty, price, total and VAT were all right. These are **ambiguous ground truth from the description text**, not scorer bugs: the scorer applied rule (c) as written.
- Credit-note signs scored correctly (97.9%), and no pack-parsing or sign bug was found.

**Caveat (does not change the verdict).** 11 wrong lines failed on pack alone, and 4 of the 5 silent-error invoices are made up only of those ambiguous pack lines. If every pack-only error counted as correct, the results would be: overall 84.2% (582/691), still below 88%; distorted at most 74.8%, still below 80%; silent errors about 1. The silent-error trigger therefore isn't robust, but the two accuracy triggers are, and either one alone is enough.

## Lessons

- **Clean structured invoices are solved on a mini model.** Clean renders scored 98.5% and credit notes 97.9%, at $0.01 a page. That is the part incumbents already sell, so it was never the wedge.
- **Phone-photo column drift is the blocker.** Distorted accuracy fell to 56% at the more severe half of rotations (87% at the milder half). Errors were mostly whole-row number shifts or blank numeric columns, not misread characters (only 3 description errors in 684 lines). DEV had flagged this at 75% on 5 photos. The 10-invoice DEV set was too small to tune against it, but big enough to predict the result.
- **Reconciliation catches most drift but not all.** It ran at 64%, which means it flags plenty. A real product would need a per-row check (qty × price = total) as a second guard. That check would still miss errors where the row's own arithmetic holds.
- **Pack ground truth must be unambiguous.** "X2 400G" and "8S 454G" can be read either way. Any future benchmark should either print the pack in its own column or score pack separately from price, qty and total.
- **The process worked.** The kill test was fixed before the run, the run happened once, it cost $0.67 of a $5 cap, and it killed the idea for about $1.10 in total instead of weeks of build.

## What would revive it

All of these, in order:
1. **A wedge first.** A measured gap against Jelly or Profito (T-81: the same invoices run through the rival, with mis-reads, fees or turnaround logged), or a channel Jelly prices out. Without one, Competition stays at 3 and the ceiling is 69.
2. **A new extraction design that fixes photo drift.** Options: deskew and perspective correction before the call, then row segmentation or OCR (for example the Document Intelligence free tier, 500 pages a month, 2 pages a request) feeding the model text with coordinates; or a pro-tier vision model. Cost implication: the pro model probably costs about 5 to 10 times mini per page (roughly $0.05 to $0.10, which crosses this test's $0.05 kill line and needs a new margin case for the £39 plan). A pre-processing pipeline keeps mini economics but adds build work and needs an Azure resource listed in `BUDGET.md`.
3. **A new kill test written before any run**, on a fresh seed with unambiguous pack ground truth, that passes. Then a re-score of 70 or more.
