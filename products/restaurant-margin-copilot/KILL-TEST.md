# Kill test: restaurant-margin-copilot synthetic-invoice benchmark (T-80)

Written by the validator on 2026-11-25, before any invoice is generated or any model is called (Q-13 B; `playbooks/pipeline.md`, proof-test route). Copy it, or link it, into the idea file and commit it before the test set exists. After that, **no bar, metric or rule below may change.** Any amendment is dated, gives its reason, is kept in the idea file, and applies only to a later run.

## 1. Benchmark design

**Layouts.** Six fictional UK supplier layouts, imitating structure only, with no real branding: broadliner A, broadliner B, cash and carry, butcher, greengrocer, dairy/drinks wholesaler.
- Dev layouts: three (broadliner A, cash and carry, butcher).
- Held-out layouts: the other three. Their generator code is written only **after** the prompt is frozen (SPEC §6).

**Sets.** Both are made with a fixed seed. The generator, seed and SHA-256 manifest are committed before tuning starts.

| Set | Invoices | Layouts | Use |
|---|---|---|---|
| Dev | 10 (seed 1001) | dev layouts only | prompt and config work, scorer debugging |
| Test | 50 (seed 2025) | 25 on dev layouts, 25 on held-out layouts | scored **once** |

**Required test-set mix.** Counts are invoices, and an invoice can count in more than one row.
- Rendering: 20 clean (PDF rendered to an image at 200 dpi) and 30 distorted phone-photo images.
- Distortions: each distorted image gets a seeded mix of rotation 2 to 12°, perspective skew, Gaussian blur (sigma 0.5 to 1.5), a shadow gradient, JPEG quality 35 to 70 and a crumple mesh warp. The parameters are logged per image.
- At least 8 credit notes, with negative quantities or totals and a "CREDIT NOTE" header.
- At least 10 multi-page invoices (2 to 3 pages, totals on the last page).
- Every broadliner and cash-and-carry invoice mixes VAT rates: 0% for food, 20% for drinks, cleaning and disposables, and 5% where it plausibly applies.
- Pack text in many forms: "12x1L", "5kg case", "6 x 2.5kg", "each", "per kg" (catch weight), "dozen", "24x330ml".
- Size: about 10 to 25 lines per invoice, so roughly 70 pages and 750 lines.

**Ground truth per line:** description as printed, qty, pack size (count x size x unit), billing unit, unit price, line total and VAT rate. Per invoice: net total, VAT by rate and gross total. The generator checks that its own totals add up before it writes any file.

**Run configuration.** Frozen and hashed together with the prompt before the test run.
- Model: `AZURE_OPENAI_DEPLOYMENT_MINI` (gpt-5-mini, $0.25 in / $2.00 out per 1M tokens, per BUDGET.md T-56). No larger model during this test.
- Calls: one call per page image, with strict JSON-schema output. Images are downscaled to a 2048 px long edge. Code merges the pages of an invoice; the model never adds up totals.
- Reasoning effort: chosen on the dev set from {low, medium}, then frozen.
- Output cap and failures: `max_output_tokens` is 16,000. If a call stops on length, returns invalid JSON or times out (180 s), it gets **one retry at 32,000**. If the retry also fails, the page counts as wrong: all of its ground-truth lines are counted as errors. Failed pages are never dropped (the T-56 lesson).
- Logging: input tokens, output tokens, retries and latency for every call.

**Spend.** The hard cap is **$5 in total** (dev, test and retries). It is enforced by the T-56 ledger spend guard, which stops the run at the cap (branch `p/pepr-packaging-data-pipeline/T-56`; reuse its generator pattern and scorer too).
- Expected cost: about $0.50 to $1.00, based on T-56's mini cost of about $0.0074 per sheet.
- Before starting: the test run may begin only if the dev run projects at most $2.50 for the test set.
- If the cap is hit anyway: unscored pages count as wrong.

## 2. Metrics (computed by code against ground truth)

**Matching lines.** Within each invoice, predicted lines are paired with ground-truth lines by an optimal one-to-one assignment on description similarity. Unpaired predictions are counted as hallucinated lines.

**A correct line meets all of these conditions:**
- (a) Description: normalised Levenshtein similarity of at least 0.95 after lower-casing and collapsing whitespace and punctuation. The description only feeds fuzzy matching, so small typos are tolerated.
- (b) Qty: exact, including the sign on credit notes.
- (c) Pack: cost per base unit (g, ml or each) within 0.5% of ground truth. The cost is computed by our code from the extracted unit price and the parsed pack, for example 12x1L gives 12,000 ml.
- (d) Unit price: within £0.005.
- (e) Line total: within £0.005.
- (f) VAT rate: exact.

**Formulas.**
- **Line accuracy** = correct lines / (ground-truth lines + hallucinated lines), so invented lines lower the score.
- **Reconciliation rate** = invoices where (sum of extracted net line totals + VAT by rate) equals the extracted gross total within £0.01 **and** the extracted gross total equals the ground-truth gross total, divided by all invoices.
- **Silent-error count** = invoices with at least one wrong line that still pass the reconciliation check. This is the number that matters for trust: wrong numbers the product would not flag.
- **Per-subset accuracy:** line accuracy for each of clean, distorted, held-out layouts, credit notes and multi-page. Reported per distortion type as well, for information.
- **Cost per page (USD)** = total billed USD for the test run, retries included (ledger) / test pages.
- **p95 latency** = the nearest-rank 95th percentile of per-page wall-clock time, retries included.
- **Failure rate** = pages that are still truncated or invalid after the retry / test pages.

## 3. Bars (fixed now)

**PASS: every one of these must hold.**
- Overall line accuracy **at least 95%**. This is the scout's own bar (idea file, risks) and validator item 4.
- Distorted subset **at least 90%**.
- Held-out layouts **at least 90%** (SPEC §8).
- Reconciliation **at least 90%** of invoices.
- Silent errors **at most 1 invoice (2%)**.
- Cost **at most $0.02 per page**. At about 1.5 pages per invoice, that is under £0.03 per invoice, the bottom of SPEC §5's assumed range and more than 95% margin on the £39 Starter plan.
- p95 latency **at most 90 s**.
- Failure rate **at most 2%**.

**KILL: any one of these is enough.**
- Overall line accuracy **below 88%**.
- Distorted subset **below 80%**.
- Held-out layouts **below 80%**.
- Silent errors **3 or more invoices (6%)**.
- Cost **above $0.05 per page**.
- Failure rate **above 5%**.

Why these kill lines:
- Accuracy and held-out: SPEC kill #1 already stops the build below 90% clean, and Jelly's extraction is human-checked. A cheap rival that gets more than 1 line in 8 wrong has no story to tell.
- Distorted: the 80% line is stricter than SPEC kill #2 (75%) because this is the proof test, not a tuning run.
- Silent errors: 3 or more invoices with wrong prices that the product would not flag would break trust in the product.
- Cost: above $0.05 per page the mini economics stop being clearly better than pro's.

A KILL counts as the idea's **second failed G1 attempt**, so the idea is killed (kill rules).

**INCONCLUSIVE: anything that is neither PASS nor KILL.**
- The result gives no rubric lift.
- One second chance is allowed: one prompt or config revision, made on the dev set only, followed by a fresh 50-invoice test set (seed 2026) on the same layouts, run once, inside the same $5 total.
- That second run is judged against the same bars. If it is INCONCLUSIVE again, it is treated as KILL.
- Both runs are reported; the better one cannot be picked.

**Latency** has no kill line, because extraction runs as an async job. A p95 above 90 s only blocks PASS.

## 4. What a PASS can and cannot lift (scored now, before the result)

Current score 66: Pain 13, Pay 14, AI 9, Reach 7, Build 11, Competition 3, Risk 9.

| Row | After a full PASS | Why |
|---|---|---|
| Pain, Pay, Reach, Risk | 13, 14, 7, 9 (no change) | Synthetic invoices say nothing about buyers, money or channels. |
| AI advantage | 9 → **10** | It shows a cheap model reads messy UK invoices, and the evaluation set becomes a small asset. It does not show "hard to copy in a week": Jelly, MarketMan and Dext already do this. |
| Build feasibility | 11 → **13** | It retires the largest build risk: extraction accuracy and unit cost on mini inside the Azure cap. Matching, recipes, the worker and the deploy are still unproven, so the row stays below 15. |
| Competition | **3 (no change)** | Our accuracy measured on our own invoices is not a gap against a human-checked rival. A measured gap needs the **same** synthetic invoices run through Jelly (T-81, currently blocked: no studio email) or Profito, with their mis-reads, turnaround, caps or fees logged against our numbers. A documented gap where we match or beat them at under half the price would score 5 or 6. |

- **Maximum after a full PASS: 69. Even a perfect pass cannot reach 70 on its own.**
- With a T-81 measured gap as well, Competition reaches 5 or 6, for **71 to 72**.

**Is the test still worth running?** Yes. This is a logged exception to the "score a pass first" lesson, for four reasons:
1. Vishal chose B, which includes this benchmark.
2. It costs about $1, with a hard cap of $5.
3. It is the cheapest decisive way to *kill* the idea, which saves weeks of build if extraction fails.
4. Our own accuracy figure is a prerequisite for any measured-gap evidence later. The set and the harness are reused by T-81 and by the build.

**Protecting the last attempt.**
- On PASS, the validator writes a dated re-score note (69, "attempt unspent", like the 2026-11-24 re-score). The G1 attempt itself is taken only when wedge evidence arrives: T-81, or a channel or price-sensitivity source.
- Deadline **2026-12-09**. If no wedge evidence exists by then, the G1 attempt is scored on what exists, which means 69 and KILL. The idea cannot stay parked indefinitely.

## 5. Known limits of synthetic data

- **We wrote both sides.** The generator and the prompt share our assumptions about fonts, layouts and wording, so 95% here is an upper bound on real accuracy. The held-out layouts reduce this, but do not remove it.
- **The distortions are simulated.** There is no thermal-paper fade, handwritten amendment, stamp, staple, glare, finger or second invoice in frame, and SPEC excludes handwriting. Real-photo accuracy stays unproven until a pilot, which is locked until `unlock selling`.
- **A pass shows feasibility, not product quality in a kitchen,** and says nothing about willingness to pay.

**Overfitting controls.**
1. Commit the generator, seeds and test manifest hash before tuning.
2. Write the held-out layout code after the prompt is frozen.
3. Freeze and hash the prompt and config before the test run.
4. Never use test images or results for prompt work. Only the 10-invoice dev set is used for that.
5. Run the test once. Any rerun is a full rerun, and both results are reported.
6. Unit-test the scorer on dev before the test. A scorer bug found afterwards may be fixed only if it is shown on a dev example, and both scores are reported.

**Credit notes are a Won't in SPEC §4,** but they are included here because real invoice piles contain them. If extraction cannot read them, the product has to detect and route them rather than mis-read them.
