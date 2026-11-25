# Review: p/_starter/T-88 (head 7bcf8ea)

Reviewer: reviewer agent, 2026-11-25. Diff: `git diff main...p/_starter/T-88` (5 files, +28 / -8). Checked in a separate worktree, detached at 7bcf8ea.

## Verdict: PASS

## Summary

T-88 fixes S7 and the Nit from `T-87-review.md`.

- **S7.** `safeNext()` (`frontend/src/pages/auth.tsx:8-19`) now returns `/` when the resolved `?next=` path, after `normalise()`, is `/login` or `/signup`. It is fixed in `safeNext` itself, so both callers are covered: the signed-in redirect effect in `App.tsx:38` and `SignIn`'s post-submit `navigate(safeNext())` (`auth.tsx:71`).
- **Nit.** `textsafe._invisible` is renamed to the public `is_blank`, and all three internal call sites plus the import in `routes/auth.py` are updated. No `_invisible` references remain in backend code. The only matches are test function names such as `test_invisible_only_*`, which are fine.

## Evidence

| Check | Result |
|---|---|
| `npm ci` | exit 0 |
| `npm test` | `Test Files 7 passed (7)`, `Tests 201 passed (201)` (was 190 on T-87, so 11 new) |
| `npx tsc --noEmit` | exit 0 |
| `npm run build` | `built in 191ms`, exit 0 |
| Backend `python -m pytest -q -o addopts=""` (local Postgres) | `604 passed, 1 warning in 89.00s` |
| New tests run against main's `auth.tsx` (branch tests kept) | `Tests 11 failed / 190 passed (201)`, `2 failed` files. So the tests catch the bug. |

## Correctness: can a signed-in user still reach a blank page through ?next=?

No. The check uses the same rule the router uses. `safeNext` tests `normalise(url.pathname)`, where `url` is the WHATWG-resolved URL, and `usePath()` uses `normalise(window.location.pathname)`. Those are the same function on the same resolved pathname. So whatever `safeNext` returns, the router cannot then see it as `/login` or `/signup`.

I ran a throwaway probe test in the worktree (deleted afterwards). It covered 22 inputs and asserted two things for each: the result is same-origin, and `normalise(pathname)` is not a sign-in page. All 22 passed:

- **Case:** `/Login`, `/LOGIN`. These pass through unchanged. The router is case-sensitive, so they render "Page not found" with a link home, not a blank page.
- **Percent-encoding:** `/%6Cogin`, `/login%2F`, `/%2e/login`, `/x/%2e%2e/login`, `/a/..%2Flogin`, `/login%00`, `/login%20`.
  - `/%2e/login` and `/x/%2e%2e/login` resolve to `/login`, and the result is `/`.
  - `%6C` and `%2F` are not decoded in either `URL` or `location.pathname`, so those paths go to "Page not found".
- **Hash and query:** `/login#x`, `/login/#x`, `/login?x=1` all give `/`, because the pathname is checked on its own and the hash is dropped. `/billing?next=/login` and `/billing#/login` give `/billing...`, which is a real page.
- **Whitespace stripped by the URL parser:** `/lo\tgin`, `/lo\ngin` give `/`.
- **Dot segments and trailing slashes:** `/./login`, `/login/.`, `/login/..`, `/signup/../login`, plus the branch's own `/x/../login`, `/login/`, `/signup//`. Each gives `/` or a non-sign-in page.
- **Other:** `/login;x` and `/ login` give "Page not found", not blank.

**Open-redirect safety is unchanged.** The guards that run first are untouched: the `/` prefix, no `//`, no backslash, the origin check and the `//` pathname check. The new branch can only turn an allowed result into `/`, so it can never widen what is allowed. The previous chained case `/login?next=/login?next=//evil.com` now lands on `/` (tested in `App.test.tsx`).

## Test quality

- `routing.test.tsx` adds 7 rejection cases. Each is a plain unit test of `safeNext`, and together they cover trailing slashes, a nested `next` and dot segments.
- `App.test.tsx` adds 4 end-to-end routing cases through `<App />`. They assert the final pathname is `/`, the search string is empty, and something renders, so the test proves the page is not blank, not just that the URL changed. That is testing behaviour, which is good.

## Critical issues

None.

## Suggestions (not blocking)

1. **`App.test.tsx`, new `it.each`.** The "dashboard renders" check is `findAllByText(/note/i)`. This is a loose match: any text containing "note" passes it. A role or heading query for the dashboard would be stricter, for example `findByRole("heading", { name: ... })`.
2. **Duplication.** The sign-in page list now lives in two places: `SIGN_IN_PAGES` in `auth.tsx:5` and `signInPage = path === "/login" || path === "/signup"` in `App.tsx:36`. If a third auth page is added, both must change together. Export `SIGN_IN_PAGES` and use `SIGN_IN_PAGES.has(path)` in `App.tsx`.
3. **`App.tsx:42` (`if (me && signInPage) return null`).** This line is now only a one-frame placeholder before the effect redirects. It is fine, but a short comment saying that the effect always leaves the page, because `safeNext` never returns a sign-in page, would explain why the blank render is safe.
4. **S5 from T-87 still applies when merging.** Keep both sides of `state/DECISIONS.md`.
