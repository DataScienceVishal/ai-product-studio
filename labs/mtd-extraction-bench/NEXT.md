# NEXT: scaling to the full benchmark

Status: pilot done (5 docs, generator, runner, scorer, 8 passing unit tests). Run `python3 -m pytest tests`, regenerate data with `python3 gen.py data`, re-score saved output with `python3 rescore.py`. `run_pilot.py` refuses to run again if `results/pilot.json` exists (cost guard; `--force` overrides).

## Fix first (pilot findings)
1. Images need a bigger output budget or less thinking. Both image calls hit 8,000 tokens, almost all reasoning. Options: raise `max_output_tokens` to 20,000 for images, split a page into 2 halves, or try a cheaper model for extraction and keep the pro model for categorising only. `reasoning.effort` low is rejected by this deployment; test `minimal`/`medium` values or check the deployment's accepted values first (one cheap probe).
2. Split extraction from categorisation: OCR/extract (cheap, deterministic where possible: pdftotext, CSV parse) then categorise in batches of 40 lines. The clean-text tokens suggest most spend is thinking, not reading.
3. Calibrate confidence: 4 of 80 auto-accepted lines were wrong. Add a rule layer (merchant memory) and a random 10% spot check of auto-accepted lines in the review-time model.

## Sizing from the pilot
Per 32-line document the working runs used about 1.1k input and 3.5 to 4.5k output tokens (images: at least 8k output). Planning figure: 6k output per 32 lines, 1.3k input.
- Target from the idea file: 5 bank layouts x 3 formats (clean PDF, scan, CSV) + 3 spreadsheets, about 200 lines per persona. 3 personas x ~6 docs of 32 lines x 18 doc variants is about 110 calls: roughly 130k input and 650k output tokens (about 500k of it reasoning), and about 2 hours of calls at the pilot's 100 s per call if run serially (run 4 in parallel).
- Add 20% for image reruns. Multiply by the deployment's price per million tokens (not known to me; get it before approving the run) to get the budget for Vishal.

## Build list
- Four more fictional bank layouts in `gen.py` (column orders, date formats, multi-line descriptions, running-balance variants, credit/debit suffixes). Do not copy real branding.
- Personas (tradesperson, consultant, market-stall seller) with their own merchant lists and some ambiguous lines (mixed personal/business, home-office, cash).
- 3 repeats per document for error bars; temperature is not settable on this model, so repeat for variance.
- Replace assumed seconds with a timed test: two people reviewing 50 lines manually vs assisted.
- Comparison with Dext Solo or a PDF-to-CSV converter needs an account: ask Vishal first (CLAUDE.md section 6).
- Real client data is not available; do not claim accuracy beyond the synthetic set.
