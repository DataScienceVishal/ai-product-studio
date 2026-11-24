# NEXT (T-56 proof test)

Done (slice 1): kill test written and committed on main (state/ideas/pepr-packaging-data-pipeline.md, "Proof test (T-56)"); benchmark README and truth schema in `benchmark/`.

Done (slice 2): `benchmark/generate.py` (seed 20261124; tuning seed 20261125), data in `benchmark/data/` (30 sheets, 5 tuning S901-S905, manifest.json; 2.4 MB, committed). Tests: `/usr/bin/python3 -m pytest benchmark/tests` (10 pass). Deps pinned in `benchmark/requirements.txt`. Regenerate: `python3 benchmark/generate.py`. Notes: 5 scanned sheets are image-only (no text layer); truth quotes are checked against PDF text only for the 25 text sheets. Feature keys appear in truth only when stated or explicitly missing.

Left:
- Optional: public spec PDFs (licence checked) under `benchmark/public/`.
- **Slice 3:** extractor built on `products/_starter` patterns: Azure OpenAI Responses API, provider interface, token budget guard (3M token cap), timeouts and retries, page-referenced output.
- **Slice 4:** run once on the 30 sheets, score with `score.py`, write results into the idea file, and have the validator re-score (pass) or record the failed G1 attempt (fail).

Verify: `python3 -c "import json;json.load(open('benchmark/truth.schema.json'))"`; each truth file validates against the schema.
