# T-115 review: CSV ingest, audit CLI, report, samples

Branch `p/holiday-pay-payroll-lookback-audit/T-115` at 17e3235, diffed against `main`. Reviewer: `reviewer` (opus).

**Verdict: CHANGES**

## Summary

The structure is good. The loader collects every issue with file and line, the CLI exits 2 and writes nothing when validation fails, and the report shows the working in plain English with the disclaimer on line 3. The sample is deterministic and the committed CSVs match the generator. The engine is called correctly: the loader checks weekday alignment and refuses negative, NaN and Infinity amounts before calling `lookback`, so on valid input the engine's own `ValueError` paths cannot fire.

There are four problems to fix before merge. One input lets a single leave row invent a large underpayment. `exceptions.csv` is open to formula injection through `worker_id`. A few malformed inputs crash with a traceback instead of exiting 2. And the W004 working tells the adviser that 57 weeks were no-pay weeks, which is not true.

## Evidence

- Test suite: `python3 -I -m unittest discover -s tests -t . -v` gives `Ran 141 tests in 0.106s / OK`.
- CLI on the sample reports 5 leave weeks and 4 exceptions. The exceptions are W002 +80.00, W003 -10.00, W004 +50.00 `shortened`, and W005 +15.00. Totals are £145.00 underpaid and £10.00 overpaid.

### Sample results re-derived by hand from the engine rules

- **W002, leave 2025-08-09.** The reference weeks are the 52 week-endings from 2024-08-10 to 2025-08-02. Every one has basic and commission, so none is skipped. Basic is 400 and commission is 30. Overtime is 60 when `(d-START)/7` is even and 40 when it is odd, so 52 consecutive weeks give 26 of each and an average of 50. Normal pay (basic + regular_overtime + commission) is 480.00 a week. This is the first leave week in the leave year starting 2025-04-01, so all of it is paid at the normal rate and 480.00 is due. `holiday_pay` paid is 400.00, so W002 is **underpaid by 80.00**. Matches.
- **W003, leave 2025-08-09.** The weeks ending 2025-01-04, 01-11, 01-18, 01-25 and 02-01 hold only `statutory` 116.75. `statutory` is not in `COUNTS_FOR_NORMAL`, so those weeks count as 0 and are skipped. To find 52 paid weeks the engine scans 57 weeks, back to 2024-06-29, which is after START (2024-06-01). Every paid week has basic 300, so the average is 300.00. Paid is 310.00, so W003 is **overpaid by 10.00**. Matches, and the 52 used / 5 skipped is asserted in the tests.
- **W005 (extra check).** Of the 52 weeks from 2024-08-10 to 2025-08-02, 26 fall on or after 2025-02-08 and are paid 330. The other 26 are paid 300. The average is 315.00 and W005 is underpaid by 15.00. Matches.
- **W004.** There are 47 week-endings from 2024-07-06 to 2025-05-24, each paid 400, so 400.00 is due. Paid is 350.00, so W004 is underpaid by 50.00. The `shortened` flag is correct.

### Mutation testing on `ingest/loader.py`

| Mutation | Caught? |
|---|---|
| Drop the history weekday-alignment check | yes |
| Drop duplicate-row detection | yes |
| Accept an empty file | yes |
| Drop the `weeks <= 0` check | yes |
| Drop the NI-number check | yes |
| Turn off personal-header refusal | yes |
| Accept negative amounts | yes |
| Accept an unknown `worker_type` | yes |
| Drop the leave weekday check | yes |
| **Drop the duplicate-column check (line 79-82)** | **no** |
| **Skip validation of `contract_weekly_basic` (line 203)** | **no** |
| **Accept rows with too many fields (`!=` changed to `<`, line 89)** | **no**: `zip` silently drops the extra fields |

## Critical issues (must fix)

1. **A leave row with `weeks` greater than 1 invents an underpayment.** `ingest/loader.py:168-171` only checks `weeks > 0`. The probe `W1,2025-06-14,50` on a history with £100 a week gives `due 5000.00, paid 50.00, underpaid 4950.00` for a single payroll week. FORMAT.md says there is one row per leave week and gives 0.5 as the example, so `weeks` must be in (0, 1]. Fix: refuse `weeks > 1` with a line-level issue, and add a test.

2. **CSV formula injection through `worker_id`.** `ingest/loader.py:99-107` accepts any non-empty, non-NI string. `report/builder.py:337` writes it as is. The probe `=HYPERLINK("http://x")` produced exit 0 and the cell `"=HYPERLINK(""http://x"")"` in `exceptions.csv`, which Excel runs as a formula. The same value goes unescaped into the Markdown heading at `builder.py:348`, and `<script>x</script>` and an email address as `worker_id` are also accepted. Fix: validate `worker_id` against an allowlist such as `^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$` with `re.ASCII`. Because of the first-character rule this also blocks `= + - @`, and it stops emails and Markdown. As a second layer, prefix `'` in `_csv_row` to any cell starting with `= + - @ \t \r`. Add a test for both.

3. **Malformed input crashes with a traceback (exit 1) instead of a validation error (exit 2).** The contract is that every error is reported and the exit code is 2.
   - **Decimal overflow.** `ingest/loader.py:19` sets `_NUM = ^\d+(\.\d+)?$` with no length limit. The amount `100000000000000000000000000000000` passes validation and then raises `decimal.InvalidOperation` in `engine/reference.py:18` (`money().quantize` goes beyond 28-digit precision). Python's `\d` also matches non-ASCII digits: `١٠٠` was accepted as 100. Fix: use `^[0-9]{1,9}(\.[0-9]{1,2})?$`. Two decimal places is the money format FORMAT.md describes; allow 1-2 dp for `weeks`.
   - **csv.Error.** `ingest/loader.py:94` catches only `OSError` and `UnicodeDecodeError`. A field over 131072 characters raises an uncaught `_csv.Error: field larger than field limit`. Fix: also catch `csv.Error` and report it with `reader.line_num`.

4. **The W004 working is misleading about skipped weeks.** `report/builder.py:351-352` prints "47 paid week(s) found looking back 104 week(s), 57 no-pay week(s) skipped". Those 57 weeks come before W004's first payroll row (2024-07-06). They are not weeks of zero pay; the file has no data for them. An adviser reading this would conclude W004 had 57 unpaid weeks. W003's "5 no-pay week(s)" had £116.75 SSP each, so that wording is also inaccurate. Fix: the loader knows each worker's first `week_ending`, so pass it through to `WorkerData`. The report then separates "N week(s) before the first payroll row in the file (no data)" from "M week(s) with no pay that counts (none, or only excluded items such as SSP)". Assert the W004 wording in `tests/test_audit.py`.

5. **Tests do not catch three validator regressions** (the mutation table above). Add tests for:
   - a duplicate header column;
   - an invalid `contract_weekly_basic` (for example `abc` or `-1`) in `workers.csv`;
   - a row with too many fields (for example `W1,2025-06-07,basic,1,extra`).

## Suggestions (not blocking)

- `audit.py:288`: `--out` pointing at an existing file, or at a directory that cannot be written, raises an uncaught `FileExistsError` or `FileNotFoundError`. Catch `OSError`, print one line and exit with a non-zero code. `write_outputs` (`builder.py:367-386`) also overwrites existing outputs and can leave a new `exceptions.csv` next to an old `report.md` if the second write fails. Write both to temporary files and rename them into place.
- Gaps inside a worker's history (a missing export week) cannot be told apart from unpaid weeks, because "Weeks with no pay need no rows" (FORMAT.md). Consider listing gaps between the first and last week as a warning in report.md so the adviser can confirm them.
- `builder.py:377`: "Workers" counts only workers who have leave rows. Rename it to "Workers with leave" or count all loaded workers.
- `samples/generate.py:50`: `date(2025,1,4) <= d <= date(2025,2,8) and d != date(2025,2,8)` is just `date(2025,1,4) <= d < date(2025,2,8)`.
- NI regex (`loader.py:20`) misses hyphenated forms such as `QQ-12-34-56-C`. The `worker_id` allowlist in item 2 still lets them through, so add `-` to the optional separators.
- When the history file fails, the leave file then reports "leave for worker 'W1' who has no payroll history" for every row. That is noise on top of the real error. Consider suppressing those messages when the history file already has file-level issues.

## Security notes

- No network access, no `eval`, no unsafe deserialisation.
- Personal-data refusal works for headers and the NI pattern. The `worker_id` allowlist in item 2 also closes the email and name-in-ID cases.
- `--out` is a local CLI argument chosen by the operator, so path traversal is not a concern.
