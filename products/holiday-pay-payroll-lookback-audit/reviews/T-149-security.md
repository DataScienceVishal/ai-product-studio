VERDICT: PASS

# T-149 security and privacy review

Reviewer: security agent, 2026-11-26. Scope: `git diff 9336720..main -- products/holiday-pay-payroll-lookback-audit` at `34c5e87`. That covers T-134..T-140: the `Leave years` summary line, blank due/difference for cannot_check rows, the basic-differs flag change, the blank-contract rate fallback, the new flags `rate_inferred_ambiguous` and `no_basic_pay_found`, and the new report text. Earlier passes were `reviews/T-120-security.md` and `reviews/T-129-security.md`. Their fixes were only re-checked here for regressions. Probes ran in the session scratchpad (`.../scratchpad/t149/`). No network calls and no product code edits.

Tests: `python3 -m unittest discover -q` gives **Ran 318 tests, OK**.

| Section | Result | Evidence |
|---|---|---|
| CSV / formula injection (`exceptions.csv`) | PASS | The new flags are constants that go through `_safe` (`report/builder.py:160`). The new blank `due` and `difference` cells are `""` or a `:.2f` value (`builder.py:156-159`). `worker_id` is still `_safe` and must match `_ID` (`ingest/loader.py:24`, first character alphanumeric). Probe row: `W0,2001-01-13,50.00,100.00,50.00,underpaid,shortened;rate_inferred_no_contract_basic;rate_inferred_ambiguous;no_basic_pay_found,1,0,103,100.00,0.00,leave_lookback`. |
| Markdown injection (`report.md`) | PASS | `_leave_years_line` (`builder.py:423-436`) escapes IDs with `_md()`. The month name comes from a fixed tuple and the day is an int from a validated MM-DD. The new `explain` line and the `FLAG_TEXT` entries are constants. The new summary counts are ints. |
| PII in errors, warnings and report | PASS | No new error messages. A bad `leave_year_start` is still masked. Probe `Jane QQ123456C` gives `leave_year_start 'Ja...' (14 chars) ...; nothing written`. The `Leave years` line shows only allowlisted IDs, which `_worker_id` has already checked against NI and date shapes. It shows at most 20 IDs, then `and N more`. |
| Input validation | PASS (improved) | `_MMDD` and `_DATE` changed from `^...$` with `.match` to `.fullmatch` (`loader.py:19,21,161,184`). This is stricter: a trailing `\n` can no longer pass the `$` check, and values are stripped before matching. No new input fields. |
| Resource use | PASS (1 Low) | The new fallback tiers (`engine/lookback.py:76-85`) make at most 3 linear scans per leave week, and only when the 8-week window has no basic. The `Leave years` line sorts once (O(W log W)). Probe: 50 fixed_pay workers x 1,500 weeks (750 leave weeks each, 75k lines) took 16.8 s with overtime only (fallback path) against 15.9 s with basic (normal path). So the fallback adds no measurable cost. Both paths are about O(leave weeks x history) per worker because of the existing `basics = [basic_pay(p) for p in recent_first]` (`lookback.py:62`). That predates this diff and is acceptable at realistic sizes. See L-1. |
| File modes, atomic writes | PASS | `_atomic_write_pair` and mkstemp are unchanged. Probe outputs: `-rw------- exceptions.csv`, `-rw------- report.md`. On a validation error the tool printed "nothing written" and created no out dir. |
| Secrets | PASS | I scanned the diff for `sk-`, `api_key`, `AccountKey`, `sig=`, `ghp_`, `xox`, `AKIA`, private-key headers and NI-shaped strings: no hits. |
| Dependencies | PASS (N/A) | Still stdlib only. |
| Privacy basics | PASS | T-120 L-5 (DRAFT retention wording) was closed in T-131. No new personal fields. |
| Infrastructure | N/A | Local CLI. |

## Findings

### L-1 (Low, new): look-back exceptions are still uncapped in report.md, and T-137 makes many more of them
`report/builder.py:388` writes a detailed section for **every** look-back exception. Only rolled-up sections are capped (T-130/T-131: 20 per worker, 500 in total). T-137 added `always_exception` (`builder.py:65-70`, used at `:96`). It makes every fixed_pay leave week with `rate_inferred_ambiguous` or `no_basic_pay_found` an exception, even when the difference is £0.00. A firm that leaves `contract_weekly_basic` blank and had a pay rise in the window will therefore get a section for nearly every fixed_pay leave week.

Repro (synthetic, `scratchpad/t149/h.csv`, `l.csv`, `w.csv`): 50 fixed_pay workers, no contract basic, 1,500 weeks each with every other week as leave:
```
python3 audit.py --history h.csv --leave l.csv --workers w.csv --out o
37500 leave weeks checked, 37500 exceptions.  -> report.md 52,189,874 bytes, 37,502 headings
```
At a realistic size (300 workers, 2 years, about 17k leave weeks) this gives a report of about 20+ MB. Nothing leaks and the run finishes. It is a usability and memory problem, not an exposure.
**Fix:** apply the same per-worker and total caps to look-back sections, with an `and K more in exceptions.csv` line. Or collapse rows that only have a guessed rate and a £0.00 difference into one line per worker. Keep `exceptions.csv` complete. Add a size-bound test.

### I-1 (Info): the per-leave-week rescans of full history predate this diff
`lookback.py:62` recomputes `basic_pay` over the whole history for each leave week, so the cost per worker is O(L x H). It is not exploitable at payroll scale (measured above). If the tool is ever hosted with untrusted uploads, compute `basics` once per worker and slice it.

### Regressions checked
- T-120 M-1, L-1, L-2 and T-129 I-2 (`explain_rolled_up` esc): not regressed. `_safe`, `_md` and masking are all still on the paths that changed.
- T-120 L-4 (mapper not wired into `audit.py`): still holds. `audit.py` imports no mapper.

## Suggested board task
1. L-1: cap or collapse look-back sections in report.md the same way as rolled-up sections, plus a size test (builder, 30 min).
