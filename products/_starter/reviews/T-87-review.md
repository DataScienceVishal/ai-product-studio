# T-87 review: starter leftovers (T-86 bugs 4 to 8)

Branch `p/_starter/T-87-leftovers`, head 7b35ff6 (code commit 429d69d), against `main`. Reviewer, 2026-11-25.

## Verdict: CHANGES

One required change (R1, a small one): a note whose Details box holds only whitespace, such as a stray newline, can no longer be saved, and the UI shows only "Some fields need fixing." Everything else is correct, and I found no security issue. `redirect_slashes=False` breaks no route, no probe and no e2e path (checked below).

## Evidence (run by the reviewer on 7b35ff6, in a separate worktree)

- Backend: Python 3.12 venv, local Postgres 16, `python -m pytest` in `backend/` gives `591 passed, 1 skipped, 1 warning in 89.46s`. `tests/test_t87_leftovers.py tests/test_spa.py` gives `140 passed, 1 skipped`.
- Frontend `npm test`: `Test Files 7 passed (7)`, `Tests 186 passed (186)`.
- `npx tsc --noEmit`: exit 0.
- `npm run build` (tsc -b plus vite build): `dist/assets/index-C_R-fzmT.js 252.59 kB │ gzip: 77.72 kB`, `✓ built in 195ms`.
- Browser e2e (Playwright) was not run. That matches the build report.

### Probe with the built SPA mounted (FRONTEND_DIST set, TestClient, follow_redirects=False; a temporary test file, now deleted)

| Path | Result |
|---|---|
| `/healthz`, `/livez`, `/api/config`, `/api/docs` | 200 |
| `/healthz/`, `/livez/` | 404 HTML (was a 307). The Dockerfile HEALTHCHECK, the bicep readiness probe (`/healthz`), `infra/smoke.sh` and `scripts/e2e.sh` all use the exact paths, so nothing depends on the slash form. |
| `/login/`, `/settings/`, `/billing/done/` | 200 HTML (the SPA fallback strips the trailing `/`, and the frontend `normalise()` does too, so these still render their pages) |
| `/api/notes/`, `/api/config/`, `/api/docs/` | 404 JSON, no Location header |
| `/assets`, `/assets/` | 404, no redirect (explicit routes in spa.py, unchanged) |
| `/x/` | 404 HTML, which renders the new Page not found view |

No route is declared with a trailing slash: every collection route uses `""` under its prefix (`notes.py:58,66`, `team.py:51`, `account.py:56`). No `fetch` in `frontend/src` and no request in `tests/e2e` or `infra` uses a slash-suffixed API path (grep).

### Body and title edge cases (probe)

- Body `"   "`, `"\n\n"`, `" "`, `"　"`, `"​\n​"` all give 422. `"a​"` gives 201 and is stored untouched. Updating an existing note with a PUT whose body is `"   "` gives 422.
- Title `"　"`, `"\xa0"`, `"᠎"`, `"\U000e0020"` give 422. Hangul fillers `U+115F` and `U+3164` and braille blank `U+2800` still give 201. Those are Lo/So characters, not Cf, so they are outside bug 4's scope (S3).
- Malformed JSON (`{"title": `, a trailing comma, invalid UTF-8 `\xff\xfe`) gives `fields: [{"field": "", "problem": "The request body is not valid JSON."}]`. A JSON array body gives `field: ""` with the pydantic dict message, as before.

## Required

### R1. A whitespace-only note body is now refused, which breaks a normal UI flow. `backend/app/textsafe.py` (`NoteBody`, `_not_invisible`)

- What happens: before this branch, a body of `"   "` or `"\n"` was accepted. Now it is a 422. The dashboard form (`frontend/src/pages/app.tsx:64`) sends `body` exactly as typed, and `errorText` (`app.tsx:11`) shows only `err.message`. So a user who types a title and leaves a stray Enter or space in Details sees "Some fields need fixing." with no hint which field, and the note is not saved. An API client resending an older note's whitespace body on PUT (full replace, `notes.py:82`) now fails as well.
- Why it matters: the body is optional, so "nothing typed" should behave like an empty body, not like an error. The title is required, so a blank title giving a 422 is right. The two are different cases, and the bug hunt asked only that invisible-only text not be stored as if it had content.
- Fix: normalise instead of refusing. Give `NoteBody` a `BeforeValidator` that returns `""` when `_invisible(value)` is true and the value unchanged otherwise (no strip of real text, so ZWJ and ZWNJ survive), then the `_TEXT_BAD` check. Drop `_not_invisible`. In `test_t87_leftovers.py`, change `test_invisible_only_body_is_422_but_empty_body_is_fine` to assert 201 with `body == ""` for each INVISIBLE value. Add one case for `"   "` and `"\n"`, which are not in the INVISIBLE list, because they were the regression. This also removes the need for a new error message.

## Suggestions (not blocking)

- **S1, back-button trap, `App.tsx` (new effect, line 37).** `navigate("/")` uses `pushState`, so history becomes `[X, /login, /]`. Pressing Back lands on `/login`, which pushes `/` again, and the user can never go back past `/login`. A redirect should replace the history entry: add a `replace` option to `navigate` (`history.replaceState`) and use it here. The same applies to the existing signed-out `navigate("/login")` on line 33, which predates this branch.
- **S2, `?next=` is ignored when already signed in.** A signed-in user opening `/login?next=/billing`, for example from a stale tab or a bookmarked deep link, lands on `/` instead of `/billing`. `navigate(safeNext())` instead of `navigate("/")` would honour it, and `safeNext` already validates the target.
- **S3, other blank-looking characters.** The company name (`auth.py:48-53`, `" ".join(...split())`) still accepts a name made only of U+200B. Titles still accept Hangul fillers U+115F, U+1160 and U+3164, and braille blank U+2800. Consider one shared `is_blank()` covering Cf plus those few known filler code points, used by `StrippedLine`, `NoteBody` and `_company`.
- **S4, `errors.py:43`, latent mislabel.** The second clause, `len(loc) == 2 and loc[0] == "body" and isinstance(loc[1], int)`, would also match a genuine item error at index N if a future product declares a list body (for example `items: list[Item]` as the whole body), and would call it "not valid JSON". `e.get("type") == "json_invalid"` alone covers FastAPI's JSON decode error, so drop the int clause.
- **S5, process.** The branch carries a `state/DECISIONS.md` append. CLAUDE.md section 9 says state files go straight to `main`. Since main's log keeps growing, expect a merge conflict there. Keep both sides when merging.
- **S6, cosmetic.** `if (me && signInPage) return null;` gives one blank frame before `/` renders. That is acceptable: there is no SignIn flash and no loop, because `/` is not a sign-in page and SESSION_ENDED sets `me` to null before it navigates to `/login`.

## Checked and fine

- ASCII email (`auth.py:33`): the check runs after `strip().lower()` and before the regex. It applies to signup and invitations (both use `Email`). Login and reset-request still take any string and simply do not match (401 or 202). Fullwidth `ｕ` and IDN domains are refused with a clear message.
- `StrippedLine` change: non-blank text is only `.strip()`ped as before, and inner ZWJ and ZWNJ are kept (tested). `all()` short-circuits on the first visible character, so the cost on a 20k body is negligible.
- App.tsx routing: there is no redirect loop. Loading shows "Loading…" until `/api/auth/me` resolves. Signed-out unknown paths still go to `/login`. Signed-in unknown paths render NotFound inside the Shell with the URL kept. `/` still renders the Dashboard. Sign-in and sign-up still `navigate` synchronously after `onSignedIn`, so the new effect does not override `safeNext()`.
- Security: no new endpoint and no authorization change. The 404 replaces a 307 whose Location was built from the Host header, so this branch removes that open-redirect and mixed-content hazard. Nothing user-controlled reaches the new error text.
- Tests check behaviour (status codes, stored values, URL, rendered headings), not implementation details.
