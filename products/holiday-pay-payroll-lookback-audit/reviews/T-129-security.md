# T-129 security and privacy review

Reviewer: security agent, 2026-11-26. Scope: `git diff 8b1b749..HEAD -- products/holiday-pay-payroll-lookback-audit` at `f540e4e`. That covers T-124 (`ingest/loader.py` `contract_weekly_basic`), T-126 (`report/rolled_up.py`, `report/builder.py` rolled-up checks and the new `check` column in `exceptions.csv`) and T-127 (per-worker `leave_year_start`). Earlier pass: `reviews/T-120-security.md`. Its fixed findings (M-1, L-1, L-2) are only re-checked here for regressions. Probes were run in `/tmp/claude-0/sec-t129/`. No network calls, no code edits.

Tests: `python3 -m unittest discover -s tests -t .` gives **Ran 269 tests, OK**.

## Verdict: PASS

The new code does not reintroduce any T-120 problem. The new input fields are validated and masked, and every new output value is a constant, an enum, a date, a formatted number or an allowlisted ID. I found one new Low finding (output size and memory on large rolled-up inputs) and two Info items. One T-120 Low (L-5, retention and deletion text) is still open and is not on the board. Nothing is exposed and nothing is urgent.

| Section | Result | Evidence |
|---|---|---|
| CSV / formula injection (`exceptions.csv`) | PASS | The new `check` column is a constant (`leave_lookback` / `rolled_up_pay`, `builder.py:18`). Rolled-up rows (`builder.py` `_csv_row`, rolled-up branch) contain `_safe(worker_id)`, an ISO date, `:.2f` numbers or blanks, the `rule_flag`/underpaid/overpaid/correct enum, and `_safe` flags taken from a fixed set. `worker_id` still has to match `_ID` (`loader.py:22`, first character alphanumeric). Probe output: `R1,2000-01-01,12.07,,,rule_flag,rolled_up_before_2024_rules,,,,,,rolled_up_pay`. |
| Markdown injection (`report.md`) | PASS | Every new section (`_ignored_basic_section`, `_holiday_paid_section`, `_stray_section`, `_rolled_up_notes`) passes IDs through `_md()`. `explain_rolled_up` is called with `esc=_md` (`builder.py:393`). `worker_type` in the ignored-basic list is enum-validated. T-120 I-3 is fixed: the flagged-worker list now uses `_md` (`builder.py:373`). See I-2. |
| PII echo in errors and stdout | PASS | Bad `leave_year_start` and bad `contract_weekly_basic` values are passed through `_mask` (`loader.py:271`, `:276`/`:175`). Probes: `John Smith` gives `'Jo...' (10 chars)`, `QQ123456C` gives `'QQ...' (9 chars)`, a 131,000-char cell gives `'xx...' (131000 chars)`, and `Jane Doe QQ123456C` as the basic gives `'Ja...' (18 chars)`. The new zero-basic message (`loader.py:278`) prints `{wid}` only after `_worker_id` has refused NI- and date-shaped values, which matches the existing messages. The new stdout and stderr lines (`audit.py`) print counts only. |
| Input validation (new fields) | PASS | `_MMDD` is anchored ASCII `[0-9]`, so Arabic-Indic digits `١٢-٠١` are refused. The value is stripped before matching, so the `$`-before-newline quirk does not apply. The real-date check refuses `00-00`, `13-01`, `02-29`, `1-1` and `04-01x`. Extreme combinations (week `2000-01-01` with start `12-31`, `2100-12-31` with `01-02`) cannot overflow, because dates are limited to 2000-2100 and `_leave_year_start` moves back at most one year. A worker with all-pre-2024 rolled-up pay gives `rule_flag` rows, not the `ValueError` from `rolled_up_pay`, because `check_week` tests `accrual_applies` first (`rolled_up.py`). |
| Regex DoS | PASS | The only new regex is `_MMDD`, which is fixed-length and anchored. `_looks_like_ni` is unchanged. |
| Paths, atomic writes, rollback, file modes | PASS | `_atomic_write_pair` (`builder.py:215`) and the out-dir handling are unchanged in the diff. New outputs are still 0600 (`-rw------- exceptions.csv`, `report.md` in probe `o2`). On a validation error, "nothing written" was confirmed. |
| Resource use | PASS (1 Low) | L-1 |
| Secrets | PASS | I scanned the diff for `sk-`, `api_key=`, `AccountKey=`, `sig=`, `ghp_`, `xox`, `AKIA` and private-key headers: no hits. The new sample rows use synthetic IDs `W006`-`W008`, with no names or NI-shaped values. |
| Dependencies | PASS (N/A) | Still stdlib only. No requirements file or package.json was added. |
| Privacy basics | FAIL (Low, carried over) | T-120 L-5 is still open. `ingest/FORMAT.md` still does not say that the inputs and `out/` are personal data (pseudonymised), how long to keep them, or how to delete them. No board task tracks it. |
| Infrastructure | N/A | Local CLI. |

## Findings

### L-1 (Low, new): `report.md` has one section per rolled-up exception, with no cap, and is built fully in memory
`report/builder.py:393` adds an `explain_rolled_up` section for every rolled-up exception. `report/rolled_up.py:71` (`audit_rolled_up`) makes up to two rows per pay week per `irregular_rolled_up` worker. The whole report is joined in memory at `builder.py:408`. Before T-126, report sections scaled with leave weeks. Now they scale with every pay week of every rolled-up worker.

Repro (`/tmp/claude-0/sec-t129/bh.csv`): 3,000 `irregular_rolled_up` workers x 100 weeks, each week `basic 100`, `rolled_up_holiday_pay 10.00` and `holiday_pay 5.00` (900,001 lines, about 30 MB):
```
python3 audit.py --history bh.csv --leave bl.csv --workers bw.csv --out ob
300000 rolled-up pay weeks checked, 600000 exceptions.
real 23.5 s, peak RSS 1,603 MB; report.md 214,284,449 bytes, exceptions.csv 48,084,151 bytes
```
For comparison, a 600k-line file with fewer exceptions ran in 10.4 s with a 776 MB peak and a 48 MB report. Nothing leaks and the run finishes. But a realistic mistake, such as setting the wrong `leave_year_start` so that every week is flagged `rolled_up_before_2024_rules`, produces a report nobody can open, and memory roughly doubles. On a small laptop or a future hosted runner this could hit out-of-memory.
**Fix:**
1. In `report.md`, group rule-flag weeks per worker and flag into ranges with the existing `_week_ranges` (one line, for example `R1: rolled_up_before_2024_rules, 39 weeks: 2024-04-06 to 2024-12-28`).
2. Show at most about 20 detailed sections per worker, followed by `... N more in exceptions.csv`.
3. Optionally write `md` to the temp file line by line instead of `"\n".join(md)`.
4. Add a test with 1 worker x 500 flagged weeks that checks report.md stays under a size bound.

Keep `exceptions.csv` complete.

### I-1 (Info): the FORMAT.md masking promise lists too few columns
`ingest/FORMAT.md:7` names `worker_id`, `week_ending`, `element_category`, `amount` and `worker_type`. The code also masks `leave_year_start`, `contract_weekly_basic` and `weeks` (all through `_mask`/`_amount`). The T-127 paragraph mentions `leave_year_start`, but the central privacy sentence is now incomplete. **Fix:** change it to "any cell value".

### I-2 (Info): `explain_rolled_up` escapes nothing by default
`report/rolled_up.py:118` has `def explain_rolled_up(r, gbp, esc=str)`. The only caller passes `_md`, and IDs are allowlisted, so nothing can be exploited today. A future caller that leaves out `esc` would put unescaped IDs into Markdown. **Fix:** make `esc` a required argument, or default it to an escaping function.

### Carried over from T-120, still open
- **T-120 L-5 (Low):** retention and deletion guidance in FORMAT.md, marked DRAFT, not legal advice. It was not part of T-121/T-122 and has no board task.
- **T-120 I-2 (Info):** Excel turns IDs such as `1-2`, `1E5` and `00123` into other values. This is still undocumented.
- **T-120 L-4:** a condition on wiring the mapper into `audit.py`. It is still not wired (`audit.py` imports no mapper), so the condition holds.

## Suggested board tasks
1. L-1: group or cap rolled-up sections in report.md, plus a size test (builder, 30 min).
2. T-120 L-5, I-2 and this review's I-1 and I-2: one docs-and-hardening task (builder, 20 min).
