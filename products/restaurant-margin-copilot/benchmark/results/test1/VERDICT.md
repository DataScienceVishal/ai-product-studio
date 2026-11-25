# T-80 TEST run: validator verdict

**Verdict: KILL** (validator, 2026-11-25). The bars are in `products/restaurant-margin-copilot/KILL-TEST.md` (main, e371acf), fixed before the run.

The results, extractions and scorer live on branch `p/restaurant-margin-copilot/T-80` at commit **18d1470** (`products/restaurant-margin-copilot/benchmark/results/test1/`: `score.json`, `REPORT.md`, `TEST-*_p*.json`). Only this note is on main.

## Numbers, recomputed from score.json

| Metric | Result | KILL line | Fired |
|---|---|---|---|
| Overall line accuracy | 82.6% = 571 / (684 + 7) | <88% | yes |
| Distorted (30 invoices) | 72.1% = 300 / 416 | <80% | yes |
| Held-out layouts (25) | 84.2% | <80% | no (fails PASS ≥90%) |
| Silent-error invoices | 5 | ≥3 | yes |
| Cost per page | $0.0101 ($0.667 / 66 pages) | >$0.05 | no |
| Failure rate | 0% | >5% | no |
| Reconciliation | 64% | (PASS ≥90%) | fails PASS |
| p95 latency | 82.9 s | (PASS ≤90 s) | passes |

Clean renders scored 98.5% and credit notes 97.9%.

## Scorer check

Wrong lines were spot-checked against `data/test` ground truth:
- **TEST-007**: the numbers are shifted one row. CREAM DBL 6X1L was given Mayo's 6 x 9.73 = 58.38; the truth is 1 x 15.41. This is a real model error.
- **TEST-019**: qty, price and total are 0 on all 10 lines, while the header totals were read correctly. This is a real model error.
- **TEST-004, 033 and 034**: these are pack-only errors on ambiguous description text. "DUCK BREAST X2 400G" was read as 2x400g (truth 400g), "PORK SAUS 8S 454G" as 8x454g (truth 454g), and the pack was left blank for "BIN LINERS 200S" and "TISSUE CENTREFEED 6RL" (truth 200 and 6). The scorer applied rule (c) as written.

No scorer bug was found. Credit-note signs and pack parsing behave correctly.

**Caveat:** there are 11 pack-only wrong lines, and they make up 4 of the 5 silent-error invoices. If every one of them counted as correct, overall would be 84.2% and distorted at most 74.8%. Both are still below their KILL lines, so the verdict does not depend on the ambiguity. The silent-error trigger on its own is not robust.

## Consequence

This is the second failed G1 attempt, so the idea is killed. The reason, the lessons and what would revive it are in the idea file (`state/ideas/killed/restaurant-margin-copilot.md` after the move).
