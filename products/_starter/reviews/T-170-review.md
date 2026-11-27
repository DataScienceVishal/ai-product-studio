# Review: p/_starter/T-170 (70687a9 vs main)

Reviewer run, 2026-11-27. Scope: test-only change closing the four nits in `T-169-review.md`
(`backend/tests/test_ai.py` +27/-3, README count 734 -> 735). No app code touched.

## Verdict: PASS

## Evidence

- Full backend suite on the branch tree (separate worktree, real Postgres): **735 passed, 1 skipped in 97.68s**, rc=0.
  Matches the README.
- `event.remove(app.state.db.engine, "before_cursor_execute", on_execute)` in `finally`: it would raise if the
  listener were not registered, and the suite is green, so it is paired correctly.
- `baseline == 1` holds (suite green); the later equality asserts still carry the behaviour.

### Mutants on `routes/notes.py::summarize` (statement executed on `db` just before `ensure_ai_enabled`, then reverted)

| Statement injected | Notes-route spy test |
|---|---|
| `UPDATE notes SET title = title WHERE id = :i` | FAILS (`sql_wrote` True) |
| `  update notes set ...` (lowercase, leading spaces) | FAILS |
| `WITH x AS (SELECT 1) UPDATE notes ...` | FAILS (missed before T-170) |
| `with d as (delete from notes ... returning id) select count(*) from d` | FAILS (missed before T-170) |
| `SELECT title FROM notes WHERE id = :i` (control, no write) | passes: no false positive, and the `in_transaction()` path is exercised with a real open transaction |
| `UPDATE ...; db.commit()` | passes on branch **and on main**: pre-existing gap, not a regression (see S1) |

### `_is_write_sql` regex, checked directly

- Catches: upper/lowercase, leading whitespace/newlines, `MERGE`, `WITH [RECURSIVE] ... INSERT/UPDATE/DELETE`.
- No false positive on: `SELECT 'update' FROM t`, `SELECT updated_at ...` (`\b` stops `updated_at`),
  `WHERE x = 'delete'`, `WITH x AS (SELECT updated_at ...) SELECT ...`, `SELECT ... FOR UPDATE`.
- False positive only inside a `WITH` that mentions the word (`WITH x AS (SELECT 'delete') ...`,
  `... FOR UPDATE` inside a CTE). Fails loudly, as the docstring says; acceptable for a spy.
- False negative on a leading comment (`/* c */ UPDATE`, `-- c\nDELETE`) or a parenthesised statement, and on
  `TRUNCATE`. SQLAlchemy and this codebase emit none of these, so not a real gap today.

### `in_transaction()` short-circuit

A write on a Session autobegins a transaction, so the only way to have written and see `in_transaction()` False is
a commit or rollback before `ensure_ai_enabled`. Rolled-back writes are gone; committed ones cannot be committed
again by the retry. Before T-170, `db.connection()` after a commit returned a fresh `Connection` not in
`sql_writes`, so that case was already invisible (mutant above survives on main too). The short-circuit hides
nothing new and removes the probe's side effect.

## Critical issues

None.

## Suggestions (non-blocking)

1. S1: raw-SQL write followed by `db.commit()` before `ensure_ai_enabled` is not caught (pre-existing). If it
   matters, track writes per Session via `after_execute`/`do_orm_execute` instead of per Connection. Low value now.
2. `test_ai.py` ~line 1804: the new comment hangs off `"flushed": db in wrote,` with one space before `#` and
   runs past the file's usual width; move it to its own line above the dict.
3. `import re` was added above `import json`; keep stdlib imports alphabetical.
