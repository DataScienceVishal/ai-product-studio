# Review: p/_starter/T-78-mock-portal-scheme (HEAD 9ca11e6)

**Verdict: PASS**

## Summary
One commit, 2 files, +31 lines. `mockPortalPath` (`frontend/src/pages/app.tsx` lines 156-165) now returns null unless the
resolved URL protocol is `http:` or `https:`. A `javascript:`, `data:` or `blob:` URL therefore goes to `safeRedirect`,
which refuses it with BAD_REDIRECT. This closes suggestion N2 of T-77-review.md. The new tests in `billing.test.tsx`
(lines 233-260) cover N3: a hostile-origin https URL is reduced to the in-app path, with origin and hash dropped and no
`location.assign`, and the three non-http schemes show the "unexpected billing link" alert with no navigation.

The tests check behaviour and catch the regression. Under Node's WHATWG URL, `javascript:/billing/mock-portal?c=1`,
`data:...` and `blob:...` all resolve to pathname `/billing/mock-portal`. Without the fix they would call `pushState`
and the new tests would fail.

## Evidence (exact tree 9ca11e6, separate worktree)
| Check | Result |
|---|---|
| Backend `python -m pytest` (Python 3.12, PostgreSQL 16.15, own database `starter_t78`) | **563 passed, 0 skipped**, 61.6 s (frontend `dist/` built, so the SPA test ran) |
| `alembic upgrade head && alembic check && alembic downgrade base` | clean, "No new upgrade operations detected" |
| Frontend `npx vitest run` | **6 files, 153 tests passed** (149 before, +4) |
| Frontend `npm run build` | succeeds: JS 250.94 kB (77.28 kB gzip), CSS 13.62 kB |

Not run: `infra/test-db-setup.sh`, Docker image job, pip-audit, e2e. The branch is frontend-only and does not touch them.

## Critical issues
None.

## Suggestions (non-blocking)
- **S1 Indentation.** The new `it(...)` blocks (billing.test.tsx line 233 onward) are indented 2 spaces. The preceding
  `it.each` body is indented 4. Cosmetic only; Prettier would fix it if it is adopted.
- **S2 Clearer test name.** "hostile-origin https url" maps to the in-app path by design (only the path is used). Saying so
  in the test name ("origin is ignored by design") would stop a reader thinking it is a bug.

Security: no new attack surface. Performance and AI cost: not affected.
