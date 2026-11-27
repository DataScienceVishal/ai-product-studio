# EVAL: SME council tender drafting (template, T-193)

Status: TEMPLATE. No scored run has happened. Fill the fields marked `TBD` at the configuration freeze (L1), commit, and
record that commit hash below. After that, any change is a dated amendment, never a silent edit.

## Run configuration (pre-registered; SPEC section 6, DESIGN 8.1)

| Item | Value |
|---|---|
| Pre-registration commit (keys, trap set, fixture drafts, this file) | TBD |
| Model and version | gpt-5-mini (2025-08-07), Azure deployment named in `AZURE_OPENAI_DEPLOYMENT_MINI`; reported model must start `gpt-5-mini` or the run stops |
| API | Responses, strict `json_schema` |
| Effort and output cap per task | extract low / 6,000; draft low / 4,000; shorten low / 1,500; claimcheck medium / 6,000 (starting values, final after tuning: TBD) |
| Truncation rule | one retry at twice the cap (harness only), then the task fails |
| Reasoning headroom | 0 (`eval/budget.json`) |
| Prompt SHA-256 | from `python -m eval.run config` at the freeze: TBD |
| Retrieval | k=8, at most 3 passages per document, score floor TBD (`RETRIEVAL_FLOOR`, 0 until L1 tuning) |
| Chunk size and overlap | `CHUNK_PAGES` and `OVERLAP_PAGES` in `app/tender/extract.py`: TBD at freeze |
| Word-count rule | `[E-n]` markers excluded, gap markers included (DESIGN 4.5; `eval/score.py count_words`) |
| A1 and A2 matching | a question matches by `ref`, else by text similarity of at least 0.8 (difflib ratio on normalised text), one-to-one greedy; word limits, page limits, marks and weights must match exactly |
| A3 | a key mandatory item must match an extracted item that is kind mandatory or pass/fail; matched but optional counts as "shown optional" and fails the bar |
| A4 | a claim is a sentence other than a bare gap marker; it passes with at least one `[E-n]` and every `[E-n]` live in the tenant and in the draft's retrieved set |
| A5 and A6c random seed | 20261127 (`eval/sample.py A5_SEED`); 100 claims from the E2 exports, all if fewer |
| A6a | a seeded claim is caught when a checker claim on the same draft overlaps its span and is `unsupported` or `contradicted`; at least 38 of 40; misses listed by type |
| Held-out drafting pack rule | the first of each sector in `demo-data/SOURCES.md` order (3 packs) |
| Budget | one-off hard cap $6.00, gpt-5-mini only, approved by Q-19 (answered A, 2026-11-27); sub-caps tuning $2.00, scored $2.60, recording $1.40; ledger `eval/ledger.jsonl`; app caps unchanged |
| Ledger rules | worst case (estimate plus output cap) must fit the phase sub-cap and the total before each call; a call that may have been billed and left nothing is charged at worst case; scored preflight needs $2.54 free |
| Scored run | one run; an infrastructure failure resumes from the first unfinished item |
| Tuning data | the 3 demo packs and the 10-question dev trap set only; never the held-out packs |

## Results

TBD (L2). Per bar: value, bar, pass or fail, with the A6a misses by type and the model-checking-a-model caveat (SPEC section 6).

## Amendments

None.
