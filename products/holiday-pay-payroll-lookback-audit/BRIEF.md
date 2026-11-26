# Brief: holiday-pay payroll look-back audit

**Status in one line: a pre-G1 parked idea (G0, score 64, rank 1), not a sellable product. There is a working engine and CLI on synthetic data only; no real payroll has ever been run through it.** (`state/ideas/holiday-pay-payroll-lookback-audit.md`, `state/ideas/RANKING.md`)

Paths below are relative to `products/holiday-pay-payroll-lookback-audit/` unless they start with `state/`.

## 1. One-picture overview

```
 payroll export                    (human or, later, AI: sort each pay item
 (3 CSV files)                      name into a category such as "overtime")
      |                                         |
      | history.csv, leave.csv,                 | NOT wired in yet (section 4.6)
      | workers.csv                             v
      v                                 [ mapper/ ]  one paid test waits for Q-16
 +-----------+  validated rows  +-----------------+  per-leave-week    +--------------+
 | ingest/   | ---------------> | engine/         | -----------------> | report/      |
 | loader.py |  (or exit 2,     | lookback.py     |  paid, due, diff,  | builder.py   |
 | refuses   |   nothing        | deterministic   |  working, flags    | writes 2     |
 | bad / PII |   written)       | Decimal maths   |                    | files        |
 +-----------+                  +-----------------+                    +------+-------+
                                                                              |
                          exceptions.csv (table) + report.md (plain English) <-+
                                                                              |
                                          payroll professional reads and SIGNS OFF
```

Glossary (first use):
- **Look-back**: re-checking holiday pay that was already paid in past payroll runs.
- **Leave week**: a week in which a worker took holiday.
- **Reference period / 52-week average**: for workers with variable pay, holiday pay is their average weekly pay over up to 52 paid weeks before the leave, skipping weeks with no pay, never reaching back more than 104 weeks (`engine/reference.py`, `reference_average`).
- **Exception**: a leave week where what was paid differs from what the rules give by more than a threshold (default 1p).
- **Pseudonymous ID**: a payroll ID that does not identify a person by itself.

## 2. The 60-second story

- **Problem.** UK employers and payroll bureaux calculate holiday pay for irregular-hours workers, often by spreadsheet. Evidence: Xero admin said a 52-week report is not on their roadmap; BrightPay docs say the holiday pay amount is entered manually (`state/ideas/holiday-pay-payroll-lookback-audit.md`, validator notes; partly search summaries).
- **Forcing event.** Holiday-pay records duty in force since 6 April 2026. Enforcement by the Fair Work Agency (FWA) is "expected to begin in 2027", with no date. Penalties are only proposed. The government response to the consultation is unpublished (same file, re-check 2026-11-26).
- **Product.** Upload a payroll export; get a list of leave weeks where holiday pay looks wrong, with the working shown.
- **Why AI.** Honestly: the maths is deterministic Python. AI's intended job is only mapping messy pay-item names to categories. The validator scored AI 7/15 for this reason.
- **Guardrail.** Every report says "Not legal advice; a payroll professional signs off" (`report/builder.py`, `DISCLAIMER`).

## 3. One small example, end to end

Take worker W002 from the synthetic sample (`samples/generate.py` docstring, asserted in `tests/test_audit.py`).

| Step | What happens | Number |
|---|---|---|
| Input | Each week: basic 400, commission 30, overtime alternating 40 / 60 | |
| Leave | One week on 2025-08-09, first leave week of the leave year starting 1 April | |
| Reference | 52 paid weeks before it; overtime averages 50 | |
| Due | basic 400 + commission 30 + overtime 50 (`engine/elements.py`, `normal_pay`) | 480.00 |
| Paid | `holiday_pay` row in the leave week (basic only) | 400.00 |
| Output | `underpaid by £80.00`, with weeks used and the average in `report.md` | 80.00 |

The other four sample workers show the other cases: correct (W001), overpaid by 10.00 because sick-pay-only weeks are skipped (W003), shortened history flag (W004, 50.00 under), mid-period pay rise (W005, 15.00 under). Totals: 3 underpayments of 145.00, 1 overpayment of 10.00.

## 4. How each part works

### 4.1 Ingest (`ingest/loader.py`, `ingest/FORMAT.md`)
- Reads three CSVs: `history.csv` (worker, week ending, pay category, amount), `leave.csv` (worker, week), optional `workers.csv` (`variable_hours` default, or `fixed_pay` with a contract basic).
- Pay categories must already be one of: basic, regular_overtime, commission, bonus_non_regular, allowance, expense_excluded, holiday_pay, statutory (`engine/elements.py`, `CATEGORIES`).
- Privacy: columns are an allowlist; name, NI number, address and date-of-birth style columns are refused; NI-shaped IDs are refused. FORMAT.md admits the NI check can be got round (e.g. `EMPAB123456C`), so "do not rely on it".
- Negative amounts (clawbacks, corrections) are refused; the user must net them first.
- Failure: exit code 2, up to 50 errors to stderr with file and line and masked values, nothing written (`audit.py`, `main`).

### 4.2 Engine (`engine/`)
- `lookback.py`, `lookback(history, leave, ...)`: per leave week returns `paid`, `due`, `difference` (positive = underpaid), flags and `working`.
- Assumption (stated in the file): the first 4 leave weeks of a leave year (starting 1 April) get "normal pay" (basic + regular overtime + commission + allowance); later weeks get basic only. Wrong if leave.csv omits weeks (FORMAT.md warns).
- `fixed_pay` workers: contract basic rate plus 52-week average of variable elements; rate inferred (and flagged) if no contract basic given.
- Money is `Decimal`, rounded half-up to the penny (`engine/reference.py`, `money`).
- Failure modes: misaligned weekdays raise an error; leave week with no earlier pay is flagged `no_reference_weeks` and reported "cannot be checked", never counted as an error.

### 4.3 Report (`report/builder.py`)
- `audit()` picks exceptions: difference over threshold, or cannot-check; `--include-flagged` adds any flagged row.
- `explain()` writes the plain-English working per exception; `write_outputs()` writes `exceptions.csv` and `report.md` together, atomically, owner-only permissions (0600) (`ingest/FORMAT.md`).
- Also warns about weeks missing from the export, holiday pay recorded but not in leave.csv, and ignored contract basics.
- Spreadsheet-injection protection: `_safe()` prefixes risky cells; `_md()` escapes Markdown.

### 4.4 Tests and the proof test
- Run: `python3 -I -m unittest discover -s tests -t . -v` (README.md). Security review counted 169 passing tests at commit 3d9f6da (`reviews/T-120-security.md`).
- `benchmark/KILL-TEST.md` was written before any code ran. **Part A (engine) PASSED**: 17+ gov.uk/Acas worked examples reproduced, 12 left out with written reasons, covering 3 of 4 required areas (no official example exists for regular overtime/commission, so it is unit-tested only). The gov.uk examples contain arithmetic slips that the engine does not copy (`benchmark/examples/SOURCES.md`, KILL-TEST results).
- Part A alone does not move the score.

### 4.5 Mapper: the AI part (`mapper/`, `mapper/README.md`)
- Sorts pay-item names into nine categories using Azure OpenAI gpt-5-mini with a strict JSON schema.
- **Part B pass line:** at least 95% right on 200 synthetic names, cost under $0.02 (aim) and kill above $0.05. Gold labels were frozen on a separate branch so the mapper's author cannot see them.
- **One live run only.** Once any reply arrives the results folder locks; bad replies count as wrong, are never repaired.
- Spend guard: hard $2 cap, https only, refuses over 500 names; worst case about $0.31 per `state/QUESTIONS.md` (Q-16 update).
- **Not run.** Waiting on Vishal's yes to Q-16 (`state/QUESTIONS.md`).
- Limit: only BrightPay's import layout is public; Xero and Sage 50 export layouts could not be fetched, so the layout half of B1 covers BrightPay only (KILL-TEST.md, Part B status).

### 4.6 What is NOT connected
- `audit.py` and `report/` never import `mapper/`. The audit expects categories already assigned. The mapper README says a person must confirm the mapping table before it feeds an audit (prompt-injection risk from hostile pay-item names).
- `engine/accrual.py` (12.07% accrual, rolled-up pay) and `engine/monthly.py` are exported and tested against official examples, but `lookback.py`, `report/` and `audit.py` do not call them. So the CLI does **not** check the 12.07% accrual rule or whether rolled-up pay is shown separately. Those were in the idea file's pitch.

## 5. Buyer Q&A (honest; no live product exists)

1. **What does it cost?** Not set; selling locked (`CLAUDE.md` section 6). Only context: bureaux already bill holiday pay calculations as an extra (DCK £73.50/hour; Irwin Mitchell £1,500 + VAT per review), from the idea file. Not a quote.
2. **What does it check today?** Whether holiday pay paid in each leave week equals the 52-week-average figure under the "first 4 weeks normal pay" assumption (`engine/lookback.py`). It does not yet check 12.07% accrual or rolled-up pay presentation (section 4.6).
3. **Is it legal advice?** No. Output says "recalculated", is labelled not legal advice, and a payroll professional signs off (`report/builder.py`; validator guardrails in the idea file).
4. **How accurate is it?** It reproduces the 17+ official gov.uk/Acas examples it encoded (KILL-TEST.md). On real payrolls: unknown, never tested. Rounding and "normal pay" rules are disputed between sources (idea file).
5. **What if the data are wrong or incomplete?** Missing weeks are listed for you to confirm; unusable weeks are flagged "cannot be checked" rather than guessed (`report/builder.py`, `FLAG_TEXT`). Armstrong Watson note: payroll exports may lack leave data, so HR leave records must be joined in (idea file, T-23).
6. **Which payroll systems does it support?** None directly. It reads a standard CSV (`ingest/FORMAT.md`). Mapping real exports (BrightPay, Xero, Sage 50) is the mapper's planned job and is unproven.
7. **What does AI do, and what if it is wrong?** Intended only to suggest pay-item categories. Nothing in the audit depends on it today. A person must confirm the table (`mapper/README.md`).
8. **Where does worker data go? UK GDPR?** Today the CLI runs locally, no network, outputs 0600 (`ingest/FORMAT.md`). It asks for pseudonymous IDs and refuses names/NI numbers, but that check is not foolproof. A production design (hosting, DPA, retention) does not exist; the idea file says it is needed. No DPDP analysis has been done.
9. **Will the Fair Work Agency or payroll vendors make this redundant?** Possible. The FWA plans a free holiday pay calculator with unstated scope; if it takes a whole payroll, Competition drops to 2 and the idea is likely dead (idea file, validator re-score). Vendors could add a report.
10. **Support and setup time?** Not defined. Build plan estimate was 3 to 4 weeks for an MVP; no support model exists.

## 6. Demo script (synthetic sample only)

Derived from `README.md`, `audit.py`, `tests/test_audit.py`; I could not run them. Run from the product folder. Sample files: `samples/history.csv`, `samples/leave.csv`, `samples/workers.csv` (generated by `samples/generate.py`).

```
python3 -I -m unittest discover -s tests -t . -v
python3 audit.py --history samples/history.csv --leave samples/leave.csv \
    --workers samples/workers.csv --out out/
```
Expected terminal line (from the code, `audit.py`): `5 leave weeks checked, 4 exceptions. Written to out/` (the 4 = W002, W003, W004, W005). Then open `out/report.md` and `out/exceptions.csv`.

Optional second runs:
- `... --threshold 20` shows only the 80.00 and 50.00 rows (`tests/test_audit.py`, `test_threshold`).
- Refusal demo: copy `samples/history.csv`, rename `worker_id` to `name`, run; expect exit 2 and nothing written (`ingest/loader.py`, personal-data header check).

| Demo step | Shows | Section |
|---|---|---|
| Test run | engine matches official examples | 4.4 |
| Audit command | ingest, engine, report | 4.1-4.3 |
| report.md W002 | working in plain English | 3 |
| W004 flag `shortened` | honest caveats | 4.2 |
| Privacy refusal | data protection stance | 4.1 |

Say plainly in any demo: synthetic data, not a product, mapper unproven.

## 7. Limits and roadmap

Cannot do yet: check 12.07% accrual or rolled-up pay in the CLI; take real export formats; join HR leave data; handle negative corrections; model sickness/family leave, pre-2024 rules or rounding variants as options; run as a hosted service.

What is open (all from `state/ideas/...` and `state/QUESTIONS.md`):
- Q-16: approve up to $2 for the Part B mapper test. PASS would lift AI +1 and Build +1 (64 to 66), still below 70.
- Government consultation response and FWA calculator scope decide whether urgency is real and the gap survives.
- Security review (T-120) was CHANGES (NI-number refusal weak, mapper cost cap); later reviews T-122 and T-123 PASS on the cap work. The pseudonymised data design is not signed off.
- Also open: no job-ad signal and no published software price.

## 8. Self-check quiz

1. What stage is this idea at, and what is its score?
2. What does a positive `difference` mean in an exception row?
3. Under the engine's assumption, which leave weeks get normal pay and which get basic only?
4. How far back does the reference period reach, and how are no-pay weeks treated?
5. What happens, and what exit code, if the input has a name column?
6. Which pay-element categories count for "normal pay"?
7. Why does the report say "recalculated" rather than "owed"?
8. What does Part B test, what is the pass line, and why is it not run?
9. Name two things in the pitch that the CLI does not currently check.
10. Which single outside event could cut Competition to 2?

### Answers
1. G0, parked, 64 (`state/ideas/RANKING.md`, idea file).
2. Underpaid: due minus paid is positive (`engine/lookback.py`).
3. First 4 leave weeks in each leave year (from 1 April): normal pay; later: basic only. Needs every leave week listed.
4. Up to 52 paid weeks within 104 weeks; no-pay weeks (including only-SSP weeks) are skipped (`engine/reference.py`).
5. Refused as personal data; exit 2; nothing written.
6. basic, regular_overtime, commission, allowance (`engine/elements.py`, `COUNTS_FOR_NORMAL`).
7. Legal-advice boundary: a calculation tool, with a professional signing off.
8. AI sorting 200 synthetic pay-item names at 95% or better; waits for Q-16 spend approval.
9. 12.07% accrual and whether rolled-up pay is shown as a separate payslip item (engine code exists but is not called).
10. The FWA publishing a free holiday pay calculator that accepts a whole payroll.
