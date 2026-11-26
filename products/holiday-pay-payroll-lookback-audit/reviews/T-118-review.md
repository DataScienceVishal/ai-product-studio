# Review: p/holiday-pay-payroll-lookback-audit/T-118 (commit c8f4b90)

Reviewer: reviewer agent. Diff: `git diff main...p/holiday-pay-payroll-lookback-audit/T-118`
(`report/builder.py` +11/-1, `tests/test_audit.py` +62).

**Verdict: PASS**

## Summary

T-118 closes the three non-blocking notes from the T-117 re-review:
1. A test where only `os.link` fails now requires a successful run with no `.bak` left. This kills mutation M6.
2. A KeyboardInterrupt (or any other non-`Exception`) whose rollback also fails is re-raised as the interrupt. The
   backup is kept, the note is printed to stderr and attached with `add_note`.
3. `NotImplementedError` from `os.link(..., follow_symlinks=False)` now falls back to `shutil.copy2`.

The change is small and correct, and the sample output is unchanged. There are no must-fix items.

## Evidence

- Full suite on the exact branch tree (HEAD = c8f4b90, Python 3.11.18),
  `python3 -I -m unittest discover -s tests -t . -v` from the product folder: `Ran 169 tests in 0.212s` / `OK`.
- Sample CLI (`--workers samples/workers.csv`): `5 leave weeks checked, 4 exceptions`. `exceptions.csv` and
  `report.md` are byte-identical to the output of `main` before T-117 (W002 +80.00, W003 -10.00, W004 +50.00
  `shortened`, W005 +15.00).
- Mutations (each applied alone to a copy of the tree, full suite run):

| Mutation | Result |
|---|---|
| M1 rollback does not restore from backup | killed |
| M2 new file not removed when there was no previous one | killed |
| M3 backups not cleaned up | killed |
| M4 range step 14 days | killed |
| M5 `if gaps:` instead of `is not None` | killed |
| **M6 copy fallback replaced by `raise`** | **killed** (previously survived) |
| M7 final `raise` after rollback removed | killed |
| N1 `except OSError` only (NotImplementedError not caught) | killed |
| N2 interrupt converted to OSError | killed |
| N3 stderr note removed | killed |
| N4 `add_note` call removed | **survived**, see suggestion 1 |
| N5 backup deleted on failed rollback (T-117 fix reverted) | killed |

## Critical issues

None.

## Suggestions (non-blocking)

1. **The `add_note` assertion is conditional, so N4 survives.** In
   `test_interrupt_with_failed_rollback_reraises_interrupt_and_keeps_backup`, `if hasattr(cm.exception, "__notes__")`
   is false when the note was never added, so the assertion is skipped. On 3.11+ assert it unconditionally, for
   example `if sys.version_info >= (3, 11): self.assertIn("kept at", "\n".join(cm.exception.__notes__))`.
2. **Duplicate message text.** `report/builder.py` builds `note` and then rebuilds the same string in the
   `raise OSError(...)` line. Use `raise OSError(f"{exc}; {note}") from exc` so the two cannot drift apart.
3. **The note appears twice on an interrupt.** It is printed to stderr and again as a traceback note, because
   `audit.py` does not catch KeyboardInterrupt. The builder flagged this. It is acceptable because naming the backup
   matters more than tidy output. Optionally, catch KeyboardInterrupt in `audit.py` and exit 130 with the message
   once.
4. **`print` in library code.** `_atomic_write_pair` now writes to stderr directly. That is fine for a CLI-only tool.
   If the builder is ever used from a web service, move this to `logging`.

## Checks with no findings

- The interrupt path keeps the backup (`leftovers.remove(backup)` runs before the type check), and the bare `raise`
  re-raises the original interrupt with its traceback.
- `except (OSError, NotImplementedError)` wraps only the `os.link` call. A failure in `copy2` still propagates and the
  folder stays unchanged (re-probed).
- Security and performance: unchanged from T-117. No new inputs, and the added work runs only on the failure path.
