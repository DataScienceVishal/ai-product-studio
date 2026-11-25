# Review: p/_starter/T-89 (head 1b154b1)

Reviewer: reviewer agent, 2026-11-25. Diff: `git diff main...p/_starter/T-89` (3 files, +6 / -5). Checked in a separate worktree, detached at 1b154b1.

## Verdict: PASS

## Summary

T-89 applies suggestions 1 to 3 from `T-88-review.md`:

1. `App.test.tsx:150`: the loose `findAllByText(/note/i)` is now `findByRole("heading", { name: "Your notes" })`. That heading is the dashboard's `<Card title="Your notes">` (`pages/app.tsx:126`), which `Card` renders as an `<h2>` (`ui.tsx:100`).
2. `pages/auth.tsx:6`: `SIGN_IN_PAGES` is now exported as `ReadonlySet<string>`, and it has a doc comment. `App.tsx:36` uses `SIGN_IN_PAGES.has(path)`, so the list lives in one place.
3. `App.tsx:42`: there is a comment on `return null` explaining that it lasts one frame and why that is safe.

## Behaviour unchanged

- The old check was `path === "/login" || path === "/signup"`. `SIGN_IN_PAGES` holds exactly those two strings, so `Set.has` gives the same result for every string.
- `path` comes from `usePath()`, which applies `normalise(window.location.pathname)` both at init and on popstate (`ui.tsx:26-32`). The comment "path is already normalised by usePath" is accurate.
- `ReadonlySet` is a type-only change, so runtime behaviour is unchanged. `safeNext` (`auth.tsx:16`) still uses the same set.
- The new comment on `return null` is correct. The effect at `App.tsx:37-39` always calls `navigate(safeNext(), true)`, and since T-88 `safeNext` never returns a sign-in page.

## Evidence

| Check | Result |
|---|---|
| `npm ci` | exit 0 |
| `npm test` | `Test Files 7 passed (7)`, `Tests 201 passed (201)` (same count as T-88) |
| `npx tsc --noEmit` | exit 0 |
| `npm run build` | `built in 210ms`, exit 0 |
| Mutation: drop `/signup` from the set used in `App.tsx` | 2 tests fail (`sends /signup to the dashboard`, `/signup?next=/login/`). The shared set is exercised. |
| Mutation: rename the dashboard heading to "Notes" | 4 tests fail (all 4 `it.each` cases). The stricter assertion really checks that the dashboard rendered. |

Both mutations were reverted, and the worktree was clean afterwards. I did not run the backend suite because no backend files changed; the lead runs it.

## Critical issues

None.

## Suggestions (not blocking)

- When the dashboard heading text changes, this test must change with it. That is acceptable, and it is the point of the stricter check.
- S5 from T-87 still applies when merging: keep both sides of `state/DECISIONS.md`.

## Round 2: head c7bc6dc

My Round 1 PASS at 1b154b1 was wrong. I did not run `tests/test_spa.py`, and it fails there. `test_client_routes_match_the_frontend_router` (`backend/tests/test_spa.py:567-573`) reads the client routes out of the `path === '/x'` comparisons in `App.tsx`, and it rejects any other kind of path check, such as `.has(path)`. Lesson: I will run `test_spa.py` on any change to `App.tsx` routing, even when no backend files changed.

### Verdict: PASS

### What changed since 1b154b1

- **`App.tsx:36-37`.** This goes back to `path === "/login" || path === "/signup"`. The comment says to keep it in step with `SIGN_IN_PAGES` and gives the reason for using `===`.
  - This is the exact behaviour `main` had.
  - The `SIGN_IN_PAGES` import is removed from `App.tsx`.
- **`App.test.tsx:144-150`.** A new `it.each([...SIGN_IN_PAGES])` checks each page. For each one, a signed-in user must end up on `/`, and the "Your notes" heading must render.
  - This replaces the shared constant as the guard against the list and `App.tsx` drifting apart.
- **`SIGN_IN_PAGES` stays exported from `pages/auth.tsx:6`.** It is still used by `safeNext`.

### Evidence (separate worktree, detached at c7bc6dc)

| Check | Result |
|---|---|
| `npm ci` | exit 0 |
| `npm test` | `Test Files 7 passed (7)`, `Tests 203 passed (203)` (201 plus the 2 new drift cases) |
| `npx tsc --noEmit` | exit 0 |
| `npm run build` | `built in 192ms`, exit 0 |
| Backend `pytest -q -o addopts="" tests/test_spa.py`, using the main checkout's `.venv` and local Postgres | `115 passed, 1 warning in 7.24s`. I confirmed that `app` imported from the worktree, and the test reads the worktree's `App.tsx` through `Path(__file__)`. |
| Mutation: add `/forgot-password` to `SIGN_IN_PAGES` only | 1 test fails: `sends a signed-in user away from /forgot-password (App.tsx signInPage matches SIGN_IN_PAGES)`. The drift test catches it. I reverted the change and the tree was clean afterwards. |

I did not run the full backend suite. The lead reports `604 passed` at this head.

### Critical issues

None.

### Suggestions (not blocking)

- **The drift test catches only one direction.** It fails when `SIGN_IN_PAGES` gains a page that `App.tsx` lacks. It does not fail when `App.tsx` gains a sign-in page that `SIGN_IN_PAGES` lacks. In that case `safeNext` could return that page. That would cost one extra redirect hop, not a blank page: the new URL has no `?next=`, so the second `safeNext()` returns `/`. This is acceptable; it is noted here for when a third auth page is added.
- **The branch has a copy of this review file committed.** The copy at c7bc6dc holds Round 1 only. When merging, use the main checkout's version, which includes this Round 2 section.
