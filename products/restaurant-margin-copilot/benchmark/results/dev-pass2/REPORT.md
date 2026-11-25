# T-80 benchmark report: dev set

10 invoices, 14 pages. Bars are from KILL-TEST.md; the verdict below is meaningful only on a complete TEST run.

| Metric | Value |
|---|---|
| Line accuracy, overall | 66.2% (90 correct of 135 lines + 1 hallucinated) |
| Line accuracy, clean | 94.1% (5 invoices) |
| Line accuracy, distorted | 38.2% (5 invoices) |
| Line accuracy, held-out layouts | n/a (0 invoices) |
| Line accuracy, dev layouts | 66.2% (10 invoices) |
| Line accuracy, credit notes | 45.5% (2 invoices) |
| Line accuracy, multi-page | 61.4% (4 invoices) |
| Reconciliation rate | 70.0% |
| Silent-error invoices (wrong lines, totals pass) | 4 ['DEV-005', 'DEV-006', 'DEV-007', 'DEV-008'] |
| Failure rate (failed after retry + never run) | 0.0% (0 failed, 0 not run) |
| Cost per page | $0.0046 (total $0.0640) |
| p95 latency per page | 29.45 s |
| Pages that needed the 32k retry | 0 |
| Tokens | 33402 in, 27811 out |

## Per layout

| Layout | Invoices | Accuracy |
|---|---|---|
| broadliner_a | 4 | 69.8% |
| butcher | 3 | 60.0% |
| cashcarry | 3 | 66.7% |

## Wrong-line causes

line_total: 21, pack: 28, qty: 32, unit_price: 21, vat_rate: 15

## By distortion type (information only)

| Parameter | More severe half | Milder half |
|---|---|---|
| rotation_deg | 22.7% | 45.7% |
| blur_sigma | 48.0% | 32.6% |
| jpeg_quality | 22.7% | 45.7% |
| shadow_strength | 48.1% | 31.7% |
| crumple_amp_px | 27.3% | 48.6% |
| perspective_jitter | 27.3% | 48.6% |

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

- DEV-002 (broadliner_a): 5 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('FLOUR PLAIN WHT 16KG', ['vat_rate']), ('NAPKIN 2PLY WHT 2000', ['vat_rate']), ('MILK SEMI SKIM 6X2L', ['vat_rate']), ('BLK PEPPER GRND 500G', ['qty'])]
- DEV-004 (broadliner_a): 11 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['STOCK BEEF PASTE 6X1KG']; [('EGGS MED FR RANGE 180', ['qty', 'pack', 'unit_price', 'line_total']), ('CHICKEN BREAST FIL SKLS 2.5KG', ['pack', 'unit_price', 'line_total']), ('MILK SEMI SKIM 6X2L', ['qty', 'pack', 'unit_price', 'line_total']), ('CLNG FLUID MULTI SURF 5L', ['qty', 'pack', 'unit_price', 'line_total'])]
- DEV-005 (cashcarry): 3 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('BIN BAGS BLACK ROLL 100', ['pack']), ('CHIPS 2.5KG X4', ['pack']), ('BIN LINERS 200S', ['pack'])]
- DEV-006 (cashcarry): 12 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHEDDAR MATURE 5KG', ['qty']), ('CHKN WHOLE FR 1.8KG', ['qty']), ('SOFT DRINK LEMON 24X330ML', ['qty']), ('LPG CYLINDER 13KG', ['qty'])]
- DEV-007 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('CHIPS 2.5KG X4', ['pack'])]
- DEV-008 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
- DEV-009 (butcher): 13 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('PORK SAUSAGE DOZEN', ['pack', 'vat_rate']), ('CHICKEN THIGH BONE IN 10KG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('SIRLOIN 28D HUNG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('CHICKEN WHOLE FR 1.8KG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate'])]
