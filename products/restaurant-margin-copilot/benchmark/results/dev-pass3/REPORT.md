# T-80 benchmark report: dev set

10 invoices, 14 pages. Bars are from KILL-TEST.md; the verdict below is meaningful only on a complete TEST run.

| Metric | Value |
|---|---|
| Line accuracy, overall | 86.0% (117 correct of 135 lines + 1 hallucinated) |
| Line accuracy, clean | 97.1% (5 invoices) |
| Line accuracy, distorted | 75.0% (5 invoices) |
| Line accuracy, held-out layouts | n/a (0 invoices) |
| Line accuracy, dev layouts | 86.0% (10 invoices) |
| Line accuracy, credit notes | 95.5% (2 invoices) |
| Line accuracy, multi-page | 85.5% (4 invoices) |
| Reconciliation rate | 80.0% |
| Silent-error invoices (wrong lines, totals pass) | 5 ['DEV-005', 'DEV-006', 'DEV-007', 'DEV-008', 'DEV-009'] |
| Failure rate (failed after retry + never run) | 0.0% (0 failed, 0 not run) |
| Cost per page | $0.0091 (total $0.1276) |
| p95 latency per page | 91.35 s |
| Pages that needed the 32k retry | 0 |
| Tokens | 33696 in, 59608 out |

## Per layout

| Layout | Invoices | Accuracy |
|---|---|---|
| broadliner_a | 4 | 73.6% |
| butcher | 3 | 94.3% |
| cashcarry | 3 | 93.8% |

## Wrong-line causes

description: 1, line_total: 11, pack: 15, qty: 8, unit_price: 11, vat_rate: 3

## By distortion type (information only)

| Parameter | More severe half | Milder half |
|---|---|---|
| rotation_deg | 69.6% | 77.8% |
| blur_sigma | 92.0% | 65.1% |
| jpeg_quality | 69.6% | 77.8% |
| shadow_strength | 92.6% | 63.4% |
| crumple_amp_px | 71.9% | 77.8% |
| perspective_jitter | 71.9% | 77.8% |

## Verdict against the fixed bars

**KILL** (kill triggers: overall < 88%, distorted < 80%, held-out < 80%, silent errors >= 3)

- FAIL: overall >= 95%
- FAIL: distorted >= 90%
- FAIL: held-out >= 90%
- FAIL: reconciliation >= 90%
- FAIL: silent errors <= 1
- ok: cost <= $0.02/page
- FAIL: p95 latency <= 90 s
- ok: failure rate <= 2%

## Invoices with errors

- DEV-002 (broadliner_a): 6 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['MILK SEMI SKIM (line printed)']; [('NAPKIN 2PLY WHT 2000', ['vat_rate']), ('MILK SEMI SKIM 6X2L', ['pack', 'unit_price', 'line_total']), ('BIN LINER HD BLK 200S', ['pack', 'unit_price', 'line_total', 'vat_rate']), ('BLK PEPPER GRND 500G', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-004 (broadliner_a): 8 wrong, reconciled=False, silent=False, failed pages []; missing ['PASTA PENNE DRY 3KG']; extra []; [('EGGS MED FR RANGE 180', ['qty', 'pack', 'unit_price', 'line_total']), ('CHICKEN BREAST FIL SKLS 2.5KG', ['pack', 'unit_price', 'line_total']), ('MILK SEMI SKIM 6X2L', ['qty', 'pack', 'unit_price', 'line_total']), ('CLNG FLUID MULTI SURF 5L', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-005 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHIPS 2.5KG X4', ['pack'])]
- DEV-006 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('POTATO BAKING LOOSE', ['description'])]
- DEV-007 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHIPS 2.5KG X4', ['pack'])]
- DEV-008 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
- DEV-009 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
