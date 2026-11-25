# DEV tuning log (T-80)

DEV set only (10 invoices, 14 pages, seed 1001). Model: gpt-5-mini via the mini deployment. No TEST image or result was used.
Each pass was run once, 7 pages in parallel (`--workers 7`), so latencies include queueing; one sample per config, so
differences of a few points are noise. Scorer and bars untouched.

| Pass | Effort | Prompt | Overall | Clean | Distorted | Credit notes | Multi-page | Reconciled | Silent-error invoices | USD/page | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | low | v1 (committed in 1483f83) | 68.1% | 91.2% | 44.8% | 45.5% | 85.5% | 70% | 5 | 0.0041 | 27 |
| 2 | low | v2: column headers, row_text, row-by-row read, self-check, pack rules | 66.2% | 94.1% | 38.2% | 45.5% | 61.4% | 70% | 4 | 0.0046 | 29 |
| 3 | medium | v2 plus "qty has the sign of line_total" | 86.0% | 97.1% | 75.0% | 95.5% | 85.5% | 80% | 5 | 0.0091 | 91 |
| 4 | low | same as pass 3 | 77.9% | 97.1% | 58.8% | 45.5% | 81.2% | 70% | 4 | 0.0046 | 20 |
| 5 | medium | v3 plus pack as "count x size" and "X2 400G" total rule | **86.9%** | 98.5% | 75.4% | 100% | 88.4% | 80% | **1** | 0.0090 | 134 |

What each change fixed:
- Pack text: v1 copied "2 x 4.99" or "6 x" from receipt detail lines into pack_size. The v2 pack rules fixed that (clean 91% to 94-98%).
- Credit-note sign: low effort ignores the sign rule (45% on credit notes in passes 1, 2 and 4). Medium follows it (95-100%).
- Column drift on tilted photos: the main remaining error. On the distorted DEV pages the right-hand numbers are read from the neighbouring row (DEV-002, DEV-004), which gives wrong qty, price, total and pack-cost together. Medium effort roughly doubled distorted accuracy (about 40-59% at low to 75% at medium); the row_text and header prompt text did not fix it alone (pass 2 vs pass 1).
- Pass 5 also fixed "CHIPS 2.5KG X4" and "DUCK BREAST X2 400G" style packs. These two rules were written after seeing those DEV lines, so DEV accuracy is slightly flattered; held-out layouts will show how far the rules generalise.

## Chosen config (frozen)

Medium reasoning effort, the prompt in `extract_config.py` at pass 5, 16k output cap and one retry at 32k, 2048 px long edge, mini deployment.

Open risks the TEST run may hit, stated before it runs:
- DEV distorted accuracy is 75%, below the 90% PASS bar and under 80% (the KILL line). DEV has 5 distorted invoices, so this is a rough signal only, but it points to a likely INCONCLUSIVE or KILL on the distorted subset.
- Latency: pass 5 p95 was 134 s with 7 pages in flight, pass 3 was 91 s; the bar is 90 s (blocks PASS only) and the timeout is 180 s. Run the TEST with fewer workers (3 suggested) to measure latency closer to a single job; a page over 180 s takes the 32k retry.
- Cost per page about $0.009 is under the $0.02 bar.

Spend: ledger total after pass 5 is about $0.457 (including the 3 smoke calls), inside the $0.60 DEV allowance and the $5 cap.
