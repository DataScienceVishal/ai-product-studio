# Holiday pay engine (T-111, kill-test Part A)

Pure, deterministic, stdlib-only Python 3 (Decimal for money). No I/O, no network.

- `engine/reference.py`: 52-paid-week average, no-pay weeks skipped, 104-week cap, fewer-weeks case.
- `engine/accrual.py`: 12.07% accrual (leave years from 2024-04-01), rolled-up pay, statutory entitlement, leaver proportion.
- `engine/elements.py`: pay categories counting for the 4 weeks of normal pay vs the 1.6 weeks (basic only allowed).
- `engine/lookback.py`: `lookback(history, leave)` returns per-leave-week `paid`, `due`, `difference` (positive = underpaid) and `working` (reference weeks used, scanned, skipped, total, average).

Run tests (from this folder): `python3 -I -m unittest discover -s tests -t . -v`

Official examples and where the published figures disagree with their own method: `benchmark/examples/SOURCES.md`.
Not legal advice; a payroll professional signs off. Assumptions: weekly history is complete, `allowance` counts only if status-related.
