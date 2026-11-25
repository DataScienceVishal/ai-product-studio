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
