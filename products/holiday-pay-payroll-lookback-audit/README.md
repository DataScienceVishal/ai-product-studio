# Holiday pay engine (T-111, kill-test Part A)

Pure, deterministic, stdlib-only Python 3 (Decimal for money). No I/O, no network.

- `engine/reference.py`: 52-paid-week average, no-pay weeks skipped, 104-week cap, fewer-weeks case.
- `engine/accrual.py`: 12.07% accrual (leave years from 2024-04-01), rolled-up pay, statutory entitlement, leaver proportion.
- `engine/elements.py`: pay categories counting for the 4 weeks of normal pay vs the 1.6 weeks (basic only allowed).
- `report/rolled_up.py` (T-126): week-by-week check of rolled-up holiday pay for `irregular_rolled_up` workers, using `engine/accrual.py` (`accrual_applies`, `rolled_up_pay`) and `engine/elements.py`. Flags `rolled_up_before_2024_rules` and `rolled_up_not_shown_separately`, or recalculates 12.07% of pay that counts. Their leave weeks are not re-audited by the look-back. Rules: `ingest/FORMAT.md`. Leave years come from the worker's `leave_year_start` (default 1 April).
- `engine/lookback.py`: `lookback(history, leave)` returns per-leave-week `paid`, `due`, `difference` (positive = underpaid) and `working` (reference weeks used, scanned, skipped, total, average).

Run tests (from this folder): `python3 -I -m unittest discover -s tests -t . -v`

Official examples and where the published figures disagree with their own method: `benchmark/examples/SOURCES.md`.
Data retention (DRAFT): inputs are your files; the tool keeps nothing beyond `out/exceptions.csv` and `out/report.md`. Delete them after sign-off; any hosted version must delete uploaded inputs within 30 days. Details in `ingest/FORMAT.md`.
Not legal advice; a payroll professional signs off. Assumptions: weekly history is complete, `allowance` counts only if status-related.

Leave weeks after the first 4 in a leave year (basic only) use the average of basic over the 52 most recent weeks with basic pay (within 104 weeks), which can differ from the weeks used for normal pay; for `fixed_pay` they use the current basic rate.

Assumptions for adviser sign-off: the first 4 weeks of leave taken in each leave year are treated as the normal-pay (reg 13) weeks, and a leave week belongs to the leave year containing its week-ending date (the year starts 1 April unless the worker has a `leave_year_start`). `worker_type="variable_hours"` (default, s224 averaging) or `"fixed_pay"` (current basic rate plus the average of variable elements over the 52 most recent paid weeks within 104 weeks; a paid week is any week with pay that counts for normal pay, so an overtime-only week counts and a week with no such pay is skipped). Misaligned dates raise; rows carry `flags` (`no_reference_weeks`, `shortened`, `leave_week_missing_from_history`).

## Run an audit (T-115)

```
python3 audit.py --history history.csv --leave leave.csv [--workers workers.csv] --out out/ [--threshold 0.01] [--include-flagged]
```
Try it on the synthetic sample: `python3 audit.py --history samples/history.csv --leave samples/leave.csv --workers samples/workers.csv --out out/`.
`workers.csv` may carry a per-worker `leave_year_start` (MM-DD, default 04-01; T-127). Non-default start dates are named in a `Leave years:` line in the `report.md` summary (omitted when all are 1 April). stdout: `5 leave weeks checked, 4 exceptions. Written to out/` (look-back only), then `13 rolled-up pay weeks checked, 8 exceptions.` when rolled-up workers exist. Writes `out/exceptions.csv` (one row per leave week whose difference exceeds the threshold, plus rolled-up pay exceptions, told apart by the `check` column) and `out/report.md` (summary plus the working in plain English). A header-only `leave.csv` is accepted only when every worker is `irregular_rolled_up` (rolled-up-only audit; a mixed firm still exits 2). Rolled-up workers with nothing to check, or leave weeks missing from history, get a stdout `note:` and a `report.md` note; `report.md` shows at most 20 detailed rolled-up sections per worker and 500 in total, with `and K more` lines for the first 50 affected workers and one combined line for the rest (exceptions.csv is complete). Exit 0 on success; exit 2 if any input is invalid: errors are printed to stderr with file and line (first 50, values masked), and nothing is written. Leave weeks that cannot be checked, or that look inconsistent (holiday pay not in leave.csv, leave week without holiday_pay), are listed or flagged, never silently dropped. Input columns, privacy rules (pseudonymous IDs only; name/NI columns are refused) and an example: `ingest/FORMAT.md`. Sample data and the hand-computed expectations: `samples/generate.py`.
