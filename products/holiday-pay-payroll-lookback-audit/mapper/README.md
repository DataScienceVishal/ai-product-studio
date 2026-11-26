# Mapper (kill-test Part B)

AI maps payroll pay-element names to nine holiday-pay categories: basic, regular_overtime, commission,
bonus_non_regular, allowance, expense_excluded, holiday_pay_paid, statutory_excluded, deduction_excluded.
Stdlib only. The prompt (`prompt.py`, version and sha256 recorded in every run) was written without seeing any labels.

## Run Part B (needs spend approval, Q-16)

From `products/holiday-pay-payroll-lookback-audit`, with the gold CSV checked out from the frozen labels branch.
Set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` (default `gpt-5-mini`) and `AZURE_OPENAI_API_KEY`
(a placeholder in cloud runs; the proxy injects the real key). Optional `AZURE_OPENAI_API=chat|responses` (auto: Responses when the endpoint ends in `/openai/v1/responses`).

```
python3 -m mapper.extract_names --in GOLD.csv --out names.csv
python3 -m mapper.run --names names.csv --out results/
python3 -m mapper.score --gold GOLD.csv --pred results/predictions.csv --run results/run.json \
  --expect-sha 6323f7fbfad3c358223840452c08e973a0b41fa431a68d98f936a27d17c7669d --out results/RESULTS.md
git add results && git commit -m "holiday-pay: kill-test part B results" && git push
```

Note: `python3 -I -m mapper.run` cannot work (`-I` removes the current directory from the module path). Use
`python3 -m mapper.run` as above, or `python3 -I mapper/run.py ...` (each script adds the product folder itself).

`python3 -m mapper.run --names names.csv --out /tmp/try --fake` checks the plumbing with the keyword baseline and no
network; it writes only to `<out>/fake/`. Fake results are not kill-test evidence.

## Pre-registered settings (fixed before any label was seen)

Structured output on both APIs (JSON schema, strict, wrapper `{"mappings":[{"id","category"}]}`, category an enum of the
nine); reasoning effort `low`; no temperature; replies are never repaired (no fence stripping). B1 is judged on
nine-category accuracy; eight-category is reported alongside. Gold header: `id,pay_element_name,source_style,gold_category,note`,
ambiguous rows noted with the exact prefix `AMBIGUOUS:`. The scorer refuses unknown gold categories, duplicate ids and
prediction ids that are not the gold ids.

## No-retry rule

One live run. Once any reply has been received (even an invalid one) the results folder is locked: `run.started`,
`predictions.csv` and `run.json` (with tokens, finish reasons, settings) exist and a second live run is refused.
A bad reply is never repaired, re-asked or re-prompted: invalid or missing items become `UNMAPPED` and count as wrong.

If the API gives NO answer at all (HTTP 400/5xx, network failure, unreadable body) nothing is scored and the shot is
not used: the run exits 4, writes no predictions or run.json, logs the attempt in `results/attempts.jsonl` and removes
`run.started`. Fix the cause (endpoint, deployment, `AZURE_OPENAI_API`) and re-run with the IDENTICAL prompt; a re-run is
refused if any logged attempt used a different prompt sha. The client's own retry is the same request after a network error, 429 or 5xx.
Cost uses gpt-5-mini at $0.25 in / $2.00 out per million tokens (state/BUDGET.md). Worst case per attempt is about $0.10.
