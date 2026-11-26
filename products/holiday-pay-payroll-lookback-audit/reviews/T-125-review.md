# T-125 review: accuracy gate for BRIEF.md

Reviewer, 2026-11-26. File checked: `products/holiday-pay-payroll-lookback-audit/BRIEF.md` (168 lines) on `main`, against the product code, `benchmark/`, `reviews/`, `state/ideas/holiday-pay-payroll-lookback-audit.md`, `state/ideas/RANKING.md` and `state/QUESTIONS.md` Q-16. BRIEF.md was not edited.

## Verdict: CHANGES

One behaviour claim is wrong and is repeated in the quiz: the report does **not** say "recalculated". There is also one misleading causal sentence in the worked example. Everything else I checked is accurate, including every number in the worked example and the demo output. Both fixes are a few words each.

## Evidence I ran (from the product folder)

```
$ python3 audit.py --history samples/history.csv --leave samples/leave.csv --workers samples/workers.csv --out <tmp>/out
5 leave weeks checked, 4 exceptions. Written to <tmp>/out          (exit 0)
exceptions.csv:
W002,2025-08-09,400.00,480.00,80.00,underpaid,,52,0,0,480.00,
W003,2025-08-09,310.00,300.00,-10.00,overpaid,,52,5,0,300.00,
W004,2025-05-31,350.00,400.00,50.00,underpaid,shortened,47,0,57,400.00,
W005,2025-08-09,300.00,315.00,15.00,underpaid,,52,0,0,315.00,
report.md: "Underpayments: 3, total underpaid £145.00" / "Overpayments: 1, total overpaid £10.00"
files: -rw------- exceptions.csv, -rw------- report.md

$ ... --threshold 20      -> "5 leave weeks checked, 2 exceptions" (W002 80.00, W004 50.00)

$ (history.csv with header worker_id renamed to name)
h.csv:1: column 'name' looks like personal data; use pseudonymous IDs only. Refused
... 7 validation error(s); nothing written.     exit=2, out dir not created

$ python3 -I -m unittest discover -s tests -t .
Ran 228 tests in 1.446s
OK
```

## Wrong claims (must fix)

### W1. "Output says 'recalculated'" (section 5, Q3) and quiz Q7 / answer 7
- Quoted: "**Is it legal advice?** No. Output says "recalculated", is labelled not legal advice, ..." (BRIEF.md:101). Quiz: "Why does the report say "recalculated" rather than "owed"?" (BRIEF.md:153) and answer 7 (BRIEF.md:165).
- Correct fact: the word "recalculated" does not appear anywhere in the product's code or output. `grep -rni recalculat --include=*.py --include=*.md` in the product folder finds only BRIEF.md. The report's wording is "Due: £X. Paid in the leave week: £Y. Result: underpaid by £Z." (`report/builder.py:134-135`), and the only guardrail text is `DISCLAIMER = "Not legal advice; a payroll professional signs off."` (`report/builder.py:14`, printed in bold at the top of report.md). "recalculated under these settings" is a validator **guardrail requirement** in the idea file (`state/ideas/holiday-pay-payroll-lookback-audit.md:76`). It has not been implemented.
- Fix: say the report shows "due", "paid" and "underpaid/overpaid by", carries the "Not legal advice; a payroll professional signs off" line, and that the idea file's guardrail asking for "recalculated" wording (never "owed") is not built yet. Reword or replace quiz Q7 to match. You could also add this to section 7 "Cannot do yet".

### W2. W003 "overpaid by 10.00 because sick-pay-only weeks are skipped" (BRIEF.md:56)
- Correct fact: W003 is overpaid because £310.00 was paid against £300.00 due. Skipping the 5 SSP-only weeks is what keeps the average at £300.00 (`samples/generate.py:9-10`; csv row `ref_weeks_skipped` = 5). If those weeks were not skipped, the average would fall and the overpayment would grow. So skipping is not the cause.
- Fix: "overpaid by 10.00 (paid 310 vs 300 due; its 5 sick-pay-only weeks are skipped so the average stays 300)".

## Verified correct (sample)

- Status: G0 parked, score 64, rank 1 (`state/ideas/RANKING.md:9`, idea file line 4 and score table line 63). The brief states plainly that this is pre-G1, not a product, synthetic data only, and that the mapper is unproven (lines 3, 97, 133). It sets no price: section 5 Q1 says "Not set; selling locked", and the DCK £73.50/hour and Irwin Mitchell £1,500 + VAT figures match idea file lines 225 and 227 and are labelled "Not a quote". No invented features: what is not connected is spelled out in section 4.6.
- Worked example, W002: basic 400, commission 30, overtime 40/60, average 50, due 480.00, paid 400.00, underpaid 80.00 (`samples/generate.py:7-8, 47-49`; CLI output above; `tests/test_audit.py:165,178`). W001 correct, W004 50.00 with `shortened`, W005 15.00, totals 3 / £145.00 and 1 / £10.00: all match the CLI output.
- `reference_average` with 52 paid weeks and a 104-week cap, skipping zero-pay weeks (`engine/reference.py:45-46, 74-101`). `money` rounds half up (`reference.py:54-56`).
- `CATEGORIES` (8 values) and `COUNTS_FOR_NORMAL` = basic, regular_overtime, commission, allowance (`engine/elements.py:13-16`). `normal_pay` is at `elements.py:27`.
- First 4 leave weeks of the leave year (from 1 April) get normal pay, later weeks basic only (`engine/lookback.py:6-7, 18, 125`). A positive difference means underpaid (`lookback.py:157`). Misaligned weekdays raise (`lookback.py:107-114`). `no_reference_weeks` (`lookback.py:144-145`) is always an exception and is not counted as an under- or overpayment (`report/builder.py:57, 69, 285-287`).
- fixed_pay: contract basic plus the average of variable elements; the rate is inferred and flagged when there is no contract basic (`lookback.py:47-90`).
- Ingest: column allowlist, personal-header refusal, NI-shape refusal, the `EMPAB123456C` gap and "do not rely on the check" (`ingest/loader.py:24-29, 88-90, 106-112, 144-145`; `ingest/FORMAT.md:5-6`). Negative amounts refused (`loader.py:19,172`; FORMAT.md:13). Exit 2, up to 50 errors, masked values, nothing written (`audit.py:13, 38-46`; `loader.py:76-79`).
- Report: `audit()` / `--include-flagged` (`builder.py:54-71`), `explain`, `write_outputs`, mode 0600 (`builder.py:193`, FORMAT.md:35), the three warning sections (`builder.py:170-280`), `_safe` and `_md` (`builder.py:74-81`), `FLAG_TEXT` (`builder.py:17`).
- 169 tests at 3d9f6da (`reviews/T-120-security.md:3`). T-120 verdict CHANGES (line 7). T-122 PASS. T-123 PASS on re-review.
- KILL-TEST: written before any engine code (line 3). Part A PASS, 17+ examples, 12 left out, 3 of 4 areas, gov.uk slips recorded (lines 31). Part A moves no score; A+B gives 64 to 66 (line 25). Gold labels on a separate branch; BrightPay layout only (line 33). Pass line 95%, cost under $0.02, kill above $0.05 (lines 20-21).
- Mapper: nine categories, gpt-5-mini, strict JSON schema, one live run with locking, no repair, $2 hard cap, https only, more than 500 names refused, human must confirm the table before audit use (`mapper/README.md:3-4, 10, 29-33, 38-40, 46-56`). Worst case about $0.31 and still waiting on a yes (`state/QUESTIONS.md:141`).
- `audit.py`, `report/` and `ingest/` never import `mapper`, `accrual` or `monthly`. Those modules are exported (`engine/__init__.py`) and tested (`tests/test_official_examples.py`, `tests/test_edge_cases.py`).
- Forcing event wording: "expected to begin in 2027", penalties proposed only, response unpublished, re-check 2026-11-26 (idea file lines 87-92, 240-245, 278-280). AI 7/15 (score table header line 60). Build 3 to 4 weeks (line 51). Armstrong Watson (line 237). The DPDP mention is legitimate because `playbooks/comprehension-brief.md:18` requires it.

## Suggestions (not blocking)

1. Section 4.4 and section 6 say "I could not run them" (BRIEF.md:112). They now run, and the expected output is confirmed (above). Replace the caveat with the verified result, and add the current count of **228 passing tests** next to the historical 169.
2. Section 4.1: leave.csv also takes an optional `weeks` column (default 1, at most 1; FORMAT.md:18).
3. Section 4.3 says "atomically". The guarantee covers Python exceptions; a crash or power loss mid-rename is not covered (`builder.py:184-192`, FORMAT.md:35). Add "(except a crash mid-write)".
4. Glossary "Exception" (BRIEF.md:32): also include leave weeks that cannot be checked, to match section 4.3.
5. Engine exit 2 also covers data the engine rejects (for example misaligned weekdays): `audit.py:47-51` prints "cannot audit this data". Section 4.2 could mention the exit code.
6. Refusal demo: the stderr output also lists 5 "settings for worker ... who has no payroll history" lines from workers.csv. Either warn the presenter about them or drop `--workers` from that demo run.

## Re-review (commit ab4a1a5)

Reviewer, 2026-11-26. Diff checked: `git show ab4a1a5 -- BRIEF.md` (8 lines changed). I re-read the rest of the file; nothing else changed. Tests were re-run on this tree: `Ran 228 tests ... OK`.

### Verdict: PASS

- **W1 fixed.** Buyer Q3 (BRIEF.md:101) now quotes the real report wording, "Due / Paid / underpaid-by" and "Not legal advice; a payroll professional signs off." (`report/builder.py:14, 134-135`), and says the "recalculated, not owed" guardrail is not built yet. Quiz Q7 and its answer (BRIEF.md:153, 165) now ask about and quote the DISCLAIMER line. "recalculat" now appears only in the two sentences that say it is not built.
- **W2 fixed.** W003 (BRIEF.md:56): "paid 310.00 against 300.00 due; its sick-pay-only weeks are skipped, which keeps the average at 300.00". This matches the CLI output and `samples/generate.py:9-10`.
- Suggestion 1 done: 228 tests, matching my run, and the demo now states the verified line "5 leave weeks checked, 4 exceptions" (matches `audit.py:61` output).
- Suggestion 2 done: leave.csv has an optional `weeks` fraction such as 0.5 (FORMAT.md:18: above 0, at most 1).
- Suggestion 3 done: the atomic-write caveat matches `builder.py:184-192` (rollback on failure; a crash mid-write is not covered).
- Not taken, still non-blocking: suggestions 4-6 (glossary "Exception" also covers cannot-check rows; engine-rejection exit 2; noisy workers.csv lines in the refusal demo). Nit: BRIEF.md:112 has "; Verified" with a capital V after a semicolon.
