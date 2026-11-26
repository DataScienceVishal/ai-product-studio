# Holiday pay engine (T-111, kill-test Part A)

Pure, deterministic, stdlib-only Python 3 (Decimal for money). No I/O, no network.

- `engine/reference.py`: 52-paid-week average, no-pay weeks skipped, 104-week cap, fewer-weeks case.
- `engine/accrual.py`: 12.07% accrual (leave years from 2024-04-01), rolled-up pay, statutory entitlement, leaver proportion.
- `engine/elements.py`: pay categories counting for the 4 weeks of normal pay vs the 1.6 weeks (basic only allowed).
- `engine/lookback.py`: `lookback(history, leave)` returns per-leave-week `paid`, `due`, `difference` (positive = underpaid) and `working` (reference weeks used, scanned, skipped, total, average).

Run tests (from this folder): `python3 -I -m unittest discover -s tests -t . -v`

Official examples and where the published figures disagree with their own method: `benchmark/examples/SOURCES.md`.
Not legal advice; a payroll professional signs off. Assumptions: weekly history is complete, `allowance` counts only if status-related.

Assumptions for adviser sign-off: the first 4 weeks of leave taken in each leave year are treated as the normal-pay (reg 13) weeks, and a leave week belongs to the leave year containing its week-ending date. `worker_type="variable_hours"` (default, s224 averaging) or `"fixed_pay"` (current basic rate plus 52-week average of variable elements). Misaligned dates raise; rows carry `flags` (`no_reference_weeks`, `shortened`, `leave_week_missing_from_history`).

## Run an audit (T-115)

```
python3 audit.py --history history.csv --leave leave.csv [--workers workers.csv] --out out/ [--threshold 0.01] [--include-flagged]
```
Try it on the synthetic sample: `python3 audit.py --history samples/history.csv --leave samples/leave.csv --workers samples/workers.csv --out out/`.
Writes `out/exceptions.csv` (one row per leave week whose difference exceeds the threshold) and `out/report.md` (summary plus the working in plain English). Exit 0 on success; exit 2 if any input is invalid: errors are printed to stderr with file and line (first 50, values masked), and nothing is written. Leave weeks that cannot be checked, or that look inconsistent (holiday pay not in leave.csv, leave week without holiday_pay), are listed or flagged, never silently dropped. Input columns, privacy rules (pseudonymous IDs only; name/NI columns are refused) and an example: `ingest/FORMAT.md`. Sample data and the hand-computed expectations: `samples/generate.py`.
