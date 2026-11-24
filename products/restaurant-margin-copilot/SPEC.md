# Restaurant margin copilot: SPEC

**DRAFT, revised 2026-11-24 after SPEC-CHECK (REVISE).** Selling is locked; every price is a hypothesis.

**Status and dependencies (read first)**
- **Process.** Q-6's written default was A. The studio logged a deliberate exception to build under option B (`state/QUESTIONS.md` Q-6; `state/DECISIONS.md` 2026-11-24T05:41Z). It skips the G1 gate: the idea scored 66 at G0 (REVISE) and its last G1 attempt is unspent. Nothing here is validated.
- **Option B is really "B plus Q-7 A".** The pro deployment's daily cap allows about 1,690 tokens a day (starter README, "Sizing the daily AI cap"); one invoice needs about 5,500. Without Q-7 A (a mini model or a larger approved budget), no live extraction runs on Azure. Model-free parts are built first, on the fake AI (section 4).
- **Evidence.** T-9 found no feature gap against Jelly or MarketMan. Under B the demo is the evidence, judged by the outcome defined in section 9.

Market facts are sourced in `COMPETITORS.md` and `state/ideas/restaurant-margin-copilot.md`. "Own page" means the vendor page was read on 2026-11-23 or 24.

## 1. Ideal customer profile

| | |
|---|---|
| Business | UK independent restaurant, gastropub or cafe, 1 to 3 sites, food-led (not drinks-led). |
| Size | About 5 to 40 staff, one head chef or chef-owner. Turnover and supplier count are not evidenced; assumptions to test. |
| Market | UK only: UK suppliers (Brakes, Bidfood, Booker, local butchers), pounds, VAT, UK units. |
| Does costing today | Owner or head chef, on a spreadsheet or in their head, late in the evening. Many do not cost at all. A bookkeeper may key invoices into accounts but never sees recipes. |
| Buys | The owner, often the chef-owner. Card, monthly, no procurement. |
| Uses | Chef or owner reads the weekly message; a manager or bookkeeper uploads invoices. |
| Trigger | A visible price shock (butter, beef, oil) or a month where sales were fine but profit was not. 88% of hospitality firms name food and drink cost inflation as a top non-tax concern (trade-body survey, see idea file); that shows pressure, not willingness to pay (T-9: no UK evidence found). |

Not our customer: groups of 4+ sites (Nory, Apicbase, Access) and single-supplier shops served free by Bidfood MyRecipes.

## 2. Jobs to be done and the core flow

Jobs (our paraphrase, not customer quotes):
1. Tell me when a price rise has hurt a dish, before the month ends.
2. Do it without me typing prices into a spreadsheet.
3. Tell me what to do about it, in plain English.

**Core flow. The demo must nail this, with a fresh upload, in under 10 minutes from sign-up:**

1. **Sign up and add a site.** Name, VAT-inclusive or not, target GP% (default 65%).
2. **Upload an invoice** (phone photo or PDF). It returns at once and a job is queued.
3. **Extract lines (async).** One model call per invoice gives supplier, date and, per line, description, pack text, quantity, unit price, line total, VAT. Code checks that lines sum to the invoice total; a mismatch flags the invoice for review.
4. **Match to ingredients, with one confirm screen.** Exact and fuzzy match against the site's alias table first; only unmatched lines go to the model, batched in one call, which proposes an ingredient and a pack conversion (for example "5kg case" to cost per kg) with a confidence. The owner confirms ("12 lines, 9 matched, 3 to check"). Confirmed matches are remembered.
5. **Recalculate.** Ingredient costs and each dish's cost and GP% are recomputed in code, never by the model. With no recipes yet it still shows price changes ("beef mince up 12% vs your last invoice"). This is a fast first-value step, not a differentiator.
6. **Recipes in.** Paste menu or recipe text; one model call structures it with portion weights; the owner confirms. Skippable at first.
7. **Weekly fixes message.** Each Monday, an email with numbers from code and options from a fixed lever menu (re-price, portion, swap supplier, drop or feature the dish). Worked example, which the code must reproduce exactly: a 14 pound burger costs 4.48 (GP 68.0%), beef is 60% of cost. Beef up 12% makes cost 4.80 and GP 65.7%. Fixes: raise the price by 1.00 (GP back to 68.0%), or cut the patty from 180 g to 165 g (GP about 67.5%), or ask the butcher about a bulk case.
8. **Notify when async work finishes** ("Invoice ready: 14 lines, 2 to check") in-app and by email.

## 3. Wedge versus Jelly and MarketMan (honest)

Own-page facts: Jelly is 129 pounds per location per month, plus a one-off setup fee (amount not stated) and a POS pass-on fee from 15 pounds; monthly cancel anytime. Its homepage advertises "human-checked AI" reading every invoice line, "Daily notifications the moment a supplier moves a price" and "margin warnings actioned the same day"; its pricing page lists "Live price tracking" and "Recipe & menu costing". MarketMan Starter is 249 US dollars a month with 50 AI scans. Unverified listings: KitchenIQ 89 US dollars, Profito from 34 euros (5 invoices a month).

**We are not better on features, and day-one price alerts are NOT a differentiator.** Jelly has them. What is left:

1. **Less product for much less money, no setup fee (the main wedge).** No POS link, ordering, supplier connections or human check, at 39 to 69 pounds against 129 plus setup. This is not "the same job for a third of the price". Our accuracy must still stand up against a human-checked rival, so the wrong-auto-match limit in section 8 is not loosened.
2. **The written weekly fixes message (thin, a demo hook).** Jelly shows alerts and warnings; T-9 found no own-page text for plain-English, numbered "do this" options. Jelly could add it in weeks. It helps most owners who use nothing today; it is not a reason to leave Jelly.

Not chosen: setup speed (Jelly claims same-day, so it is a measured demo metric only) and a bookkeeper-led channel (possibly strongest for reach, but needs conversations, which are locked; first thing to test after unlock).

## 4. MVP scope: Must, Should, Won't

Target: about 3 weeks of builder runs on `products/_starter`, if everything listed under Must fits. Starter gaps found by SPEC-CHECK are scoped explicitly.

**Build order (model-free first, so Q-7 delays never stall the build)**
- **Week 1, on the fake AI:** synthetic invoice generator with ground truth (named task, 2 to 3 days); ingredient catalogue, alias and fuzzy matching, pack conversion; GP arithmetic and price-change detection; weekly message from a template; file storage and upload limits; job queue and worker. Test: the section 2 burger example equals the code output.
- **Week 1 to 2, needs Q-7 A:** image and PDF input in the AI adapter, extraction prompt, confirm screen, held-out benchmark run.
- **Week 2 to 3:** recipe import, message wording by model, demo tenant, end-to-end test, Azure deploy.

**Must**
- Starter as is: sign-in, tenancy, billing (mock), logs, delete-my-data.
- One site per account (schema allows several).
- **File storage:** starter has none and no Blob is budgeted. Store invoice images and PDFs as Postgres `bytea` with a size cap and a retention period; add them to `DATA.md` and the purge. Blob only after asking.
- **Upload limit:** `max_body_bytes` is 1,000,000 (`backend/app/config.py:28`). Raise it on the upload route only (about 10 MB), cap at 5 pages, downscale images on the server.
- **Async worker that survives scale to zero:** `ca-starter` scales 0 to 1, so an in-app polling loop stops when the app sleeps. Use a Container Apps job (like `caj-starter-purge`) that drains the queue, started on upload, plus a scheduled job for the Monday message. Cost them in `state/BUDGET.md`. The worker has its own deadline and retries (`ai_deadline_seconds` is 25 s; pro needs 70 to 150 s).
- **Image and PDF input in the AI adapter** (none exists today), with PDF-to-image rendering. A new dependency needs pip-audit. Budget about 2 days.
- **AI cap sizing:** set `AI_GLOBAL_DAILY_TOKENS` and `AI_PRICE_PER_MILLION_TOKENS` together for the chosen deployment (cost guard enforces $6.10 a month). On pro, one invoice exceeds the daily cap; so live runs need Q-7 A.
- Extraction to schema-validated JSON with arithmetic check and a "needs review" state.
- Catalogue, alias table, fuzzy match, one-call model fallback, confirm screen, base-unit conversion (g, ml, each).
- Recipe import from pasted text, confirm screen, dish GP table sorted by margin.
- Price-change detection per ingredient; weekly GP delta per dish.
- Weekly fixes email: numbers from code, wording from one short model call, template fallback.
- Demo tenant on synthetic data (section 6) and the evaluation harness (section 8).

**Should (only if Must is done and green)**
- A third degraded-variant type; second email recipient; "what if I raise the price" calculator in code.
- Azure Document Intelligence free tier as an OCR pre-step (unverified, check in week 1).

**Won't (this MVP)**
- Recipe CSV import, email-in (even as a mock; it adds nothing to the demo), WhatsApp, SMS.
- POS, Xero or accounting links; ordering or EDI; stock-takes, wastage, allergens.
- Multi-site roll-ups, bookkeeper multi-client view, roles beyond owner and staff.
- Credit notes, delivery-note matching, handwritten invoices.
- Price optimisation beyond the lever menu; learning across customers.
- Live payments, public landing page, outreach, real customer data.

## 5. Pricing hypothesis (GBP, selling locked)

Per-invoice model cost, measured in T-12 (`state/BUDGET.md`): about 27,600 output tokens for 5 documents, roughly 5,500 per document. At the assumed 120 US dollars per million, that is about 0.66 dollars, **about 0.52 pounds per invoice on pro** (price assumption, check the Azure list). On a mini model at the starter's 2 dollar blend the token cost is about 1 cent; allowing for image input and retries, **assume 0.03 to 0.10 pounds per invoice on mini, to be measured**. Dext sells line extraction at 0.40 pounds per document (own page), which caps what buyers may think it is worth.

| Plan | Price per site | Invoice cap | Model cost at cap (pro / mini) | Includes |
|---|---|---|---|---|
| Free trial | 14 days, no card | 10 invoices | about 5.20 / 0.30 to 1.00 | full flow |
| Starter | 39 per month | 25 a month | about 13 / 0.75 to 2.50 | price alerts, weekly message, recipes up to 40 dishes |
| Standard | 69 per month | 60 a month | about 31 / 1.80 to 6 | unlimited recipes, second email recipient |
| Early customers | first 5: free 3 months, then 50% off for 12 months | as plan | | 20-minute feedback call, anonymised results |

The caps are chosen so both models work: on pro, Starter leaves about two thirds of the price and Standard about 55%, before hosting (a stopgap, not a business); on mini the margin is above 90%. Extra invoices cost a per-invoice top-up or are blocked by a hard per-tenant cap. If Q-7 is not A, the plan holds only for the demo and the trial; **no real pilot should run on pro.** 25 invoices a month may be too few for a kitchen with 4 suppliers; test it in the demo, not by assumption.

Value tie (assumption-based): a site turning over 400,000 a year loses 4,000 per GP point, about 333 a month. 39 to 69 pays for itself if the message recovers a fraction of a point. The turnover figure is unchecked.

Anchors (sources in `COMPETITORS.md`): Jelly 129 plus setup (own page); MarketMan from 249 US dollars (own page); Dext 24.17 pounds, 250 documents (own page); KitchenIQ 89 US dollars and Profito from 34 euros with a 5-invoice cap (unverified).

## 6. Demo plan (synthetic data only)

- **Fictional business:** "The Crown & Anchor", 60-cover gastropub, 24-dish menu, 4 suppliers (broadliner-like x2, cash and carry, local butcher).
- **Tuning set vs held-out set.** Generate 30 invoices over 8 weeks across 3 layouts for tuning. Generate a separate **held-out set of at least 3 further layouts (about 5 invoices each) that are never used to tune prompts or matching**; the generator for them is written after the prompts are frozen. Layouts imitate general structure only; no real branding.
- **Degraded variants:** two types in Must (phone photo with skew and shadow; split-page PDF), a third in Should.
- **Story arc:** weeks 1 to 4 stable; week 5 beef mince +12%; the burger falls from 68.0% to 65.7% and the Monday message gives the section 2 fixes. Seed data and message come from code.
- **Demo script (5 minutes):** sign up; upload a **fresh, uncached invoice photo** and watch it queue and finish live; confirm 3 matches; see the dish table change; open the weekly message. Pre-processed data may fill the history only; the live upload is never replaced by a cached result. A run that takes 2 minutes is shown as such.

## 7. Cost and async design

- Every AI step is a queued job, never in a web request. One call per invoice (downscaled, needed pages only, strict schema, short output); matching and all arithmetic in code; the model is used for extraction, unmatched-line matching (batched), recipe parsing and message wording. No cache is needed for the bar; a hash cache may exist to avoid double charges, but the demo never relies on it.
- **Model routing:** the adapter takes a named deployment per task, so extraction can move to mini with one setting (`AZURE_OPENAI_DEPLOYMENT_MINI`); pro only for low-confidence pages.
- Benchmark spend: roughly 20 documents on pro (about 15 dollars, Q-7 option B) without Q-7 A; the full 30 plus held-out set needs it.

## 8. Success metrics (demo, synthetic data)

| Metric | Target | Method |
|---|---|---|
| Line extraction, clean, tuning set | at least 95% of lines fully correct | harness vs ground truth |
| Line extraction, **held-out layouts** | at least 90% | same harness, held-out set, run once after prompts freeze |
| Line extraction, degraded photos | at least 85% | harness |
| Wrong invoices flagged by total check | at least 90% | harness |
| Auto-match wrong rate | under 3% (accuracy against a human-checked rival) | harness |
| Pack and unit conversion | at least 95% | harness |
| Fresh upload to first GP report | under 10 minutes of owner time; price change visible in under 3 | timed script, 3 runs |
| Confirm effort | under 10 clicks per invoice after week 1 | click count |
| Cost per invoice | measured on pro and mini, written down; target under 0.10 on mini | token log |
| Weekly message | numbers 100% equal to code; fixes rated "sensible and actionable" by at least 4 of 5 | see below |

**Fixes message review.** Reviewers: the `reviewer` agent, the `validator` agent, and the `gtm` agent in a "restaurant owner" role (three distinct roles, not the builder); Vishal as optional fourth and fifth. Written rubric, each scored yes or no: (1) every number matches the code; (2) the cause is named (which ingredient, how much); (3) each option is a real lever with its effect in pounds or points; (4) options are consistent (for example, a +40p fix is never claimed to restore 7 points); (5) under 120 words and plain English. Pass: at least 4 of 5 criteria for at least 2 of 3 reviewers on 5 sample messages.

**Pilot (after unlock, not before):** activation = first invoice confirmed within 24 hours of sign-up; weekly use = at least 1 invoice a week and the message opened for 4 weeks; value = owner hours saved a week (self-reported) and any price or portion change made because of a message.

## 9. Risks and kill criteria

Risks:
- Crowded market with no feature gap (T-9); we win on price and message only.
- Willingness to pay of independents is unproven at 39 or 129.
- Jelly could add a fixes message, a low tier, or already has daily alerts.
- Synthetic accuracy is not real accuracy; crumpled real photos are untested.
- Free substitute (Bidfood MyRecipes) for single-supplier kitchens; supplier count unknown.
- Model cost and latency depend on Q-7; unit economics fail on pro.
- Low regulatory risk (business documents); keep personal data minimal.

**Demo-evidence outcome (what "the demo is the evidence" means).** After the 5-minute demo, Vishal's friend says he would show it to at least 2 named kinds of customer (for example a gastropub owner and a cafe owner) at 39 pounds or more. If not, stop at G3 and do not polish for G4. Recorded in `state/DECISIONS.md`; check once, within a week of the demo being ready.

**Kill and stop criteria.** Dates assume build starts 2026-11-25 and slip day for day if Q-7 or the start slips.

| # | Criterion | Date | Check method |
|---|---|---|---|
| 1 | Line extraction under 90% on the clean tuning set with the best available model (pro measured; mini when Q-7 = A), or cost per invoice cannot get under 0.25 pounds on mini | 2026-12-02 | harness report in `products/restaurant-margin-copilot/` |
| 2 | Held-out layout accuracy under 80%, or degraded photos under 75% after one prompt revision | 2026-12-09 | harness, held-out run, once |
| 3 | Auto-match wrong rate above 5% after the confirm step is tuned, or more than about 20 clicks per invoice | 2026-12-09 | harness and click count |
| 4 | Competitor trigger: Jelly or KitchenIQ publishes a written weekly "what to do" message **at under 60 pounds a month**, or Jelly adds a tier under 60 | re-checked every Tuesday from 2026-12-02 | re-read Jelly homepage and pricing page and the KitchenIQ listing; log in `COMPETITORS.md` |
| 5 | Q-7 is not A by 2026-12-02 | 2026-12-02 | `state/QUESTIONS.md`; stop at the model-free prototype |
| 6 | Friend demo outcome (above) fails | within 7 days of demo-ready | DECISIONS entry |
| 7 | After unlock: 10 owner or bookkeeper conversations with fewer than 3 saying they would pay 39 pounds or more | after unlock | conversation log |

## 10. Open questions

- Q-7 answer (mini model or budget); without it this is a prototype only.
- Postgres `bytea` storage versus Blob (Blob needs approval and a BUDGET entry).
- Is a bookkeeper channel real through the friend's network? It changes user and price.
- Jelly's exact setup fee and fair-use limit; do independents buy from one broadliner or several?
- Real inbound and outbound email need paid services (Q-5); WhatsApp needs a paid business account.

## Changes after SPEC-CHECK

1. Demo arithmetic corrected: 14 pound burger, GP 68.0% to 65.7%, fixes +1.00 or 165 g patty; code must reproduce it, with a test and a rubric line catching inconsistent fixes.
2. Wedge restated: day-one alerts dropped (Jelly has daily price notifications and live price tracking); "less product for much less money, no setup fee" plus the thin fixes message. COMPETITORS.md section 3(c), the Jelly row and the "missing" bullet corrected.
3. Unit economics: about 0.52 pounds per invoice on pro and 0.03 to 0.10 assumed on mini; invoice caps lowered (trial 10, Starter 25, Standard 60) so both work; real pilots need Q-7 A.
4. Starter gaps added to scope (file storage, upload limit, scale-to-zero worker and scheduled job, image and PDF input, cap sizing); build ordered model-free first; CSV import and email-in moved to Won't.
5. Kill criteria dated with check methods; held-out layouts, a degraded-photo kill line, a defined friend-demo outcome, named reviewer roles and rubric added; the cached-invoice-only demo removed; process status (Q-6 exception, Q-7 A dependency) put at the top.
