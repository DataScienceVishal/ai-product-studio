## per document (model_only | rules_and_risky_cap)

| doc | kind | persona | cat acc | routed | silent errs | ratio (pilot formula) | ratio (silent charged) | calibrated: cat acc / routed / silent / ratio silent |
|---|---|---|---|---|---|---|---|---|
| fenwick_trade | pdf | tradesperson | 0.9062 | 0.2188 | 2 | 0.5062 | 0.8063 | 1.0 / 0.0938 / 0 / 0.3513 |
| quillon_consult | pdf | consultant | 0.9375 | 0.4688 | 0 | 0.8163 | 0.8163 | 1.0 / 0.125 / 0 / 0.39 |
| tarn_stall | pdf | market_stall | 0.9375 | 0.375 | 0 | 0.7 | 0.7 | 1.0 / 0.0625 / 0 / 0.3125 |
| corvid_trade | pdf | tradesperson | 0.9688 | 0.2188 | 1 | 0.5062 | 0.6562 | 1.0 / 0.0312 / 0 / 0.2737 |
| fenwick_consult | pdf | consultant | 0.9688 | 0.3438 | 0 | 0.6613 | 0.6613 | 1.0 / 0.0312 / 0 / 0.2737 |
| csv_a_trade | csv | tradesperson | 0.9688 | 0.25 | 1 | 0.545 | 0.695 | 1.0 / 0.0312 / 0 / 0.2737 |
| csv_b_stall | csv | market_stall | 0.9375 | 0.3125 | 0 | 0.6225 | 0.6225 | 1.0 / 0.0625 / 0 / 0.3125 |
| sheet_trade | xlsx | tradesperson | 0.9375 | 0.2812 | 2 | 0.5837 | 0.8838 | 0.9688 / 0.2188 / 0 / 0.5062 |
| sheet_consult | xlsx | consultant | 1.0 | 0.2188 | 0 | 0.5062 | 0.5062 | 1.0 / 0.0625 / 0 / 0.3125 |
| scan_trade | scan | tradesperson | 0.9375 | 0.125 | 4 | 0.39 | 0.99 | 1.0 / 0.0938 / 2 / 0.6512 |
| sheet_stall | xlsx | market_stall | 1.0 | 0.3125 | 0 | 0.6225 | 0.6225 | 1.0 / 0.0625 / 0 / 0.3125 |
| csv_a_consult | csv | consultant | 0.9688 | 0.3438 | 0 | 0.6613 | 0.6613 | 1.0 / 0.0312 / 0 / 0.2737 |

## per format (pooled over docs)

| format | docs | lines | model cat acc | ratio pilot formula | ratio silent charged | calibrated ratio (pilot formula) | calibrated ratio silent charged | silent errors per 100 auto lines (model / calibrated) |
|---|---|---|---|---|---|---|---|---|
| Clean PDF | 5 | 160 | 94.4% | 63.8% | 72.8% | 32.0% | 32.0% | 2.8 / 0.0 |
| CSV export | 3 | 96 | 95.8% | 61.0% | 66.0% | 28.7% | 28.7% | 1.5 / 0.0 |
| Owner spreadsheet | 3 | 96 | 97.9% | 57.1% | 67.1% | 37.7% | 37.7% | 2.9 / 0.0 |
| Scan (image) | 1 | 32 | 93.8% | 39.0% | 99.0% | 35.1% | 65.1% | 14.3 / 6.9 |
| All docs | 12 | 384 | 95.6% | 59.3% | 71.8% | 32.9% | 35.4% | 3.7 / 0.6 |

## threshold sweep (all docs, calibrated, silent errors charged)

| threshold | routed % | silent errs | ratio pilot formula | ratio silent charged |
|---|---|---|---|---|
| 0.7 | 5.5% | 3 | 30.3% | 34.0% |
| 0.8 | 7.6% | 2 | 32.9% | 35.4% |
| 0.9 | 8.9% | 2 | 34.5% | 37.0% |
| 0.95 | 8.9% | 2 | 34.5% | 37.0% |

## ambiguous lines (truth flagged ambiguous): model category accuracy

ambiguous lines 112, model correct 98 (87.5%)

## tokens and cost

| doc | in tokens | out tokens | reasoning | latency s | USD |
|---|---|---|---|---|---|
| scan_trade | 1311 | 10343 | 8868 | 260.7 | 1.26 |
| corvid_trade | 957 | 1623 | 1286 | 92.0 | 0.21 |
| fenwick_trade | 940 | 3061 | 2720 | 92.6 | 0.38 |
| tarn_stall | 953 | 2864 | 2530 | 113.0 | 0.36 |
| quillon_consult | 953 | 2202 | 1863 | 124.7 | 0.28 |
| sheet_trade | 783 | 2345 | 2007 | 57.5 | 0.29 |
| csv_a_trade | 948 | 1638 | 1294 | 110.9 | 0.21 |
| fenwick_consult | 948 | 3750 | 3414 | 112.3 | 0.46 |
| csv_b_stall | 967 | 2722 | 2390 | 117.3 | 0.34 |
| photo_consult | None | None | None | 108.0 | 0.00 |
| sheet_stall | 785 | 1619 | 1283 | 81.7 | 0.21 |
| sheet_consult | 773 | 1493 | 1156 | 138.7 | 0.19 |
| scan_stall | None | None | None | 169.5 | 0.00 |
| csv_a_consult | 945 | 2381 | 2058 | 143.5 | 0.30 |

TOTAL: calls 15 of 15, input 11263, output 36041, $4.49 of $11.50
