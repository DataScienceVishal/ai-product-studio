# T-87 build: leftovers from the T-86 bug hunt (bugs 4 to 8)

Branch `p/_starter/T-87-leftovers` (from main, not merged). Code commit: 429d69d (this report is committed on top; no code changed after it).

## Changes
| # | Change |
|---|---|
| 4 | `backend/app/textsafe.py`: title blank check (`StrippedLine`) treats text of only whitespace and Unicode category Cf characters (U+200B-U+200D, U+2060, U+FEFF, soft hyphen, ...) as empty, so min_length gives the usual 422. New `NoteBody` type for note bodies: empty body still allowed, but a non-empty body of only whitespace and Cf characters is a 422. Non-blank text is stored untouched (ZWJ in emoji, ZWNJ in Persian kept). Note: a whitespace-only body (e.g. "   ") is now also a 422; it was accepted before. |
| 5 | `backend/app/routes/auth.py` `_email`: non-ASCII gives 422 "Use an email address with only standard (ASCII) characters." Applies to signup and invitations (both use `Email`). Login and password-reset request use a plain string, so a non-ASCII email just gives the normal 401 / no match. |
| 6 | `backend/app/main.py`: `redirect_slashes=False`. `/api/notes/` is a JSON 404, no Location header. SPA client routes with a trailing slash still serve the app (the 404 fallback handles them). No slash-suffixed API paths in `frontend/src` or `tests/e2e`. |
| 7 | `backend/app/errors.py`: JSON syntax errors (`json_invalid`, loc `("body", <int>)`) report `{"field": "", "problem": "The request body is not valid JSON."}`. |
| 8 | `frontend/src/App.tsx`: signed-in user on /login or /signup is sent to `/`; unknown paths render a "Page not found" page (link "Go to your notes") inside the shell. `spa.py` docstring updated. |

## Tests added (each fails without its fix; checked by reverting app code, 3 of 3 frontend and the backend file failed)
- `backend/tests/test_t87_leftovers.py`: 26 tests (invisible-only title create/update, body, ZWJ/ZWNJ kept, non-ASCII signup x4, invitation, login 401, slash 404, malformed JSON, missing field still named).
- `frontend/src/App.test.tsx`: 4 tests (/login and /signup redirect x2, Page not found, dashboard still at /).

## Full suites on the final tree
- Backend (Postgres 16 local, `python -m pytest` in products/_starter/backend): `591 passed, 1 skipped in 78.92s` (was 564 + 1 skipped in T-86 report).
- Frontend `npm test`: `Test Files 7 passed (7)`, `Tests 186 passed (186)` (was 169).
- `npx tsc --noEmit`: exit 0. `npx tsc -b` (the build typecheck): exit 0.

## Risk for the reviewer
- Whitespace-only note body is now refused (behaviour change in 4).
- Not run: browser e2e (Playwright), the production `vite build`.

## Round 2 (reviewer CHANGES R1, S1 to S4)

Changes:
- R1: `NoteBody` now uses a `BeforeValidator` that turns a whitespace/invisible-only body into `""` (201 on POST, 200 on PUT); real text is untouched. `_not_invisible` removed. Tests now expect 201 and body `""` for the INVISIBLE list plus `"   "`, `"\n"`, U+200B.
- S1: `navigate(to, replace=false)` in `ui.tsx`; the signed-in `/login`,`/signup` redirect and the signed-out `/login` redirect use `replaceState`. Tests assert `pushState` is not called.
- S2: signed-in user on `/login?next=/billing` goes to `safeNext()` (tests: `/billing`, and unsafe `//evil.com` falls back to `/`).
- S4: `errors.py` detects malformed JSON by `type == "json_invalid"` only. Test uses a `list[Item]` body app: item error at index 1 keeps field `1.n`; a real syntax error still says not valid JSON.
- S3: U+115F, U+1160, U+3164, U+FFA0, U+2800 count as blank in `_invisible` (titles, bodies). Signup company name uses the same check. Tests added for both.

Results on the final tree:
- Backend `pytest` (local Postgres 16): `604 passed, 1 warning in 85.66s` (no skips this run).
- Frontend `npm test`: `Test Files 7 passed (7)`, `Tests 190 passed (190)`.
- `npx tsc --noEmit`: exit 0.
- `npm run build`: `dist/assets/index-BiEA8UW7.js 252.64 kB │ gzip: 77.73 kB`, `✓ built in 214ms`.
