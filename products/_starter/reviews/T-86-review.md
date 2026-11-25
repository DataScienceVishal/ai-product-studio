# Review: p/_starter/T-86-bughunt (at 560a7ed)

Reviewer run, 2026-11-25. Diff: `git diff origin/main...HEAD`. Changed: `frontend/src/pages/app.tsx` (Dashboard), new `frontend/src/pages/dashboard.test.tsx`, `reviews/T-86-bughunt.md`.

## Verdict: CHANGES

The three fixes are mostly right and the retry and wrap fixes are clean. One bug introduced by the paging fix is easy to reproduce: deleting a note from a fully loaded list shows a "Show more notes" button that does nothing useful. The fix is one line plus a test. There are also two smaller races in load-more.

## Evidence

- `npx vitest run`: **176 passed (176)**. `npm run build`: built OK (251.97 kB JS). node_modules is a symlink to the main checkout. package-lock.json is identical in both, so `npm ci` was not needed.
- Backend contract (`backend/app/routes/notes.py:59-63`): `GET /api/notes?limit=50&offset=N`, ordered `created_at DESC`, returns `{items, total}` with `total` counted per tenant. The frontend sends `offset=notes.length` with the default limit of 50 and stops when `notes.length >= total`. That matches the backend. Deletes are applied locally, so the server list and `notes.length` both shrink by one and the next offset still lines up (checked by hand). New notes trigger a full `load()`. Duplicates from concurrent inserts are filtered out by id.
- Mutation checks (each run against `dashboard.test.tsx`, then reverted with `git checkout`):

| Mutation | Result |
|---|---|
| Show-more button never rendered | killed (paging test fails) |
| offset always 0 | killed |
| loadFailed never set on error | killed (retry test fails) |
| Try again does not call load() | killed |
| title loses break-words | killed |
| body loses break-words | killed |
| loadMore does not update total | **survived** |
| id de-dup filter removed | **survived** |
| loadFailed never cleared on success | survived (harmless: the flag is only read while notes is null) |
| summary loses break-words | **survived** |

  Paging and retry regressions are caught, so the core of each fix is pinned. Same mutation method as above: removing the button or the failure state makes the 3 tests fail without the fix.

- Security: there is no new injection or XSS surface. Note text is still rendered as React text nodes, with no `dangerouslySetInnerHTML`. The offset is a number taken from an array length. No new endpoints.

## Critical issues

1. **Phantom "Show more notes" button after a delete.** `frontend/src/pages/app.tsx`: `remove()` (near line 95) filters the note out locally but never decrements `total`, and the button shows whenever `notes.length < total` (near line 144). A user with 3 notes who deletes one sees "Show more notes (2 of 3)". Clicking it fetches an empty page. It happens every time, on the most basic flow, in the product every studio product starts from. I reproduced it with a throwaway test: render with 3 of 3 notes, click Delete, and the Show more button is present (assertion failed).
   **Fix:** in `remove` after a successful DELETE, add `setTotal((t) => Math.max(0, t - 1))`. Add a regression test: delete from a fully loaded list and expect no Show more button.

## Suggestions (non-blocking, but worth doing in the same pass)

2. **Load-more can be clicked twice while in flight.** It shares the single `busy` slot. Clicking Summarise or Delete while load-more is pending sets `busy` to the note id and then to null, so the Show more button is enabled again before its request returns. I confirmed this with a probe: the button's `disabled` was `false` mid-flight. A second click sends the same offset. The de-dup filter keeps the list correct, but it costs a wasted request. Fix: use a separate `loadingMore` boolean, or an in-flight ref guard.
3. **Stale load-more after a reload can skip a note.** If `load()` runs while load-more is pending (Save note, Add samples, Try again), the late load-more response is appended to the fresh first page using the old offset. With 100 notes, saving one during load-more leaves the old S49 out of the list. If the stale response carries `total=100`, the button disappears and that note is unreachable until a refresh. The window is narrow. Fix: keep a generation counter in a ref, bump it in `load()`, and drop load-more responses whose generation is stale.
4. **Tests that would make the surviving mutants fail:** (a) a paging test where the second page's total differs from the first page's total (for example, total 3 to 2 after a concurrent delete), so a missing `setTotal` is caught; (b) a second page that repeats an id already shown, then assert the note appears once; (c) assert the summary `<p>` has `break-words`.
5. Minor: a Save note after load-more collapses the list back to the first 50. That's acceptable for now. If kept, a comment would help.
6. Backend (outside this diff): `order_by(Note.created_at.desc())` has no tie-breaker. Notes with equal timestamps (for example Add samples in one transaction) can come back in a different order on different pages, which gives duplicates (filtered out) or skips (not filtered). Add `Note.id` as a secondary sort key.

## Bug-hunt report

`reviews/T-86-bughunt.md` is thorough and honest about what was not run. The open items 4 to 8 are reasonable to queue. Its test count (169) is from before the origin/main merge; the merged branch has 176.

---

# Re-review at da5d327: PASS

Re-reviewed `git diff 209e0fe..da5d327`: `app.tsx`, `dashboard.test.tsx`, `backend/app/routes/notes.py` and `backend/tests/test_tenancy.py`.

## Evidence

- Frontend: `npx vitest run` gives **182 passed (182)** across 7 files. `npm run build` built OK.
- Backend: `pytest` on the full suite gives **566 tests, 0 failures, 0 errors, 0 skipped** (read from the junit XML; exit code 0).
- Frontend mutants, each run against `dashboard.test.tsx` and then reverted:

| Mutant | Result |
|---|---|
| Show-more never rendered / offset always 0 | killed (4 tests fail) |
| loadMore does not set total (previously survived) | killed ("trusts the total from the latest page") |
| id de-dup removed (previously survived) | killed ("shows a note once") |
| summary loses break-words (previously survived) | killed ("lets a long summary wrap") |
| loadFailed never set / Try again does nothing | killed |
| title or body loses break-words | killed |
| remove() does not decrement total (C1) | killed ("hides Show more after deleting") |
| Show-more `busy` forced false (#2) | killed ("keeps Show more disabled while it loads") |
| stale-page check removed / generation never bumped (#3) | killed ("drops a load-more response…") |
| `loadingMoreRef` early return removed | survived. Expected: the disabled button already blocks re-clicks in jsdom, and the ref only matters for two clicks inside one tick before React re-renders. Harmless defence in depth. |

- Backend mutant: dropping the `Note.id.desc()` tie-breaker makes `test_notes_with_the_same_timestamp_page_in_a_stable_order` fail (killed).

## Findings

- C1 is fixed. `remove()` now calls `setTotal((t) => Math.max(0, t - 1))`, and a regression test pins it.
- #2 is fixed. Load-more has its own `loadingMore` state, separate from `busy`, so Summarise and Delete no longer re-enable Show more while it is loading.
- #3 is fixed. `load()` bumps `generation`, and a load-more response from an older generation is dropped. The button then reappears with the correct offset.
- #4 is done: all three mutants that survived before are now killed.
- #6 is fixed: the backend orders by `created_at DESC, id DESC`, so paging is stable.
- Security: no new surface. The backend change only alters the ORDER BY of a query that is already scoped to the tenant.

## Remaining (non-blocking)

- Narrow window: a load-more that starts after `load()` has begun but before it resolves captures the new generation, so it is not dropped. It would use the old `notes.length` as its offset. The cause is the same as #3 and the window is much smaller. It could be closed by also disabling Show more while `load()` is in flight.
- Item 5 is unchanged: Save note collapses the list back to the first 50. Acceptable for the starter.
