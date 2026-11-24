# MTD quarterly prep: extraction and categorisation benchmark (T-12)

Synthetic data only. Model: the pro deployment (gpt-5.4-pro per pilot.json), v1 Responses API. Full-run numbers are in `results/full.json` (per-document detail in `results/full_report.md`, regenerate with `python3 report.py`). The pilot write-up is kept unchanged below.

## Headline: does review time halve?

**No, not with the model alone. Yes only under a calibration layer whose benefit is inflated by the synthetic data and is not evidence for real clients.**

| Format (docs, lines) | Model only, pilot time formula | Model only, silent errors charged (120 s each) | With merchant memory + risky-category review (silent charged) |
|---|---|---|---|
| Clean bank PDF, 4 layouts (5 docs, 160) | 63.8% | 72.8% | 32.0% |
| CSV export (3 docs, 96) | 61.0% | 66.0% | 28.7% |
| Owner spreadsheet / xlsx (3 docs, 96) | 57.1% | 67.1% | 37.7% |
| Scan image (1 doc, 32; see caveat) | 39.0% | 99.0% | 65.1% |
| Phone photo | not run (HTTP 502) | not run | not run |
| All 12 scored docs (384 lines) | 59.3% | 71.8% | 35.4% |

Values are assisted time as a share of manual time (50% or below means it halved). Pooled over documents.

How to read it:
- Pilot formula (comparable to the pilot, 51 to 56% there): 57 to 64% on the text formats. Worse than the pilot because the personas have ambiguous lines (mixed personal/business, home office, cash) that the model rightly marks low confidence, so more lines are flagged. Not halved.
- Charging silent errors (wrong lines at confidence 0.8 or above that nobody looks at, 120 s each, same as the T-12 pilot check): 66 to 73%. Not halved on any format. 12 of 384 lines were silent errors in the model-only run: 3.7 per 100 auto-accepted lines (the pilot had 5 per 100).
- Calibration layer (see below) takes the text formats to 29 to 38%, which would be a halving. Do not rely on this. The merchant-memory rules are learned from a reviewed "prior quarter" generated from the same short merchant list, so almost every merchant is already known. That is the synthetic data repeating itself. Real clients have a long tail of new merchants, and the rules only help on repeats. Treat 29 to 38% as a ceiling, and the 66 to 73% model-only figure as the floor.
- Truthful summary: model-only misses the halving bar; with a reviewed-history rule layer the bar is plausibly reachable for clients whose spending repeats, which needs real-data evidence. The G1 criterion "does review time halve?" is therefore **not yet proven**.

## What was run

| Item | Value |
|---|---|
| New model calls | 15 of 15 allowed (1 rejected probe, 12 completed, 2 failed with HTTP 502) |
| Documents | 14 planned, 12 completed and scored, 2 images failed (photo_consult, scan_stall) |
| Mix | 5 PDFs over 4 fictional layouts (Fenwick & Dale, Quillon Direct, Tarn Building Society, Corvid Direct), 3 CSV (2 layouts), 3 xlsx owner sheets, 3 images (1 scored) |
| Personas | tradesperson, IT consultant (home office), market-stall seller (cash); 112 truth-flagged ambiguous lines |
| Tokens (new) | 11,263 input, 36,041 output (reasoning is most of it) |
| Spend, recorded | $4.49 of $11.50 cap |
| Spend, upper bound | $7.95 if the two 502 calls were billed at their full output cap (unknown); still under the cap |
| Pilot | not re-run; its own spend is not part of the figures above |

The run stopped on the call cap (15), not the dollar cap. Two of the 15 attempts were lost to a rejected parameter and two 502s, so only 1 of 3 image documents produced a result.

Cost per document (assumed $15/M input, $120/M output, reasoning counted as output):

| Doc type | Input tokens | Output tokens | USD | Notes |
|---|---|---|---|---|
| Text docs (categorise only, 32 lines), 11 docs | 773 to 967 | 1,493 to 3,750 | 0.19 to 0.46, mean about 0.29 | extraction is free (deterministic) |
| Scan image (extract and categorise) | 1,311 | 10,343 (8,868 reasoning) | 1.26 | 261 s |
| Pilot text doc (for comparison; extract and categorise in one call) | 745 to 1,280 | 3,448 to 4,515 | about 0.43 to 0.56 | |

Per-document table: `results/full_report.md`. Time per call was 58 to 144 s for text docs and 261 s for the scan.

## Method

- Deterministic extraction, no model: `pdftotext -layout` plus one regex parser per layout, CSV parsers, `openpyxl` for sheets. Parsed dates, amounts and descriptions matched the truth on every one of the 11 non-image documents (date, amount, description accuracy 100%; verified by tests for all of them). Layouts include two-line descriptions, a signed amount with no balance, year-less dates ("9 Apr", year inferred from the tax year), trailing-minus debits, CR/DR balance suffixes and a semicolon CSV with preamble rows. Debit or credit is taken from the running-balance change where the layout has a balance.
- Model, categorise only: one call per document with numbered lines, returning `[index, category, confidence]`. Persona context is in the prompt.
- Images: the model transcribes and categorises (it is the only reader). Reasoning effort probe: `minimal` is rejected (HTTP 400, no tokens, counted as a call), `medium` is accepted. Pilot said `low` is also rejected. Image call at `medium` with a 14,000-token output cap completed with 10.3k output tokens. Text docs used the default effort (the pilot's setting) for comparability.
- Calibration (`calib.py`, no model): (1) merchant memory: rules map a normalised merchant (digits and reference tokens stripped) to the category from a reviewed prior quarter of the same persona; a rule agreeing with the model raises confidence to 0.97; a rule disagreeing overrides the category and sends the line to review; (2) lines in categories where the pilot's errors sat (repairs, car/van, other expenses, professional fees) with no rule are capped at 0.79 so they go to review; (3) confidence threshold 0.8. Rules and risky categories come from the prior quarter and the pilot, not from the scored documents, but the prior quarter shares the merchant list (see above).
- Review-time model: pilot assumptions unchanged (25 s manual per line, 4 s glance, 35 s flagged, 25 s missed line, 60 s fixed per document), plus a "silent errors charged" variant: 120 s for every wrong auto-accepted line. A silent error is a wrong category, date, amount or description at confidence 0.8 or above.

## Accuracy

| Measure | Result |
|---|---|
| Date, amount, description (text formats, deterministic) | 100% on 11 documents |
| Model category accuracy, all 12 scored docs | 95.6% (94.4% PDF, 95.8% CSV, 97.9% sheets, 93.8% the one scan) |
| Category accuracy on truth-flagged ambiguous lines | 87.5% (98 of 112) |
| Silent errors per 100 auto lines, model only | 3.7 (2.8 PDF, 1.5 CSV, 2.9 sheet, 14.3 scan) |
| Silent errors per 100 auto lines, with calibration | 0.6 (all from the scan) |
| Threshold sweep, calibrated (0.7 / 0.8 / 0.9 / 0.95) | silent errors 3 / 2 / 2 / 2; ratio with silent errors charged 34.0 / 35.4 / 37.0 / 37.0%. Threshold matters little once rules and the risky-category cap are on |

The scan transcription itself was good (amount and description 100%, date 93.8%, no lines missed), but 4 silent wrong categories at confidence 0.8 or above on one document make the model-only scan cost 99% of manual time.

## Caveats

- Synthetic, self-generated data: a short repeating merchant list, clean fictional layouts, and truth labels we chose for ambiguous lines (a labelling choice, not tax advice). No real bank formats, branding or client data. The model's 95.6% category accuracy and the calibration results do not transfer to real statements.
- Image evidence is thin: 1 scan scored; the phone photo and the second scan failed with HTTP 502 and the call cap blocked retries. No claim about phone photos. Do not read "scan 65%" as a result.
- Repeats: one call per document, so no error bars. A single wrong line moves a document by about 3 points. Per-format figures rest on 3 to 5 documents.
- Calibration is circular on this data (above). Its true value for real clients is unknown.
- Review seconds are assumptions, not measured with people. The 120 s silent-error cost is a guess; at 60 s the model-only text formats would be 62 to 68% (still not halved).
- The 502 calls were recorded at $0. If they were billed, spend is at most $7.95.
- No comparison with Dext or a PDF converter (needs an account; ask Vishal first).
- QA additions (see QA-FULL.md): (a) merchant coverage of the rules is 92.7% of scored lines (356 of 384) because every document contains each merchant of its persona once; re-running the calibrated scoring with only a random half of the rules gives 54.4% (not halved), a quarter 64.1%, none 72.9%. So the 35.4% needs about 80% or more of spend to be at known merchants. (b) 20 of the 37 merchant keys in the full run also appear in the pilot merchant list, so the full run is not independent of the pilot; but the risky-category cap adds nothing (no rules, cap on: 72.9%; no rules, no cap: 71.8%), so the pilot-derived `RISKY_CATS` is not what produces the 35.4%. (c) 112 of 384 lines (29%) are truth-flagged ambiguous with our own labels; model category accuracy is 98.9% on the 272 non-ambiguous lines against 87.5% on the ambiguous ones. (d) Silent-error cost sensitivity, model only, 12 docs pooled: 60 s 65.6%, 120 s 71.8%, 240 s 84.3%; calibrated 34.1 / 35.4 / 37.9%. Model-only misses the halving bar at every cost tried, including 0 s (59.3%).

---

# Pilot results (unchanged)


Model: Azure OpenAI deployment `gpt-5.4-pro`, one call per document, `max_output_tokens` 8000. Documents are synthetic (fictional "Northbank", fictional merchants, 32 lines each). Run once, no retries. Raw data: `results/pilot.json`.

## Metrics (confidence threshold 0.8)

| Doc type | Date | Amount | Description | Balance | Category | Routed to review | Category acc, auto-accepted lines | Confident-but-wrong lines |
|---|---|---|---|---|---|---|---|---|
| Clean text PDF | 100% | 100% | 100% | 100% | 93.8% | 25.0% | 95.8% (23/24) | 1 |
| Degraded scan | 0% | 0% | 0% | n/a | 0% | 100% | n/a | 0 |
| Phone photo | 0% | 0% | 0% | n/a | 0% | 100% | n/a | 0 |
| CSV export | 100% | 100% | 100% | 100% | 93.8% | 21.9% | 92.0% (23/25) | 2 |
| Messy spreadsheet | 93.8% | 93.8% | 93.8% | n/a | 84.4% | 28.1% | 95.7% (22/23) | 1 |

Scan and photo scored zero because the model ran out of output budget, not because it could not read them (see below). Treat those two rows as "failed run", not as a measure of image accuracy.

## Tokens and latency

| Doc type | Input | Output | of which reasoning | Latency | Status |
|---|---|---|---|---|---|
| Clean PDF (text extracted) | 1,280 | 4,515 | 3,045 | 124 s | completed |
| Degraded scan (image) | 1,294 | 8,000 | 7,033 | 72 s | cut off at limit |
| Phone photo (image) | 1,265 | 8,000 | 8,000 | 70 s | cut off, no answer text at all |
| CSV export | 1,125 | 3,656 | 2,169 | 87 s | completed |
| Messy spreadsheet | 745 | 3,448 | 2,262 | 148 s | completed |
| Total | 5,709 | 27,619 | 22,509 | 501 s | |

Reasoning is about 81% of output tokens. The API rejected `reasoning: {effort: "low"}` with a 400 on every document, so the runs used the model's default effort (the rejected requests produced no tokens).

## Does review time halve?

Short answer: borderline on clean inputs, no on images (this pilot).

Assumptions (editable in `score.py`): manual baseline 25 s per line; an auto-accepted line costs a 4 s glance; a flagged line (confidence below 0.8) costs 35 s; a missed line costs 25 s by hand; 60 s fixed per document. These are guesses, not measured.

| Doc type | Assisted vs manual time |
|---|---|
| Clean PDF | 54.5% |
| CSV export | 50.6% |
| Messy spreadsheet | 55.9% |
| Scan, photo | 107.5% (run failed, so the user pays the fixed cost and does everything by hand) |

On the three runs that worked, assisted review takes roughly half the manual time, a little above 50% under these assumptions. The result moves easily with the glance and flagged-line costs, and it ignores the risk below.

## What this shows

- Extraction from clean text and CSV is mechanically solved: every date, amount, description and balance matched.
- Category accuracy is about 84 to 94%. The misses were plausible (tyres as car/van instead of repairs, a trade subscription as professional fees, two sheet lines that were fine on category but whose amount sign the model flipped, see below).
- Messy sheet: the 2 lines at 93.8% date/amount/description are "moved to savings" rows whose sheet amount is positive while the bank text says "TRANSFER FROM SAVINGS". The model returned them negative (both at confidence 0.58, so flagged). The scorer counts them as missed lines, not category errors. The sheet's own signs are inconsistent, so this is a defensible miss.
- Confidence is only weakly useful: 4 lines were wrong at confidence 0.8 or above and went into the auto-accepted pile. These errors are invisible to a reviewer who only checks flagged lines. Any real product needs a sampling check or a rule for this.

## Caveats

- Synthetic data, generated by us, with a handful of merchant patterns that repeat. It proves the mechanics, not real-world accuracy. Real bank layouts, odd merchants and real owner spreadsheets will be harder.
- One run per document, one document per type: no error bars. A single category slip moves the figures by 3 points.
- Image failures: the model spent its whole 8,000-token budget on reasoning. My runner then discarded the partial text (the scan reply was cut off mid-JSON). I fixed the runner to keep it, but the pilot rule was one call per document, so the images were not re-run. We do not know the image accuracy.
- Review-time seconds are assumptions. No person timed anything.
- Only one fictional layout. The idea file asks for five bank layouts; that is for the full benchmark.
- Cost in pounds is not computed: no price list was provided.
