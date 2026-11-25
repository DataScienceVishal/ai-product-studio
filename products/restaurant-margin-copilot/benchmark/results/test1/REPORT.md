# T-80 benchmark report: test set

50 invoices, 66 pages. Bars are from KILL-TEST.md; the verdict below is meaningful only on a complete TEST run.

| Metric | Value |
|---|---|
| Line accuracy, overall | 82.6% (571 correct of 684 lines + 7 hallucinated) |
| Line accuracy, clean | 98.5% (20 invoices) |
| Line accuracy, distorted | 72.1% (30 invoices) |
| Line accuracy, held-out layouts | 84.2% (25 invoices) |
| Line accuracy, dev layouts | 81.2% (25 invoices) |
| Line accuracy, credit notes | 97.9% (10 invoices) |
| Line accuracy, multi-page | 85.4% (15 invoices) |
| Reconciliation rate | 64.0% |
| Silent-error invoices (wrong lines, totals pass) | 5 ['TEST-004', 'TEST-015', 'TEST-033', 'TEST-034', 'TEST-039'] |
| Failure rate (failed after retry + never run) | 0.0% (0 failed, 0 not run) |
| Cost per page | $0.0101 (total $0.6671) |
| p95 latency per page | 82.92 s |
| Pages that needed the 32k retry | 0 |
| Tokens | 155958 in, 314039 out |

## Per layout

| Layout | Invoices | Accuracy |
|---|---|---|
| broadliner_a | 9 | 71.5% |
| broadliner_b | 9 | 84.7% |
| butcher | 8 | 77.9% |
| cashcarry | 8 | 95.0% |
| dairy_drinks | 8 | 86.2% |
| greengrocer | 8 | 81.8% |

## Wrong-line causes

description: 3, line_total: 87, pack: 101, qty: 65, unit_price: 91, vat_rate: 34

## By distortion type (information only)

| Parameter | More severe half | Milder half |
|---|---|---|
| rotation_deg | 56.1% | 86.7% |
| blur_sigma | 78.5% | 64.8% |
| jpeg_quality | 65.3% | 78.5% |
| shadow_strength | 61.6% | 81.7% |
| crumple_amp_px | 65.8% | 77.6% |
| perspective_jitter | 66.5% | 77.0% |

## Verdict against the fixed bars

**KILL** (kill triggers: overall < 88%, distorted < 80%, silent errors >= 3)

- FAIL: overall >= 95%
- FAIL: distorted >= 90%
- FAIL: held-out >= 90%
- FAIL: reconciliation >= 90%
- FAIL: silent errors <= 1
- ok: cost <= $0.02/page
- ok: p95 latency <= 90 s
- ok: failure rate <= 2%

## Invoices with errors

- TEST-001 (broadliner_a): 4 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('EGGS FREE RANGE DOZEN', ['qty', 'pack', 'unit_price', 'line_total']), ('PASTA PENNE DRY 3KG', ['pack', 'unit_price', 'line_total']), ('HONEY CLEAR 3KG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('FOIL CATERING 450MMX90M', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate'])]
- TEST-002 (broadliner_b): 1 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('PEPPER WHITE GRND 1KG', ['vat_rate'])]
- TEST-004 (butcher): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack'])]
- TEST-007 (broadliner_a): 10 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['TOM CHOPPED IN JUICE 6X400G']; [('MAYO CATERING 5L', ['qty', 'pack', 'unit_price', 'line_total']), ('CREAM DBL 6X1L', ['qty', 'pack', 'unit_price', 'line_total']), ('POTATO CHIP FRZN 4X2.5KG', ['pack', 'unit_price', 'line_total']), ('OIL RAPESEED CATERING 20L', ['pack', 'unit_price', 'line_total'])]
- TEST-011 (greengrocer): 10 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('RASPBERRIES 12X125G', ['pack', 'unit_price', 'line_total']), ('MUSHROOM CHESTNUT 3KG', ['pack', 'unit_price', 'line_total']), ('CARROT LOOSE 20KG', ['pack', 'unit_price', 'line_total']), ('PARSLEY FLAT BUNCH', ['pack', 'unit_price', 'line_total'])]
- TEST-012 (dairy_drinks): 2 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('JUICE APPLE 12X1L', ['vat_rate']), ('COFFEE BEANS ESPRESSO 1KG', ['vat_rate'])]
- TEST-015 (cashcarry): 1 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('TISSUE CENTREFEED 6RL', ['pack'])]
- TEST-016 (butcher): 10 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['PORK SAUS 8S 454G']; [('PORK SAUS 8S 454G', ['pack']), ('BUTCHERS STRING 500G', ['pack']), ('CHICKEN THIGH BONE IN 10KG', ['qty', 'pack', 'unit_price', 'line_total']), ('RUMP STEAK TRIMMED', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-019 (broadliner_a): 10 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('BACON SMKD RINDLESS 2KG', ['qty', 'pack', 'unit_price', 'line_total']), ('CLNG FLUID MULTI SURF 5L', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('BUTTER UNSLTD 20X250G', ['qty', 'pack', 'unit_price', 'line_total']), ('MAYO CATERING 5L', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-022 (butcher): 7 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['qty', 'pack', 'unit_price']), ('BUTCHERS STRING 500G', ['qty', 'pack', 'unit_price', 'vat_rate']), ('DISPOSABLE GLOVES BLU X100', ['qty', 'pack', 'unit_price']), ('CHICKEN THIGH BONE IN 10KG', ['qty', 'pack', 'unit_price'])]
- TEST-026 (broadliner_b): 5 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['HONEY SQUEEZY 12X340G']; [('FLR STRONG WHT BREAD 16KG', ['vat_rate']), ('DEGREASER HD SPRAY 750ML', ['vat_rate']), ('GRAVY GRANULES BEEF 2KG', ['pack', 'unit_price', 'line_total']), ('CHEESE CHEDDAR MED 5KG', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-029 (greengrocer): 1 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('CARRIER BAGS 100', ['vat_rate'])]
- TEST-031 (broadliner_a): 7 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('BLK PEPPER GRND 500G', ['qty', 'line_total', 'vat_rate']), ('GLOVE NITRILE BLU L X100', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('EGGS MED FR RANGE 180', ['qty', 'pack', 'unit_price', 'line_total']), ('HONEY CLEAR 3KG', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-032 (broadliner_b): 11 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['(line text partly obscured)']; [('SYRUP GOLDEN 6X680G', ['pack', 'unit_price', 'line_total']), ('COOKING CHOC 2X2.5KG', ['pack', 'unit_price', 'line_total']), ('VINEGAR BREWED 5 LTR', ['pack', 'unit_price', 'line_total']), ('OIL SUNFLWR 20 LTR JERRY', ['unit_price', 'line_total'])]
- TEST-033 (cashcarry): 3 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('BIN BAGS BLACK ROLL 100', ['pack']), ('BIN LINERS 200S', ['pack']), ('TISSUE CENTREFEED 6RL', ['pack'])]
- TEST-034 (butcher): 2 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack']), ('PORK SAUS 8S 454G', ['pack'])]
- TEST-036 (dairy_drinks): 3 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['VODKA 6X70CL']; [('CHEESE CHEDDAR 5KG BLOCK', ['qty', 'pack', 'unit_price', 'line_total']), ('COFFEE BEANS ESPRESSO 1KG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate'])]
- TEST-039 (cashcarry): 2 wrong, reconciled=True, silent=True, failed pages []; missing []; extra []; [('MINCED BEEF 5% 2KG', ['description']), ('TISSUE CENTREFEED 6RL', ['pack'])]
- TEST-042 (dairy_drinks): 10 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['40x250g']; [('WINE WHITE PINOT 6X75CL', ['qty', 'pack', 'unit_price', 'line_total']), ('PROSECCO DOC 6X75CL', ['qty', 'pack', 'unit_price', 'line_total']), ('JUICE APPLE 12X1L', ['pack', 'unit_price', 'line_total']), ('GINGER BEER 12X200ML', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-046 (butcher): 3 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('DUCK BREAST X2 400G', ['pack', 'unit_price', 'line_total']), ('OX CHEEK', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('BACON SMKD BACK 2KG', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-047 (greengrocer): 9 wrong, reconciled=False, silent=False, failed pages []; missing []; extra []; [('CARRIER BAGS 100', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('MUSHROOM CHESTNUT 3KG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('APPLE BRAMLEY 12KG', ['qty', 'pack', 'unit_price', 'line_total']), ('CAULIFLOWER', ['qty', 'pack', 'unit_price', 'line_total'])]
- TEST-049 (broadliner_a): 8 wrong, reconciled=False, silent=False, failed pages []; missing []; extra ['CHICKEN WINGS 5KG CASE']; [('OIL RAPESEED CATERING 20L', ['pack', 'unit_price', 'line_total']), ('SUGAR GRAN 15KG', ['qty', 'pack', 'unit_price', 'line_total']), ('LPG CYLINDER REFILL 13KG', ['qty', 'pack', 'unit_price', 'line_total', 'vat_rate']), ('STOCK BEEF PASTE 6X1KG', ['qty', 'pack', 'unit_price', 'line_total'])]
