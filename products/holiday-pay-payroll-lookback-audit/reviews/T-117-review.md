# Review: p/holiday-pay-payroll-lookback-audit/T-117 (commit ecb1898)

Reviewer: reviewer agent. Diff: `git diff main...p/holiday-pay-payroll-lookback-audit/T-117` (5 files, +147/-12).

**Verdict: CHANGES** (one small must-fix, in the rollback failure path)

## Summary

T-117 covers all five T-116 suggestions. The rollback in `_atomic_write_pair` works in every failure I tried except one:
when the rollback itself fails. In that case the error is not reported, even though the docstring says it is, and the
`finally` block deletes the backup, which is then the only copy of the user's previous file. The brief asked for an
accurate docstring and for the pair never to be mismatched, so this has to be fixed before merge. The fix is a few
lines. Range grouping, the `gaps=None` summary line, the FORMAT.md note and the `history_gaps` export are all correct.
The sample CLI output is byte-identical to `main`.

## Evidence

- Full suite on the exact branch tree (HEAD = ecb1898), `python3 -I -m unittest discover -s tests -t . -v` from the
  product folder: `Ran 164 tests in 0.171s` / `OK`.
- Sample CLI (`--workers samples/workers.csv`): W002 +80.00 underpaid, W003 -10.00 overpaid, W004 +50.00 `shortened`,
  W005 +15.00 underpaid; `5 leave weeks checked, 4 exceptions`. Both `exceptions.csv` and `report.md` are
  byte-identical to the output of `main`. Both files have mode `-rw-------`.
- Probes run by hand against `report.builder.write_outputs` with `os.replace`, `os.link` and `shutil.copy2` patched:

| Case | Result |
|---|---|
| Stale `.report.md.abc.bak`, `.exceptions.csv.x.tmp`, `report.md.bak` user files already in out dir, 2nd rename fails | OLD pair restored; all three user files untouched (mkstemp names are random, so they never collide) |
| Hard link unavailable (EPERM), copy fallback, 2nd rename fails | OLD pair restored, no leftovers |
| `report.md` is a symlink to a file outside out dir, success | symlink replaced by a regular file; the target is unchanged |
| Same symlink, 2nd rename fails | symlink restored as a symlink (Linux `link()` does not follow symlinks) |
| Dangling `report.md` symlink | succeeds |
| `report.md` is a directory | `IsADirectoryError` raised, folder unchanged (CLI prints "cannot write output", exit 2) |
| KeyboardInterrupt on 2nd rename | OLD pair restored, interrupt propagates |
| Backup creation fails (link and copy both fail) | original error raised, folder unchanged |
| **Rollback `os.replace(backup, dest)` fails** | **only "2nd fail" raised; folder left with NEW exceptions.csv + OLD report.md; the OLD exceptions.csv is deleted** |

- Mutations (each applied alone to a copy of the tree, full suite run):

| Mutation | Result |
|---|---|
| M1 rollback does not restore from backup | killed |
| M2 rollback does not remove new file when there was no previous one | killed |
| M3 backups not cleaned up | killed |
| M4 range step 14 days instead of 7 | killed |
| M5 `if gaps:` instead of `if gaps is not None:` | killed |
| M6 copy fallback replaced by `raise` | **survived** (no test forces `os.link` to fail) |
| M7 exception swallowed after rollback | killed |
| M8 skip the `os.remove(backup)` after mkstemp | survived, but harmless: link fails with EEXIST and the copy fallback overwrites the empty placeholder |

## Critical issues (must fix)

1. **A failed rollback is silent and deletes the last copy of the user's previous file.**
   `report/builder.py:176-184` and `:191-195`. If `os.replace(backup, dest)` raises, `except OSError: pass` drops the
   error. The `finally` block then removes every path in `leftovers`, including that backup. The result is a mismatched
   pair (new `exceptions.csv`, old `report.md`), the old `exceptions.csv` gone for good, and a CLI message that only
   names the original rename failure. Line 146 of the docstring says "a failure while rolling back is reported", which
   is not true. This is rare, but failures in the same folder tend to come together (permissions, a filesystem
   problem), and this is exactly the case the task was meant to make safe.
   **Fix:** when a rollback step fails, take that backup out of `leftovers` so it is kept, and record it. After the
   loop, if any step failed, raise an `OSError` (chained `from` the original) whose message names the kept backup
   path(s) and says the pair may be mismatched, for example
   `"... and rollback failed; previous file kept at <out>/.exceptions.csv.XXXX.bak"`. The CLI already prints
   `e.strerror or e`, so make sure the text reaches it (set `strerror`, or have the CLI print `str(e)`). Add one test
   that patches `os.replace` to fail for `.bak` sources too. It should assert exit 2, that the message mentions the
   backup, and that the backup file still exists with the OLD content. If you choose to keep it silent instead, the
   docstring and FORMAT.md must say so, but keeping the backup is still required.

## Suggestions (non-blocking)

1. **Test the copy fallback.** M6 survived. Add a test that patches `report.builder.os.link` to raise
   `OSError(EPERM)` combined with the 2nd-rename failure, and assert the OLD pair is restored with no leftovers.
2. **Hard links on other platforms.** On macOS/BSD, `link()` follows symlinks, so a symlinked `report.md` would be
   restored as a regular file that shares the target's inode. Passing `follow_symlinks=False` to `os.link` makes this
   explicit and portable. Low priority because deployment is Linux.
3. **The mkstemp/remove/link sequence (lines 164-171) has a small race.** Between `os.remove(backup)` and
   `os.link`, another process could create that name, and then `shutil.copy2` would overwrite it. The out dir is
   owner-chosen and the name is random, so the risk is negligible. A comment explaining why the placeholder is
   created and then removed (to reserve a unique name) would help the next reader.
4. **Async interrupt window.** A KeyboardInterrupt that lands between `os.replace(tmp, dest)` and
   `backups.append(...)` (lines 172-174) would skip rolling back that file. This is a gap of a few bytecodes and
   is covered by "crash mid-rename not covered". Optional: append to `backups` before the replace, and have the
   rollback check whether the tmp still exists.
5. The test helper name `_fail_second_replace` is fine. `test_history_gaps_exported` could also assert
   `"history_gaps" in report.__all__`.

## Checks with no findings

- **Range grouping:** `history_gaps` produces sorted, unique dates on a 7-day grid, so `_week_ranges` never sees
  duplicates or out-of-order dates. A single week, one run, and several runs are all tested. The end-to-end gap test
  checks the 5-week range text. The week count before the colon still uses `len(ws)`, which matches the total of the
  ranges.
- **`gaps=None`:** the summary line is omitted, `gaps={}` prints `0`, and `_gap_section(None)` returns `[]`. The CLI
  always passes a dict, so CLI output is unchanged.
- **FORMAT.md:** states 0600 accurately and that existing modes are replaced. "If either cannot be written, the folder
  keeps its previous contents" holds once must-fix 1 is done. Until then, it is false in the rollback-failure case.
- **Security:** no new input reaches a shell, SQL or an LLM. Backup names come from `mkstemp` in the out dir with
  mode 0600, and hard-linked backups keep the original inode's mode. Hard links are removed on success, so the
  number of links to user files returns to what it was.
- **Performance:** one extra link and unlink per output file. Negligible.

## Re-review (1553475)

**Verdict: PASS.** The must-fix is resolved, and nothing new blocks the merge.

### Evidence
- Full suite on the exact tree (HEAD = 1553475), `python3 -I -m unittest discover -s tests -t . -v` from the product
  folder: `Ran 166 tests in 0.216s` / `OK`.
- Sample CLI: `5 leave weeks checked, 4 exceptions`. `exceptions.csv` and `report.md` are byte-identical to `main`
  (W002 +80.00, W003 -10.00, W004 +50.00 `shortened`, W005 +15.00).
- Forced rollback-failure probe re-run (2nd rename fails and `os.replace` from `.bak` fails):
  `OSError: 2nd fail; rollback failed, the output files may not match: previous exceptions.csv kept at
  <out>/.exceptions.csv.986ph4hq.bak (rollback fail)`. The `.bak` survives with the OLD content. The CLI prints this
  message because the new `OSError` has no `strerror`, so `e.strerror or e` falls through to `str(e)`. The new test
  `test_failed_rollback_keeps_backup_and_names_it` checks exit 2, the path in stderr, the backup content and that no
  `.tmp` files are left.
- I re-ran all the other probes (stale `.bak` and user files, copy fallback, symlink success and rollback with
  `follow_symlinks=False`, dangling symlink, directory dest, KeyboardInterrupt, backup creation failure). The results
  are the same as before and all correct.
- The docstring now matches the behaviour.

### Mutation M6 still survives (non-blocking)
With `shutil.copy2(dest, backup)` replaced by `raise`, the suite still passes. The new
`test_link_unavailable_uses_copy_fallback_and_rolls_back` combines no-links with a 2nd-rename failure. A broken
fallback aborts before any rename, so it produces the same end state (OLD pair, exit 2) and the test cannot tell the
two apart. I confirmed this by hand: with links unavailable and no other failure, the mutated code raises
`[Errno 1] no links` and the real code succeeds. **Suggested fix:** add a test where `os.link` raises EPERM and
nothing else fails, and assert exit 0 with the new files written and no `.bak` left. This kills M6.

### Other notes (non-blocking)
- If the original exception is a KeyboardInterrupt and the rollback also fails, the new chained `OSError` replaces
  the interrupt. The CLI then prints the message and exits 2 instead of stopping on the interrupt. This is acceptable
  because the message is more useful, but a re-raise of non-`Exception` types could be considered.
- `os.link(..., follow_symlinks=False)` raises `NotImplementedError` (not `OSError`) on platforms that do not support
  it, such as Windows, and the copy fallback would not catch it. Deployment is Linux, so this is fine. Catch
  `(OSError, NotImplementedError)` if Windows support is ever needed.
