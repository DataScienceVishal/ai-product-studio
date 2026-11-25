# T-80 benchmark report: dev set

10 invoices, 14 pages. Bars are from KILL-TEST.md; the verdict below is meaningful only on a complete TEST run.

| Metric | Value |
|---|---|
| Line accuracy, overall | 68.1% (92 correct of 135 lines + 0 hallucinated) |
| Line accuracy, clean | 91.2% (5 invoices) |
| Line accuracy, distorted | 44.8% (5 invoices) |
| Line accuracy, held-out layouts | n/a (0 invoices) |
| Line accuracy, dev layouts | 68.1% (10 invoices) |
| Line accuracy, credit notes | 45.5% (2 invoices) |
| Line accuracy, multi-page | 85.5% (4 invoices) |
| Reconciliation rate | 70.0% |
| Silent-error invoices (wrong lines, totals pass) | 5 ['DEV-005', 'DEV-007', 'DEV-008', 'DEV-009', 'DEV-010'] |
| Failure rate (failed after retry + never run) | 0.0% (0 failed, 0 not run) |
| Cost per page | $0.0041 (total $0.0576) |
| p95 latency per page | 27.24 s |
| Pages that needed the 32k retry | 0 |
| Tokens | 27690 in, 25326 out |

## Per layout

| Layout | Invoices | Accuracy |
|---|---|---|
| broadliner_a | 4 | 75.0% |
| butcher | 3 | 82.9% |
| cashcarry | 3 | 50.0% |

## Wrong-line causes

line_total: 12, pack: 29, qty: 22, unit_price: 11, vat_rate: 6

## By distortion type (information only)

| Parameter | More severe half | Milder half |
|---|---|---|
| rotation_deg | 22.7% | 55.6% |
| blur_sigma | 8.0% | 66.7% |
| jpeg_quality | 22.7% | 55.6% |
| shadow_strength | 55.6% | 37.5% |
| crumple_amp_px | 71.9% | 20.0% |
| perspective_jitter | 71.9% | 20.0% |

## Verdict against the fixed bars

**KILL** (kill triggers: overall < 88%, distorted < 80%, held-out < 80%, silent errors >= 3)

- FAIL: overall >= 95%
- FAIL: distorted >= 90%
- FAIL: held-out >= 90%
- FAIL: reconciliation >= 90%
- FAIL: silent errors <= 1
- ok: cost <= $0.02/page
- ok: p95 latency <= 90 s
- ok: failure rate <= 2%

## Invoices with errors

- DEV-002 (broadliner_a): 5 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('NAPKIN 2PLY WHT 2000', ['vat_rate']), ('MILK SEMI SKIM 6X2L', ['qty', 'line_total', 'vat_rate']), ('BIN LINER HD BLK 200S', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('BLK PEPPER GRND 500G', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate'])]
- DEV-004 (broadliner_a): 8 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('EGGS MED FR RANGE 180', ['qty', 'pack', 'unit_price', 'line_total']), ('CHICKEN BREAST FIL SKLS 2.5KG', ['pack', 'unit_price', 'line_total']), ('MILK SEMI SKIM 6X2L', ['qty', 'pack', 'unit_price', 'line_total']), ('CLNG FLUID MULTI SURF 5L', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-005 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHIPS 2.5KG X4', ['pack'])]
- DEV-006 (cashcarry): 12 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('CHEDDAR MATURE 5KG', ['qty']), ('CHKN WHOLE FR 1.8KG', ['qty']), ('SOFT DRINK LEMON 24X330ML', ['qty']), ('LPG CYLINDER 13KG', ['qty'])]
- DEV-007 (cashcarry): 11 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('SUNFLWR OIL 5L', ['pack']), ('COFFEE JAR INST 750G', ['pack']), ('TOMATO PASSATA 6X700G', ['pack']), ('CHIPS 2.5KG X4', ['pack'])]
- DEV-008 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
- DEV-009 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
- DEV-010 (butcher): 4 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('BEEF MINCE 20% 5KG', ['pack']), ('BUTCHERS STRING 500G', ['pack']), ('BLACK PUDDING 1KG', ['pack']), ('BACON SMKD BACK 2KG', ['pack'])]
