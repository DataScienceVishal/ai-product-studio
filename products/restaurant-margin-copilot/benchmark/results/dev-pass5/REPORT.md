# T-80 benchmark report: dev set

10 invoices, 14 pages. Bars are from KILL-TEST.md; the verdict below is meaningful only on a complete TEST run.

| Metric | Value |
|---|---|
| Line accuracy, overall | 86.9% (119 correct of 135 lines + 2 hallucinated) |
| Line accuracy, clean | 98.5% (5 invoices) |
| Line accuracy, distorted | 75.4% (5 invoices) |
| Line accuracy, held-out layouts | n/a (0 invoices) |
| Line accuracy, dev layouts | 86.9% (10 invoices) |
| Line accuracy, credit notes | 100.0% (2 invoices) |
| Line accuracy, multi-page | 88.4% (4 invoices) |
| Reconciliation rate | 80.0% |
| Silent-error invoices (wrong lines, totals pass) | 1 ['DEV-008'] |
| Failure rate (failed after retry + never run) | 0.0% (0 failed, 0 not run) |
| Cost per page | $0.0090 (total $0.1258) |
| p95 latency per page | 133.73 s |
| Pages that needed the 32k retry | 0 |
| Tokens | 34564 in, 58574 out |

## Per layout

| Layout | Invoices | Accuracy |
|---|---|---|
| broadliner_a | 4 | 68.5% |
| butcher | 3 | 97.1% |
| cashcarry | 3 | 100.0% |

## Wrong-line causes

line_total: 9, pack: 10, qty: 7, unit_price: 9, vat_rate: 5

## By distortion type (information only)

| Parameter | More severe half | Milder half |
|---|---|---|
| rotation_deg | 62.5% | 82.2% |
| blur_sigma | 100.0% | 61.4% |
| jpeg_quality | 62.5% | 82.2% |
| shadow_strength | 100.0% | 59.5% |
| crumple_amp_px | 75.0% | 75.7% |
| perspective_jitter | 75.0% | 75.7% |

## Verdict against the fixed bars

**KILL** (kill triggers: overall < 88%, distorted < 80%, held-out < 80%)

- FAIL: overall >= 95%
- FAIL: distorted >= 90%
- FAIL: held-out >= 90%
- FAIL: reconciliation >= 90%
- ok: silent errors <= 1
- ok: cost <= $0.02/page
- FAIL: p95 latency <= 90 s
- ok: failure rate <= 2%

## Invoices with errors

- DEV-002 (broadliner_a): 9 wrong, reconciled=False, silent=False, failed pages []; missing ['CHICKEN BREAST FIL SKLS 2.5KG', 'PASTA PENNE DRY 3KG']; extra ['MILK SEMI SKIM 6X2L', 'BIN LINER HD BLK 200S']; [('FLOUR PLAIN WHT 16KG', ['vat_rate']), ('NAPKIN 2PLY WHT 2000', ['vat_rate']), ('MILK SEMI SKIM 6X2L', ['vat_rate']), ('BIN LINER HD BLK 200S', ['vat_rate'])]
- DEV-004 (broadliner_a): 8 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('EGGS MED FR RANGE 180', ['qty', 'pack', 'unit_price', 'line_total']), ('CHICKEN BREAST FIL SKLS 2.5KG', ['pack', 'unit_price', 'line_total']), ('MILK SEMI SKIM 6X2L', ['qty', 'pack', 'unit_price', 'line_total']), ('CLNG FLUID MULTI SURF 5L', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-008 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
