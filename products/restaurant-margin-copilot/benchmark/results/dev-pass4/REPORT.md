# T-80 benchmark report: dev set

10 invoices, 14 pages. Bars are from KILL-TEST.md; the verdict below is meaningful only on a complete TEST run.

| Metric | Value |
|---|---|
| Line accuracy, overall | 77.9% (106 correct of 135 lines + 1 hallucinated) |
| Line accuracy, clean | 97.1% (5 invoices) |
| Line accuracy, distorted | 58.8% (5 invoices) |
| Line accuracy, held-out layouts | n/a (0 invoices) |
| Line accuracy, dev layouts | 77.9% (10 invoices) |
| Line accuracy, credit notes | 45.5% (2 invoices) |
| Line accuracy, multi-page | 81.2% (4 invoices) |
| Reconciliation rate | 70.0% |
| Silent-error invoices (wrong lines, totals pass) | 4 ['DEV-005', 'DEV-006', 'DEV-007', 'DEV-008'] |
| Failure rate (failed after retry + never run) | 0.0% (0 failed, 0 not run) |
| Cost per page | $0.0046 (total $0.0643) |
| p95 latency per page | 20.11 s |
| Pages that needed the 32k retry | 0 |
| Tokens | 33696 in, 27963 out |

## Per layout

| Layout | Invoices | Accuracy |
|---|---|---|
| broadliner_a | 4 | 77.4% |
| butcher | 3 | 88.6% |
| cashcarry | 3 | 70.8% |

## Wrong-line causes

line_total: 9, pack: 15, qty: 19, unit_price: 10, vat_rate: 3

## By distortion type (information only)

| Parameter | More severe half | Milder half |
|---|---|---|
| rotation_deg | 34.8% | 71.1% |
| blur_sigma | 48.0% | 65.1% |
| jpeg_quality | 34.8% | 71.1% |
| shadow_strength | 85.2% | 41.5% |
| crumple_amp_px | 62.5% | 55.6% |
| perspective_jitter | 62.5% | 55.6% |

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

- DEV-002 (broadliner_a): 3 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['BLK PEPPER GRND 500G']; [('MILK SEMI SKIM 6X2L', ['pack', 'unit_price']), ('CHICKEN BREAST FIL SKLS 2.5KG', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-004 (broadliner_a): 9 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('CREAM DBL 6X1L', ['vat_rate']), ('EGGS MED FR RANGE 180', ['qty', 'pack', 'unit_price', 'line_total']), ('CHICKEN BREAST FIL SKLS 2.5KG', ['pack', 'unit_price', 'line_total']), ('MILK SEMI SKIM 6X2L', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-005 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHIPS 2.5KG X4', ['pack'])]
- DEV-006 (cashcarry): 12 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHEDDAR MATURE 5KG', ['qty']), ('CHKN WHOLE FR 1.8KG', ['qty']), ('SOFT DRINK LEMON 24X330ML', ['qty']), ('LPG CYLINDER 13KG', ['qty'])]
- DEV-007 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHIPS 2.5KG X4', ['pack'])]
- DEV-008 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
- DEV-009 (butcher): 3 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('PORK SAUSAGE DOZEN', ['pack']), ('BUTCHERS STRING 500G', ['vat_rate']), ('DUCK BREAST X2 400G', ['pack'])]
