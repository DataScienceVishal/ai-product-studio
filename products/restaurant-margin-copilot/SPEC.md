# Restaurant margin copilot: SPEC

**DRAFT, pending Q-6.** Written so building can start at once if the studio defaults to option B. Nothing here is validated: the idea scored 66 at G0 (REVISE), and the T-9 evidence says no feature gap survives against Jelly or MarketMan. Under option B the demo is the evidence. Selling is locked; every price below is a hypothesis.

Sources for market facts are in `state/ideas/restaurant-margin-copilot.md` (T-9 section). "Own page" means the vendor's page was fetched on 2026-11-23. "Unverified" means a listing or search summary only.

## 1. Ideal customer profile

| | |
|---|---|
| Business | UK independent restaurant, gastropub or café, 1 to 3 sites, table or counter service, food-led (not drinks-led). |
| Size | Roughly 5 to 40 staff, one head chef or chef-owner. Turnover and supplier count are not evidenced; treat as assumptions to test. |
| Market | UK only at first: UK suppliers (Brakes, Bidfood, Booker, local butchers and greengrocers), pounds, VAT, UK units (kg, litres, case sizes). |
| Does costing today | The owner or head chef, on a spreadsheet or in their head, late in the evening. Many do not cost at all. In some businesses a bookkeeper keys the invoices into accounts software but never sees recipes. |
| Buys | The owner (often the chef-owner). Card payment, monthly, no procurement. |
| Uses | Chef or owner weekly (the message), a manager or bookkeeper to upload invoices. |
| Purchase trigger | A visible price shock (butter, beef, oil) or a bad month where sales were fine but profit was not. The trade-body survey (88% name food and drink cost inflation as top non-tax concern) shows the pressure; it does not show independents' willingness to pay (T-9: no UK evidence found). |

Not our customer: groups of 4+ sites (Nory, Apicbase, Access), single-supplier shops already served free by Bidfood MyRecipes.

## 2. Jobs to be done and the core flow

Jobs, in the owner's words (our paraphrase, not quotes):
1. Tell me when a price rise has hurt a dish, before the month ends.
2. Do it without me typing prices into a spreadsheet.
3. Tell me what to do about it, in plain English.

**Core flow (the demo must nail this, in under 10 minutes from sign-up):**

1. **Sign up and add a site.** Name, VAT-inclusive or not, target GP% (default 65%).
2. **Send an invoice.** Upload a phone photo or PDF, or forward by email (email-in behind an adapter, mock in demo). The upload returns instantly; a job is queued.
3. **Extract lines (async).** One model call per invoice produces supplier, date, and per line: description, pack text, quantity, unit price, line total, VAT. Totals are checked in code (lines sum to invoice total); a mismatch flags the invoice for review.
4. **Match to ingredients, with a confirm step.** Deterministic first: exact and fuzzy match against the site's alias table. Only unmatched lines go to the model, batched in one call, which proposes an ingredient and a pack-size conversion (e.g. "5kg case" to cost per kg) with a confidence. The owner confirms in a single screen ("12 lines, 9 matched, 3 to check"). A confirmed match is remembered, so each supplier line is confirmed once.
5. **Recalculate costs and GP.** Cost per ingredient updates; each dish's cost and GP% is recomputed in code (no model in the arithmetic). Before any recipes exist, the product still works as a **price-change alert** ("beef mince up 12% vs your last invoice").
6. **Recipes in.** Paste a menu or recipe text (or a spreadsheet); one model call turns it into structured recipes with portion weights; the owner confirms. Skippable at first.
7. **Weekly "fixes" message.** Each Monday, an email (WhatsApp later, behind an adapter) such as: "Beef mince up 12%. Your burger GP fell from 68% to 61%. Three options: raise price by 40p, cut patty from 180g to 165g, or ask your butcher about the 10kg case." Numbers come from code; the model only words the message and proposes options from a fixed menu of levers (re-price, portion, swap supplier, drop or feature the dish).
8. **Notify when async work finishes** ("Invoice ready: 14 lines, 2 to check") by email and in-app.

## 3. Wedge versus Jelly and MarketMan (honest)

Facts from own pages (2026-11-23): Jelly is £129 per site per month, cancel anytime monthly, one-off setup fee of unstated amount, claims same-day set-up, does invoice scanning, recipe costing, GP report and price alerts. MarketMan Starter is $249 a month with 50 AI scans, recipe costing and price-change flags. Unverified: KitchenIQ $89, Profito from EUR 34 (capped at 5 invoices on Starter).

**We are not better on features. Jelly covers the same job.** The strongest two angles, in order:

1. **Weekly written fixes message plus invoice-only value on day one (the product wedge).** Competitors show alerts and dashboards; T-9 found no own-page text for written fix suggestions at Jelly (KitchenIQ "suggested pricing" is unverified). Dashboards need someone to open them; a message that arrives and says what to do suits a chef with no time. Value starts before any recipe is entered, so minutes-to-first-value is short. Caveat: Jelly could add this in weeks, so it is a head start, not a moat. Whether it changes behaviour is exactly what the demo and a pilot must show.
2. **Price well under £129 with no setup fee (the commercial wedge).** A £39 to £69 band undercuts Jelly by about half or more, and is above Profito's capped entry tier but with a real invoice allowance. Caveat: cheap tools already exist ($25 to $89), so price alone does not win; it only removes an objection if the fixes message works. Evidence that independents refuse £129 is still missing.

Not chosen as the lead:
- **Setup time in minutes.** Jelly claims same-day set-up on its own page, so "fast" is table stakes. We keep it as a measured demo metric, not a claim.
- **Accountant or bookkeeper-led channel.** Potentially the strongest fix for Reach and Competition (one bookkeeper serves many independents; Jelly's own page lists Xero, so they sell to the owner, not the practice). But it needs real conversations, which are locked, and it is Q-6 option C territory. Keep it as the first thing to test once selling unlocks; design multi-client access later, not in the MVP.

## 4. MVP scope (about 2 to 3 weeks of builder work on `products/_starter`)

**IN**
- Reuse the starter as is: sign-in, tenancy, billing (mock), AI cap, logs.
- Site and settings (one site per account in MVP; schema allows several).
- Invoice upload (JPEG, PNG, PDF, up to 5 pages), stored per tenant; email-in as an adapter with a mock (no real inbound mail).
- Async job queue in Postgres (table plus worker loop; no new infrastructure), status page, in-app and email notification through the existing email adapter (mock until Q-5 approves a real one).
- Extraction to structured JSON with schema validation and arithmetic check; a "needs review" state.
- Ingredient catalogue, alias table, fuzzy matching, one-call model fallback for unmatched lines, confirm screen, pack-size conversion to a base unit (g, ml, each).
- Recipe import from pasted text or CSV, confirm screen, dish GP table sorted by margin.
- Price-change detection per ingredient and per dish GP delta week on week.
- Weekly fixes message: scheduled job, email only, numbers from code, wording from one short model call (template fallback if the call fails).
- Demo tenant seeded with synthetic data (section 6); delete-my-data and data inventory from the starter.
- Evaluation harness: scripts that score extraction and matching against the synthetic ground truth.

**OUT (not in MVP)**
- POS, Xero or accounting integrations; supplier ordering or EDI; stock-takes and wastage; allergen management.
- WhatsApp (adapter stub only), real inbound email, SMS.
- Multi-site roll-ups, bookkeeper or practice multi-client view, roles beyond owner and staff.
- Credit-note reconciliation, delivery-note matching, handwritten invoices.
- Menu price optimisation beyond the fixed lever menu; any learning across customers.
- Live payments, public landing page, outreach of any kind (all locked).
- Real customer data. The MVP is demonstrated on synthetic data only.

## 5. Pricing hypothesis (GBP, hypothesis only, selling is locked)

| Plan | Price per site | Includes |
|---|---|---|
| Free trial | 14 days, no card | 15 invoices, full flow |
| Starter | £39 per month | 40 invoices a month, price alerts, weekly fixes message, recipes up to 40 dishes |
| Standard | £69 per month | 120 invoices a month, unlimited recipes, second email recipient (bookkeeper) |
| Early customer offer | First 5 customers: free for 3 months, then 50% off for 12 months, in return for a 20-minute feedback call and permission to use anonymised results | |

Value tie (arithmetic with assumptions, not a market fact): if a site turns over £400,000 a year, one percentage point of GP is £4,000 a year, about £333 a month. At £39 to £69 the product pays for itself if it recovers a fraction of one point, or saves roughly an hour of costing time a week at an owner's time value. The turnover figure is an assumption to check.

Anchors: Jelly £129 per site plus setup fee (own page); MarketMan from $249 (own page); KitchenIQ $89, Profito from EUR 34 with 5-invoice cap (unverified); Kitchen Porter Tech US$25 per location (listing, manual entry). Our band sits in the gap between the cheap capped tools and Jelly.

Cost check: at pro-model prices, invoice extraction is the cost driver (about 70 to 150 s and several thousand tokens per document). Margins at £39 depend on moving to a mini model (Q-7); see section 7.

## 6. Demo plan (synthetic data, no real customer data)

- **Fictional business:** "The Crown & Anchor", a 60-cover gastropub, one site, 24-dish menu, 4 suppliers (a Brakes-like and a Bidfood-like broadliner, a Booker-like cash and carry, a local butcher).
- **Invoices:** 30 synthetic invoices over 8 weeks (generated from templates with known ground truth): about 10 per layout style (broadliner multi-page with pack codes like "12x1L", cash and carry with VAT columns, a butcher's plain one-page). Include 6 degraded variants: phone photo with skew and shadow, a credit note, a split-page PDF, a handwritten-style total. Layouts imitate general structure only; no real supplier branding or logos.
- **Story arc:** weeks 1 to 4 stable; week 5 the butcher's beef mince rises 12% and olive oil rises 15%; the burger GP falls from 68% to 61% and the Monday message arrives with three fixes. This is the 5-minute demo.
- **Demo script (5 minutes):** upload an invoice photo, watch the queue, confirm 3 matches, see the dish table change, open the weekly message, ask "what if I raise the burger by 40p" (computed in code, not by the model).
- **Pre-computed fixtures:** because live pro calls take 70 to 150 s each, the demo tenant is seeded with processed results, and the live upload uses one invoice processed in advance in the same code path (cached by file hash), with a true live run shown only as a "this takes about 2 minutes" async example.

## 7. Cost and async design (premium model only until Q-7)

- Only gpt-5.4-pro is reachable: slow (70 to 150 s per document) and expensive. The starter's own guidance (README, "Sizing the daily AI cap") works out that at an assumed $120 per million output tokens the current $6.10 monthly budget allows about 1,690 tokens a day. That is one or two documents. The full 30-invoice benchmark would need Vishal's approval to spend; without Q-7 the studio is limited to roughly 20 documents (about $15, per Q-7 option B).
- **Design rules:** every AI step is a queued job, never inside a web request; the UI shows "processing, we will email you"; one call per invoice (image downscaled, only needed pages, strict JSON schema, short output); deterministic matching and all arithmetic in code; model used only for extraction, unmatched-line matching (batched), recipe parsing and message wording; cache by file hash so a re-upload costs nothing; per-tenant and global caps from the starter.
- **Model routing:** write the adapter to take a named deployment per task, so extraction can move to the mini deployment (`AZURE_OPENAI_DEPLOYMENT_MINI`) with one setting. Keep pro for hard or low-confidence pages only.
- Azure Document Intelligence free tier (500 pages a month, first 2 pages per request) is a possible cheap OCR pre-step; unverified, to check in week 1.

## 8. Success metrics for the demo (what proves it works, on synthetic data)

| Metric | Target |
|---|---|
| Line extraction accuracy (description, quantity, unit price, line total all correct) | at least 95% of lines on clean invoices; at least 85% on degraded variants |
| Invoice total check catches wrong extraction | at least 90% of wrong invoices flagged for review |
| Match accuracy, first confirmed pass (auto-matched lines that are correct) | at least 90%; wrong auto-match rate under 3% (wrong prices destroy trust) |
| Pack-size and unit conversion correct | at least 95% |
| Time to first GP report from sign-up with demo data | under 10 minutes of owner time (definition of done); invoices-only price alert in under 3 minutes |
| Owner confirm effort | under 10 clicks per invoice after the first week |
| Cost per invoice | known and written down; target under £0.10 on the mini model (assumption to test) |
| Weekly message | numbers 100% match the code-computed values; 3 reviewers rate fixes as sensible and actionable |

The pilot (after selling unlocks, not before): activation = first invoice confirmed within 24 hours; weekly use = at least 1 invoice a week and the message opened for 4 weeks; value = hours saved per week and any price or portion change the owner made because of a message.

## 9. Risks and kill criteria

Risks:
- **Crowded market, no feature gap (T-9).** Jelly, MarketMan, Profito, KitchenIQ and Access all cover the job. We win only on message quality, price and, later, channel.
- **Willingness to pay of independents is unproven.** No UK evidence found at £39 or £129.
- **Free substitute:** Bidfood MyRecipes is free for Bidfood customers; single-supplier kitchens may not need us. Number of suppliers per independent is unknown.
- **Synthetic accuracy is not real accuracy.** Passing the benchmark does not prove crumpled real photos work.
- **Copy risk:** a competitor adds a fixes message in weeks.
- **Model cost and latency** until Q-7; margins unclear on pro.
- Low regulatory risk (business documents). Keep personal data minimal.

Kill or stop criteria (checked at the end of weeks 1, 2 and 3):
1. End of week 1: line extraction below 90% on clean synthetic invoices with the best available model, or cost per invoice cannot get under £0.25 even with the mini model.
2. End of week 2: auto-match wrong rate above 5% after the confirm step is tuned, or confirming takes more than about 20 clicks per invoice.
3. Before any outreach: Jelly or another vendor ships a written fixes message at a price under £60, and we have no channel advantage.
4. Once selling unlocks: 10 owner or bookkeeper conversations with fewer than 3 saying they would pay £39 or more.
5. If Q-7 is not answered, the benchmark cannot run: stop at the week-1 prototype rather than build blind.

## 10. Open questions

- Q-6 and Q-7 answers (this spec is only useful under option B; option C would change the channel and scope).
- Is a bookkeeper-led channel realistic through the friend's UK network? It would fix Reach and may change the user (bookkeeper) and price (per client).
- Exact Jelly setup fee and fair-use limit (not stated on the pricing page).
- Do independents buy from several suppliers, or mostly one broadliner? (No figure found.)
- Real inbound email and a real email sender need paid services (ask first, Q-5).
- Do we show the weekly message by WhatsApp? Needs a paid business account (ask first).
