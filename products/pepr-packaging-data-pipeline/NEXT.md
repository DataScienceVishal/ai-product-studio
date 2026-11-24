# NEXT (T-56 proof test)

Done (slice 1): kill test written and committed on main (state/ideas/pepr-packaging-data-pipeline.md, "Proof test (T-56)"); benchmark README and truth schema in `benchmark/`.

Left:
- **Slice 2:** generate the 30 synthetic sheets plus 5 tuning sheets as PDF via a script (`benchmark/gen/`, deterministic seed, scanned-look rasterisation), with truth files validated against `benchmark/truth.schema.json`. Optionally add public spec PDFs (licence checked) under `benchmark/public/`.
- **Slice 3:** extractor built on `products/_starter` patterns: Azure OpenAI Responses API, provider interface, token budget guard (3M token cap), timeouts and retries, page-referenced output.
- **Slice 4:** run once on the 30 sheets, score with `score.py`, write results into the idea file, and have the validator re-score (pass) or record the failed G1 attempt (fail).

Verify: `python3 -c "import json;json.load(open('benchmark/truth.schema.json'))"`; each truth file validates against the schema.
