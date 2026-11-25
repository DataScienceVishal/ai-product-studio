# Review: p/_starter/T-77-redirect-review

- Branch: `origin/p/_starter/T-77-redirect-review`, HEAD `c09fbca`, one commit on top of `origin/main` (merge-base is main).
- Scope: S1, S3, S4, S5 and S6 from `reviews/T-76-review.md`. S2 (host allowlist) was declined on purpose, and this review accepts that.
- Reviewer: reviewer agent, 2026-11-25.

## Verdict: PASS

No blocking issues. The redirect guard now follows exactly the URL it checked. Its comment now describes what the code
really does. The mock-portal shortcut cannot leave the SPA or run script. The UI verification gate now uses the same
rule as `deps.verified_owner`.

## Test evidence (exact branch tree, git worktree at c09fbca)

| Check | Result |
|---|---|
| Backend `python -m pytest` (Python 3.12, pinned hash-checked `requirements-dev.txt`, PostgreSQL 16.15, own database `starter_t77`) | **562 passed, 1 skipped**, 1 warning, 57.6 s. The skip is `tests/test_spa.py:103` ("frontend not built"). |
| `tests/test_spa.py` re-run after `npm run build` | 115 passed, so the skipped test also passes once `dist/` exists |
| `alembic upgrade head && alembic check && alembic downgrade base` | clean, "No new upgrade operations detected" |
| Frontend `npx vitest run` | **6 files, 149 tests passed** |
| Frontend `npm run build` (`tsc -b && vite build`) | succeeds: JS 250.89 kB (77.27 kB gzip), CSS 13.62 kB |

Not run: `infra/test-db-setup.sh`, the Docker image job, and `pip-audit`. This branch does not touch them.

## What changed and how it was checked

### Redirect guard (`frontend/src/redirect.ts`): S1, S3
- `window.location.assign(target.href)` sends the browser to the parsed, normalised URL, so what was checked is what
  is followed (S3). The test `navigates to the parsed, normalised href` pins this with the cases
  `HTTPS://Billing.Stripe.Example:443/p/1` -> `https://billing.stripe.example/p/1` and the space -> `%20` case.
- The comment is now accurate. It says protocol-relative and backslash URLs inherit the page's scheme. On https they
  are followed like any https URL, which is a scheme guarantee and not a host allowlist. On an http origin they are
  refused. The tests cover both origins:
  - **http origin**: `javascript:`, `http://evil`, `//evil` and `data:` are refused. A comment explains why `//evil`
    is refused only on http.
  - **https origin**: `//evil.example`, `/\evil.example` and `\\evil.example` are followed as `https://evil.example/`.
    `JAVASCRIPT:`, a leading space, `java\tscript:`, a leading NUL, `http:evil.example`, `http://evil` and `data:` are
    all refused.
  
  I checked these against WHATWG URL parsing. The parser strips leading C0 controls and spaces and removes tabs, so
  all three `javascript:` variants parse to the `javascript:` protocol and are refused. `http:evil.example` against an
  https base becomes `http://evil.example/` and is refused. All of this matches the tests.

### In-app mock portal (`frontend/src/pages/app.tsx` `mockPortalPath`): S4
- The portal URL is parsed against `window.location.origin`. Only when `pathname === "/billing/mock-portal"` exactly
  does the code call `navigate(pathname + search)`. Otherwise it falls through to `safeRedirect`.
- Abuse analysis. I ran the same function in Node on hostile inputs:
  - `https://evil.example/billing/mock-portal?customer=<script>x</script>#h` gives
    `/billing/mock-portal?customer=%3Cscript%3Ex%3C/script%3E`. The origin and hash are dropped, and the search is
    percent-encoded by the parser.
  - `//evil/billing/x/../mock-portal?a="q` gives `/billing/mock-portal?a=%22q`. Dot segments are normalised before
    the comparison.
  - `/billing/mock%2Dportal`, a trailing slash and a different case all give `null`, so they fall through to
    `safeRedirect`.
  - `javascript:/billing/mock-portal` and `data:/billing/mock-portal` give `/billing/mock-portal`. The scheme is
    thrown away and only a same-origin path reaches `history.pushState`, which never runs script. This is harmless.
    See nit N2.
- The value passed to `navigate` always starts with the literal `/billing/mock-portal`. It can never be `//host`,
  and `pushState` cannot change origin, so the path stays in the app. The worst a hostile or misconfigured provider
  can do is show the mock page, which is safer than following its URL.
- `MockPortal` renders `customer` as a JSX text node. The new test with `?customer=<img src=x onerror=alert(1)>`
  checks that the text appears and no `<img>` is created (S6).
- Test: the in-app navigation is exercised with both the absolute `http://localhost:5173/...` URL from a `:4173`
  origin and the relative path. It asserts `pushState` is called with the path and `assign` is never called.
  `restoreMocks` and `unstubGlobals` are set in `vitest.config.ts`, so the stubs do not leak into other tests.

### `email_verification_required` in `/me` (`backend/app/routes/auth.py`, `team.py`): S5
- `me_payload(db, user, tenant, request)`. I grepped every caller. All four were updated: signup, login, `/me`, and
  team accept. The value is `bool(settings.require_email_verification)`, which is the same setting
  `deps.verified_owner` reads.
- Exposing this flag to an authenticated user is not sensitive.
- The backend test checks both values. The `app` and `settings` fixtures are function-scoped, so changing the
  setting inside one test does not leak into others.
- The `Me` type and `makeMe` were updated. `tsc -b` passes, so no other place builds a `Me` object without the new
  field.

### UI gating (`Billing`)
- `blocked = email_verification_required && !email_verified` is the same predicate as the server's.
- Manage billing is `disabled={blocked}`. Choose is `disabled={!isOwner || blocked}`. The hint shows only for owners
  who are blocked. Both endpoints (`/checkout` and `/portal`) depend on `verified_owner`, so the server still enforces
  the rule whatever the UI shows.
- The tests cover all four combinations of required and verified, for both buttons and the hint.
- Rollout skew: if the field were missing, `blocked` would be falsy and the buttons would be enabled, and the server
  would still refuse the action. Frontend and backend ship as one image, so skew is not a practical concern.

## Critical issues

None.

## Suggestions (non-blocking)

- **N1 Comment wording** (`redirect.ts` line 4). "a plain-http URL on another host" should say "on another
  origin". `http://localhost:5173` seen from `http://localhost:4173` is the same host but a different origin, and it
  is refused.
- **N2 Scheme check in `mockPortalPath`** (`app.tsx` lines 156-163). Consider requiring
  `target.protocol === "http:" || target.protocol === "https:"` before matching the path, so `javascript:` and
  `data:` inputs are rejected outright instead of being silently turned into the in-app path. This is not
  exploitable today because only the path is used. It makes the intent obvious to the next reader.
- **N3 Test the abuse case.** Add a cross-origin hostile entry to the `it.each` in "mock portal in-app navigation",
  for example `https://evil.example/billing/mock-portal?customer=x#frag`, and assert it goes to
  `/billing/mock-portal?customer=x` with no `assign`. Also add one near-miss, such as `/billing/mock-portal/` or
  `/billing/mock-portal-x`, that must go through `safeRedirect`. This pins the exact-match rule.
- **N4 Pre-existing, outside this diff.** `safeRedirect` follows any same-origin URL whatever its scheme, for example
  `blob:https://app.example.com/...`. This cannot be exploited without script already running in the origin. If you
  touch the guard again, limit the same-origin branch to `http:` and `https:`.
- **N5 Style** (`backend/tests/test_verification.py` lines 89-91). There are three blank lines before the new test
  (PEP 8 E303). CI has no lint step, so this is cosmetic.
- **N6 Consistency.** `VerifyBanner` still shows to unverified users when verification is not required. That is
  fine as information, but the wording could say verification is optional in that mode. This is dev-only.
