# T-107 scout: capital vs revenue classifier for UK accountancy practices

Date: 2026-11-26. Desk check, about 12 searches and 6 page fetches. All claims are from public pages accessed 2026-11-26.

## Verdict: DROP (no idea file written)

Reason: the problem is real but the evidence for willingness to pay is missing and no wedge survives. The job is bundled inside a fixed year-end fee and has no price of its own. Practitioner pain evidence is thin and mostly HMRC and ACCA guidance, not complaints about hours lost. Two AccountingWEB forum threads came up, but AccountingWEB returned HTTP 403 on fetch, so I saw only search snippets.

## Pain signals (3 found, all weak to moderate)
1. HMRC BIM46905: "It is therefore a tax question whether expenditure on 'repairs' is capital or revenue and accountancy practice has no role in deciding the answer." https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim46905 (seen via search snippet). This shows the judgement is a tax question the practitioner owns, so liability stays with the practice.
2. ACCA, "Self assessment: repair or capital" (Jan 2024). It calls the split "fundamental" and warns that "the use of modern materials may give an apparent element of improvement". It does not say this is a common error or enquiry area. https://www.accaglobal.com/uk/en/technical-activities/uk-tech/in-practice/2024/January/Self-assessment-repair-or-capital.html
3. Tribunal cases (via search summaries, not read in full): a yard resurfacing of about £74,000 held not capital (https://rossmartin.co.uk/sme-tax-news/4867-resurfacing-was-not-a-capital-improvement, redirects to 2020innovation.com), and Moonlight Textiles, where £34,000 was held capital after an enquiry (https://taxjournal.com/articles/moonlight-textiles-ltd-v-hmrc). Disputes happen, but these are single large-ticket items. A per-line classifier would not have decided them.
4. AccountingWEB threads (snippets only, not fetched): a pub client with big year-end repairs and improvements spend (https://www.accountingweb.co.uk/node/107922 or nearby node), "Roof repairs - Revenue / Capital" (https://www.accountingweb.co.uk/any-answers/roof-repairs-revenue-capital) and "Lift refurb capital or revenue" (https://www.accountingweb.co.uk/node/55328). They show practitioners ask peers about edge cases. They give no hours or cost. The one thread on capital allowances software is from 2009 (https://www.accountingweb.co.uk/node/38379).

No source I found says the work takes hours, is mis-coded at scale, or is a cost the practice wants to remove.

## Price points
- All-in small-company year-end accounts plus CT600, bundled with capital allowances: roughly £600 to £1,800 a year (vendor sites summarised by search, for example https://www.ukpropertyaccountants.co.uk/cost-to-file-company-accounts/). Asset registers are sometimes listed as an add-on with no price. The classification job has no separate price, so the practice's saving per client is a fraction of a bundled fee.
- Specialist capital allowances firms charge a percentage of the claim, with the rate agreed once the claim is quantified, and many act no win no fee: Hillier Hopkins https://hillierhopkins.co.uk/wp-content/uploads/2021/01/capital-allowances-on-properties_65ef0.pdf and Swansea Council https://www.swansea.gov.uk/emptyproprtiesallowancesandrelief. I found no published percentage. That market is surveyor-led (RICS accredited, per https://taxadvisermagazine.com/article/unclaimed-capital-allowances-engaging-specialist-surveyor). It needs site surveys and fit-out drawings, and the claim is one-off per property transaction. Software cannot serve it. Dropped as a segment.
- Tool prices: AssetAccountant for Xero is "priced on your asset volume", with no figure published (https://apps.xero.com/uk/function/accountant-tools-extras/app/assetaccountant). IRIS Fixed Asset Register has no price, demo only (https://www.iris.co.uk/products/iris-fixed-asset-register/). So there are no published substitute prices. Bookkeeper hourly rates for fixed-asset register work: not found.

## Incumbents (vendor pages)
- Xero fixed asset management: creates draft assets from bills, depreciation, capital allowances recorded in Xero Tax (https://www.xero.com/uk/accounting-software/fixed-asset-management/). The user decides what is an asset.
- AssetAccountant (Xero app): flags bills allocated to a fixed-asset account as Draft Assets. The page mentions no AI and no capital-or-revenue decision.
- IRIS Fixed Asset Register: links to IRIS Business Tax and Accounts Production. No AI and no capital/revenue judgement on the page.
- Sage corporation tax and CCH registers push additions to tax systems (vendor help pages, from search snippets only). Thomson Reuters OneSource has capital allowance sheets.
- Dext, AutoEntry and Hubdoc: the searches returned only third-party comparisons, and I did not check the vendors' own pages. Dext claims line-item extraction, Hubdoc reportedly reads headers only, and AutoEntry charges 2 credits for line items (https://beancount.io/blog/2026/11/13/dext-vs-hubdoc-vs-autoentry-receipt-capture-tool-small-business-guide). None of the three was shown to classify capital against revenue.
- ChatFin markets AI agents that check invoices against a capitalisation policy and suggest a GL code with a note (https://chatfin.ai/blog/capex-vs-opex-ai-agents-that-classify-spend-automatically). It is US-style and finance-team oriented, not UK SME, and it cites no HMRC manual.
- Precise statement: I found no SME-priced UK product that performs the AI judgement (line to capital or revenue, pool, reason citing the HMRC manual). Every UK tool starts after the user marks an item as an asset. Caveat: this is absence in about 12 searches, I did not check TaxCalc, Taxfiler, Digita, Caseware or Fyle/Bookkeep pages, and incumbents can add this in weeks (Dext and Xero already extract lines). Tax-adviser and PwC/RSM tools were not checked.

## Wedge
None evidenced. The only candidate is "cites HMRC manual and UK pools", which is a prompt-level feature that Dext, Xero or IRIS could copy. Sign-off liability points the wrong way, because HMRC says it is a tax question and the practice must own the answer. A classifier would only make suggestions. Score if a test passed: Competition stays about 2 to 3, Pay about 6 to 8, so the total cannot reach 70 on a benchmark alone (pipeline.md lesson 1: do not spend on the benchmark).

## Proof test design (not run, because the verdict is DROP)
- Dataset: 150 labelled lines built from HMRC BIM35430, BIM35445, BIM46915, the Capital v Revenue Toolkit and CA manual worked examples, plus tribunal facts. Label each as capital or revenue, with a pool where capital. Cost under $2 on a cheap model.
- Pass mark: at least 85 percent label accuracy, at least 90 percent on revenue lines, and a reason that cites the correct manual paragraph on at least 80 percent. Fix model, effort and a generous output cap before running.
- Weakness: worked examples are textbook cases, so a pass would show little about real messy invoices. That is a data red-flag risk for any demo.

## Recurring or one-off
Annual per client (each year-end has additions), so it could be a practice subscription. But the volume per small client is a handful of items, and the value is a few minutes of work inside a £600 to £1,800 fee. Property-transaction capital allowances are one-off.

## Open risks
- Pay evidence is absent, which was the round 19 hole.
- Liability: HMRC says the practice owns the answer.
- Incumbent speed: line-item extraction already exists in Dext and AutoEntry, and adding a capex flag is small.
- Source gaps: AccountingWEB blocked fetches, so quotes there are unverified. Practice forums such as ICAEW and ATT were not mined.
- If revisited, the only route is a buyer saying the work costs hours (the round 19 recommendation). Not worth further desk time.

## Injection note
No instructions embedded in fetched pages were observed.
