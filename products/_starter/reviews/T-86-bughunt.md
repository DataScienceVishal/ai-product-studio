# T-86 bug hunt on products/_starter (QA, about 30 min)

Setup: API on :8086 (FakeAI, mock billing, email verification off), Vite dev on :5186, Python httpx probes, a Playwright browser run, and a throwaway pytest probe for concurrency and token reuse (removed after running).
Result: 3 UI bugs found and fixed (with regression tests), 5 low or cosmetic items left open, no 500s and no cross-tenant leaks found.
Tests after the fixes: frontend 169 passed (was 166, +3 in `frontend/src/pages/dashboard.test.tsx`, which fail without the fix), backend 564 passed and 1 skipped (unchanged code), `tsc --noEmit` clean.

## Bugs

| # | Severity | Bug | Status |
|---|---|---|---|
| 1 | Medium | Only the first 50 notes are ever shown. `GET /api/notes` pages at 50 and returns `total`, but `Dashboard.load` ignores it and has no way to load more, so note 51 onwards looks lost. `frontend/src/pages/app.tsx` (load, near line 22) | Fixed: "Show more notes (n of total)" button, de-duplicated |
| 2 | Low-Medium | A failed notes load (502, offline, 500) leaves "Loading…" on screen forever next to a generic error, with no retry. app.tsx near line 99 | Fixed: "We couldn't load your notes." with Try again |
| 3 | Low-Medium | Long unbroken text (a pasted URL, or a 150-character Arabic title) in a title, body or summary stretches the page: 65,190 px horizontal overflow at 320 px width, so the buttons are unreachable on mobile. app.tsx note `<li>` (`h3`, body `p`, summary `p`) | Fixed with `break-words` (jsdom test checks the class only; the real overflow was measured in Chromium) |
| 4 | Low | A title or body made only of zero-width characters (U+200B, U+FEFF) is accepted; it shows as a blank heading. `backend/app/textsafe.py` `StrippedLine` only strips whitespace | Open |
| 5 | Low | Signup accepts a non-ASCII (IDN) email such as `üser@exämple.com`; mail to it may not be deliverable, and the same address in different Unicode forms (NFC and NFD) counts as different accounts. `auth.py:30` EMAIL regex | Open, a decision for the product |
| 6 | Low | `GET /api/notes/` answers 307 to `http://localhost:8086/api/notes` (absolute http URL built from the Host header), which is a mixed-content hazard behind a proxy without forwarded headers. Starlette `redirect_slashes` | Open, set `redirect_slashes=False` or serve a 404 |
| 7 | Low | A malformed JSON body gives the field name `"1"` (the parser's byte offset) in the 422 `fields` list. The UI joins problems only, so it is cosmetic. error handler in `errors.py` | Open |
| 8 | Cosmetic | Signed in, `/login` still shows the sign-in form, and an unknown path such as `/does-not-exist` renders the dashboard with the URL unchanged. `frontend/src/App.tsx` | Open |

## Flows and edge cases tried (result)

API (httpx against the live app):
- Sign-up, duplicate email (also upper-case): 201 then 409. OK
- Login, logout, logout twice, old cookie after logout (401 "session has ended"), login with upper-case and padded email: OK
- Wrong password and unknown email give the same 401 message: OK
- NUL in login password, signup company name, login email: no 500. A NUL in the company name is turned into a space (201). OK
- Password too short (422), 257 characters (422), Hindi passphrase (201): OK
- Tenant isolation: tenant B's GET, PUT, DELETE and summarise on A's note all give 404; B's list is empty; B's mock checkout completion of A's session is 404; B revoking A's invitation and removing A's member are 404. OK
- Invitations: invite, self invite and existing account give 409, bad email 422, accept with a bad token 400. OK
- Concurrency (pytest probe): six simultaneous accepts of one invitation gave one 201; six simultaneous signups with one email gave one 201; four simultaneous password-reset confirms gave one 204 and sessions were revoked; a removed member's cookie gives 401 straight away. OK
- Mock billing: checkout, completion (repeated completion is idempotent), checkout when already active (409), portal without a customer (409), unsigned and bad-signature webhooks (400). OK
- AI with FakeAI: summary 200; 8 concurrent summaries all 200; the per-minute limiter returned 429 after 12 calls; usage endpoint counts tokens. OK (the daily and monthly token caps were not reached, the existing tests cover them)
- CSRF: POST without `X-Requested-With` gives 403 on /notes and /logout; GET without a session gives 401. OK
- Malformed JSON, text/plain, form body, array, `null`, empty body, an int or list title, lone surrogate, invalid UTF-8, 100,000 nested brackets: all 4xx, no 500. OK
- Note inputs: Hindi, Tamil, Urdu, 50 emoji, 200 and 201 character titles (the second gives 422), body of 20,000 and 20,001 characters (the second gives 422), RTL override, combining marks: accepted or refused cleanly (see bug 4 for zero-width).
- Query validation (limit 0, 101, -1, abc, offset 100001): 422. Bad UUID and `%00` in a path: 422. OPTIONS and PATCH give 405; `/docs` and `/openapi.json` are 404 (hidden). OK
- Odd bodies (empty, `{`, `[]`, `null`, null fields) on invite, checkout, reset request and account delete: none gave a 5xx. OK

Browser (Playwright Chromium):
- Sign-up with a Hindi company name plus 100 characters, double-clicking Create account: one account, lands on the dashboard. OK
- Double-clicking Save note: one note. Double-clicking Summarise: one summary, no error. OK
- Direct load and refresh of /billing, /team, /settings, /help: render. OK
- Session cookie cleared mid-use, then Save note: redirected to /login. OK
- Sign out, then Back button: stays on the login page, no protected content. OK
- Slow API (2.5 s): the Sign in button shows its busy state. OK
- Offline sign-out: clear message, and the user stays signed in. OK
- Two browser contexts (two tenants) side by side: B sees none of A's notes. OK
- No page errors in the console across the run. The 502 case led to bug 2.
- Not run: real email verification and invitation accept in the browser (covered by the existing e2e and backend tests), the mobile layout beyond the overflow check.
