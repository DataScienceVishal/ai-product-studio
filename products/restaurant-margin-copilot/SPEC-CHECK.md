# SPEC check (T-39): restaurant margin copilot, build plan under Q-6 option B

- Checker: validator, 2026-11-24. Checks `SPEC.md` (DRAFT) and `COMPETITORS.md` as a build plan.
- This is **not a G1 re-score**. The idea's last G1 attempt is unspent and its score stays 66 (G0, parked).
- Web text was read as data. Fetches went through a summarising tool, so quotes are as that tool returned them.

## Verdict: REVISE

The spec is honest about the main thing: "We are not better on features." It is buildable on the starter in about three weeks if the scope is cut a little. But four problems need fixing before build starts:

1. Half of the stated product wedge (price alerts on day one, before any recipes) is already on Jelly's own homepage.
2. The headline demo example is arithmetically impossible.
3. The plan conflicts with the starter's limits and with Q-7 in ways the spec does not resolve.
4. Q-6 does not actually default to B.

None of these makes B a waste, so this is not KILL. Fix them (list below) and the plan is ready.

## Spot-checks on vendors' own pages (fetched 2026-11-24)

| Claim in COMPETITORS.md | Own page | Result |
|---|---|---|
| Jelly: £129 per location per month; one-off setup fee per site, amount not stated; POS pass-on fee from £15; monthly cancel anytime; annual 10% off, locked to year end; "about 1 hour to a day" | https://www.getjelly.co.uk/pricing: "£129 per location per month. That's it."; "a one-time setup fee per site, which includes a customised 1-1 onboarding session"; "starting from £15 per month per location"; "cancel anytime"; annual "can't be canceled before the year ends", 10% off; "anywhere from 1 hour to a day" | **Confirmed.** One omission: the pricing page also lists **"Live price tracking"** as a separate item from "Recipe & menu costing". |
| Jelly: "the word AI not on the pricing page"; GP alerts "not on pricing page"; invoices-first value "no own page was seen to promise" (section 3c) | https://www.getjelly.co.uk/ (homepage): "Jelly's human-checked AI reads every line of every invoice"; "Daily notifications the moment a supplier moves a price"; "Price alerts and margin warnings actioned the same day"; "Spot the item that's quietly losing money this week"; invoices by "photo, forward the email, or connect your suppliers directly" | **Misleading by omission.** The homepage advertises AI reading checked by humans, daily price-move notifications and margin warnings. Per-ingredient price tracking needs no recipes by its nature. Section 3(c) and SPEC section 3 wedge 1 overstate the gap. No own-page text was found for written "do this" suggestions. A Jelly-branded article on an EC2 mirror says the tool shows affected dishes "so operators can decide" (search summary only, not an official page). |
| MarketMan Starter USD 249 (50 scans, 1 EDI), Growth 299, Enterprise from 449, email scanning an add-on, "first 3 months free" | https://marketman.com/pricing: "$249 /monthly", "50 AI-Powered Invoice Scans/mo", 1 vendor EDI; Growth "$299 /monthly" unlimited; Enterprise "From $449"; email scanning an add-on on Starter and Growth; "Get your first 3 months ... free" | **Confirmed.** |
| Dext £24.17 a month (£290 a year), 250 documents, 5 users; line-item add-on from £16.50 a month or £0.40 per document | https://dext.com/uk/business/pricing: same figures, ex VAT | **Confirmed.** Useful anchor: generic line extraction already sells for £0.40 per document. |

## (1) Is the wedge credible and honestly stated?

**Partly.** The spec's general honesty is good: it says there is no feature gap, there is copy risk, and willingness to pay is unproven. The specific wedge needs restating.

- **"Day-one price alerts before recipes" is not a wedge.** Jelly's homepage sends "Daily notifications the moment a supplier moves a price" and lists "Live price tracking" on its pricing page. Keep this as a fast first-value feature and a demo metric, but drop it from the wedge. COMPETITORS.md section 3(c) and the matrix's Jelly "GP alerts" cell should cite the homepage.
- **The weekly written fixes message is the only product wedge left, and it is thin.** Jelly already gives "margin warnings actioned the same day". The difference is a ranked, plain-English "here are three options with the numbers" summary. That is a presentation layer Jelly could add in weeks, which the spec admits. It is credible as a demo hook. It is not credible as a reason to switch from Jelly. It only helps owners who use nothing today.
- **Price: "£39 to £69 vs £129" is accurate, but compare like with like.** Jelly's £129 includes POS-linked actual margins, ordering, supplier connections and *human-checked* extraction (homepage). The MVP has none of these. The honest framing is "less product, much less money, no setup fee", not "the same job for a third of the price". The spec should say this in section 3. Our accuracy also has to compete with a human-checked rival, so the 3% wrong-auto-match bar is right and must not be loosened.
- **Unit economics are not yet credible at £39.** The T-12 pilot used about 27,600 output tokens for 5 documents (`state/BUDGET.md`), roughly 5,500 per document. At the assumed $120 per million that is about $0.66 (about £0.52) per invoice on pro. The Starter plan's 40 invoices would cost about £21 of a £39 price before hosting. Dext sells line extraction at £0.40. The spec's own £0.10 target depends entirely on Q-7 (a mini model), and the spec should say so in the pricing section, not only in section 7.

## (2) Buildable in 2 to 3 weeks on `_starter`, and does it reach the demo-able bar?

**Buildable, with cuts. The demo as specified does not yet meet `definition-of-done.md`.**

Starter facts the spec has not accounted for:
- `max_body_bytes` is 1,000,000 (`backend/app/config.py:28`). Phone photos and 5-page PDFs are often larger. The spec needs a per-route upload limit (for example 10 MB, upload route only), server-side downscaling, and a page limit.
- **The starter has no file storage.** No Blob resource is in `state/BUDGET.md`. Decide now: store files as Postgres bytea with a size cap and retention (free, fine for the demo), or ask before adding Blob storage. Add the files to `DATA.md` and the purge.
- **AI deadline:** `ai_deadline_seconds` is 25 s (`config.py:61`), and pro takes 70 to 150 s per document. The worker needs its own deadline and retry settings, separate from web requests.
- **The AI adapter shows no image or PDF input** (no image handling found in `backend/app/`). Multimodal input and PDF-to-image rendering (a new dependency, which needs pip-audit) are real work. Budget about 2 days for them.
- **Scale to zero vs a worker loop:** `ca-starter` scales from 0 to 1 (`BUDGET.md`), so a Postgres-polling worker inside the app stops when the app sleeps. Use a Container Apps job (like `caj-starter-purge`) for the weekly message, and a job or wake-on-request for the queue. Cost it in `BUDGET.md`.
- **The daily cap blocks even one live invoice.** On pro, the deployed $6.10 cap allows about 1,690 tokens a day (starter README). One invoice needs about 5,500 or more. Without Q-7, no live extraction can run on Azure inside the approved budget.

Against the bar: `definition-of-done.md` §1 needs a deployed stable URL, "a new user completes the core job **with their own data** in under 10 minutes", and a demo account with realistic data.
- The demo replays a pre-processed invoice "cached by file hash" and shows a true live run only as an example. That is an honest disclosure, but it does not meet "own data". SPEC §8's metric says "with demo data", which quietly lowers the bar. The demo must include at least one uncached invoice processed live end to end, within the 10 minutes.
- Scope is about 3 weeks only if these move to OUT or "if time": the recipe CSV import (keep pasted text), the email-in adapter (the mock adds nothing to the demo), and more than 2 degraded-variant types. The synthetic invoice generator with ground truth is itself 2 to 3 days. List it as a named week-1 task.
- Build the model-free parts first, so Q-7 delays do not stall the build: catalogue, alias and fuzzy matching, pack conversion, GP arithmetic, price-change detection, and the message from a template. These run on FakeAI today.

## (3) Are the kill criteria concrete and measurable?

**Mostly, with gaps.**
- #1 and #2: concrete (90% clean line accuracy; under £0.25 per invoice; under 5% wrong auto-matches; about 20 clicks). But "best available model" is pro only, and the £0.25 test cannot be run without Q-7. Say "pro measured; mini when Q-7 = A", and give calendar dates, not "end of week 1".
- #3 is not measurable: "Jelly or another vendor ships a written fixes message under £60, and we have no channel advantage" has no check method or date, and "channel advantage" is undefined. Replace it with a dated check (re-read Jelly's homepage and pricing page and the KitchenIQ listing at the end of each week) and a concrete trigger.
- #4 is fine (after unlock).
- #5 is right, but it means option B is really "B plus Q-7 A". Say so at the top of the spec.
- **Missing:**
  - (a) The option-B evidence itself. Define what "the demo is the evidence" means, for example: after a 5-minute demo, Vishal's friend says he would show it to at least 2 named kinds of customer at £39 or more. If not, stop at G3 and do not polish for G4.
  - (b) A **held-out benchmark**: score extraction on invoice layouts the prompts were not tuned on. Otherwise the generator and the extractor share our assumptions and 95% means little.
  - (c) The degraded-variant target (85%) has no kill line.
  - (d) "3 reviewers rate fixes as sensible" needs to say who the reviewers are and give a written rubric.

## (4) Changes needed before build starts (most important first)

1. **Fix the demo arithmetic.** "Beef mince up 12%, burger GP 68% to 61%, fix: +40p" is impossible. At 68% GP, food cost is 32% of price. A 12% rise in one ingredient moves GP by at most 0.12 x 32 = 3.8 points, and only if beef is the whole dish cost. A dish at about £14 that dropped 7 points would need about £3, not 40p, to recover. A worked consistent example: £14 burger, cost £4.48 (68%), beef 60% of cost. +12% beef gives cost £4.80 and GP 65.7%. The fixes are +£1.00, or patty 180 g to 165 g, which restores about 68%. A chef would spot the error in seconds. Generate the seed data and the message example from code, and add a test that the spec's example equals the computed output.
2. **Restate the wedge honestly.** Drop "day-one price alerts" as a differentiator, citing Jelly's homepage ("Daily notifications the moment a supplier moves a price", "human-checked AI", "margin warnings"). State "less product (no POS, ordering or human check) for much less money, no setup fee". Correct COMPETITORS.md: the Jelly row's AI and alerts cells, section 3(c), and "Live price tracking" on the pricing page.
3. **Resolve the process and budget dependencies at the top of the spec.**
   - Q-6's written default is A, not B, and its recommendation is C. Under CLAUDE.md §6 the studio cannot drift into B by default. It needs Vishal's yes, or a logged DECISIONS entry amending Q-6. Building it also skips the G1 gate, which must be logged as a deliberate exception.
   - State that live extraction needs Q-7 A, because the pro cap allows less than one invoice a day.
   - Put the per-invoice cost (about £0.52 on pro, measured) next to the £39 price.
4. **Add the starter deltas to the scope**: upload limit and downscaling, file storage choice and retention, worker deadline, multimodal adapter, PDF rendering, how the worker and weekly job run under scale-to-zero. Order the work model-free first. Move CSV import and email-in out of the MVP.
5. **Tighten the bar and the kill criteria**: one live, uncached invoice in the 10-minute demo (DoD "own data"); a held-out layout set; dated checks; a defined demo-evidence outcome from the friend; named reviewers and a rubric for the fixes message.

## Sources (accessed 2026-11-24)
- https://www.getjelly.co.uk/pricing
- https://www.getjelly.co.uk/
- https://www.getjelly.co.uk/product-tour (no feature text, video only)
- https://marketman.com/pricing
- https://dext.com/uk/business/pricing
- Jelly-branded article mirror (search summary only, not an official page): https://ec2-34-250-149-172.eu-west-1.compute.amazonaws.com/uk-restaurant-price-hike-alerts/
- Repo: `products/_starter/backend/app/config.py` (lines 28, 61), `products/_starter/README.md` ("Sizing the daily AI cap"), `state/BUDGET.md` (T-12 token log), `state/QUESTIONS.md` Q-6 and Q-7, `playbooks/definition-of-done.md` §1
