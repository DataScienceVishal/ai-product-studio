# Review: T-116 (T-115 review leftovers)

Branch `p/holiday-pay-payroll-lookback-audit/T-116`, commit 6f4eca6, diff `git diff main...HEAD`
(6 files, +182/-19). Reviewer: reviewer agent, 2026-11-26.

## Verdict: PASS

All seven T-115 suggestions are done. Engine output is unchanged, the sample CLI output is unchanged, the
full suite is green, and 10 of 12 mutations were caught. The other 2 behave the same as the original code
(details below). Nothing here blocks the merge. The suggestions below are worth a later task.

## Evidence

- Full suite on the exact branch tree (`python3 -I -m unittest discover -s tests -t . -v` from the product folder):
  `Ran 157 tests in 0.170s` / `OK`.
- Sample CLI (`--workers samples/workers.csv`): W002 +80.00 underpaid, W003 -10.00 overpaid, W004 +50.00 `shortened`
  (47 used, 57 before first record), W005 +15.00 underpaid. `exceptions.csv` is byte-identical (`cmp`) to the
  output from a `main` worktree. In `report.md` only the summary changed: "Workers: 5" became "Workers loaded: 5"
  plus "Workers with leave: 5", and the line "Workers with weeks missing from the export: 0" is new.
- Generator: `samples/generate.py` on both the branch and `main` writes history/leave/workers CSVs that are byte-identical
  to the committed samples. The committed sample CSVs are untouched by the diff.
- Gap detection, run by hand on a synthetic file (W1 has gaps, W2 has a single row, W3 has a gap after an SSP-only week).
  The report lists `W1: 2 week(s): 2025-06-21, 2025-07-05` and `W3: 1 week(s): 2025-06-14`. W2 has no entry. The week
  with only `statutory` rows is not called a gap, which is correct because it has rows. `exceptions.csv` is
  byte-identical to `main` on the same input, so engine results do not change.
- Single-row worker: `weeks[0] + 7 < weeks[0]` is false, so the result is empty. A worker can never have an empty
  history, because `WorkerData` is only created when a history row is accepted. So `weeks[0]` cannot raise.
- `--out` error paths: an existing file gives `cannot write output to '...': File exists` with exit 2. A path under a
  file gives `... Not a directory` with exit 2. Each is one line with no traceback.
- Item 6, suppression: `history_failed` is computed before the leave file is read, so it only reflects history-file
  issues. When the history is clean, "no payroll history" is still reported. Tests cover this, and mutation M2 caught
  it. When the history has errors, the leave message is held back but the run still fails with exit 2 and writes
  nothing. A real leave typo therefore shows up on the next run after the history is fixed. It is delayed, never
  silently accepted.

### Mutations (scratch copy, full suite each time)

| # | Mutation | Result |
|---|---|---|
| M1 | never suppress the "no payroll history" message | caught (1 failure) |
| M2 | always suppress it | caught (2) |
| M3 | suppress only on file-level history issues | caught (1) |
| M4 | invert the gap membership test | caught (2) |
| M5 | gap step of 14 days | caught (1) |
| M6 | no temp-file cleanup | caught (2) |
| M7 | do not prune `temps` after a rename | not caught. Behaves the same: the later `os.remove` hits ENOENT, which is swallowed |
| M8 | rename each file straight after writing it (not atomic) | caught (6) |
| M9 | CLI does not catch OSError | caught (4 errors) |
| M10 | "Workers loaded" count off by one | caught (2) |
| M11 | gap section dropped | caught (1) |
| M12 | start the gap scan at the first week | not caught. Behaves the same, because the first week is always present |

## Critical issues

None.

## Suggestions (non-blocking)

1. **A rename failure partway through can leave a mismatched pair.** In `report/builder.py`, `_atomic_write_pair`
   (`for tmp, dest in temps: os.replace(...)`): if the first `os.replace` succeeds and the second fails, the folder
   holds a new `exceptions.csv` next to an old `report.md`. I reproduced this by patching the second `os.replace`
   to fail. Both temp files were removed and the CLI exits 2, so the user does see the failure. Both files are in
   the same directory, so this is very unlikely on POSIX. Still, the docstring and the T-116 aim promise "no partial
   outputs". Fix options: (a) write both files into a fresh sibling temp directory and swap the directory into place,
   or (b) on a second-rename failure, delete the already-renamed new file and say so in the message. At the very
   least, update the docstring so it does not promise more than the code does.
2. **Output file permissions changed from 0644 to 0600.** `mkstemp` creates files with mode 0600, and `os.replace`
   carries that mode over. It also replaces the inode, so any mode or owner on files already in `--out` is lost.
   For payroll data, 0600 is arguably the better default. It is still a silent behaviour change, so either record it
   in FORMAT.md or README, or call `os.chmod(tmp, 0o666 & ~umask)` if the old behaviour is wanted. Record the
   decision either way.
3. **The gap list has no size limit.** A worker with a long break, such as a year off, produces one line with more
   than 50 dates. Group consecutive weeks into ranges, for example `2024-03-02 to 2025-02-22 (52 weeks)`. That keeps
   the report readable for the payroll professional.
4. **The `write_outputs` defaults can mislead callers.** When `gaps=None` it still prints "Workers with weeks missing
   from the export: 0", even though the caller never ran the check. Print that line only when `gaps is not None`,
   which matches how `workers_loaded` is handled, or make `gaps` a required argument.
5. **Where `history_gaps` lives.** `audit.py` imports it from `report.builder` rather than from the `report` package
   that it already imports from. Export it from `report/__init__.py` for consistency. This is cosmetic.
6. **Small test gap.** No test covers the mismatched pair from suggestion 1 or file modes. Add tests once those
   behaviours are decided.

## Security and performance

- No new inputs reach a shell, SQL or an LLM. `_md(wid)` escapes worker IDs in the gap section. Temp files are
  created with `mkstemp` in the target directory, so there is no predictable-name or symlink race. Mode 0600 limits
  exposure.
- `history_gaps` runs in O(weeks spanned) per worker with no I/O. That is negligible.
