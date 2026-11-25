# Review: p/_starter/T-76-portal-followups (696786d)

Reviewer verdict: **PASS** (no critical issues; suggestions below are for a later slice)

## Summary

Implements the T-75 review suggestions: a `/billing/mock-portal` page (frontend route plus `CLIENT_ROUTES` in
`backend/app/spa.py`), `safeRedirect()` in `frontend/src/redirect.ts` guarding the checkout and portal redirects, and
Manage billing disabled (with a hint) for owners whose email is not verified.

Tests on the exact branch tree (HEAD 696786d):

- backend `pytest`: **562 passed** (0 failed), including `test_client_routes_match_the_frontend_router`, which
  confirms `App.tsx` and `CLIENT_ROUTES` agree on the new route.
- frontend `npx vitest run`: **131 passed (131)**.
- `npm run build`: OK (250.69 kB JS, 77.22 kB gzip).

## Redirect guard: is it sound?

The rule is: parse with `new URL(url, location.origin)`, then follow only if `protocol === "https:"` or the origin
matches the page's. I ran the edge cases through Node's WHATWG URL parser (the same parser browsers use for
`location.assign`):

| Input | Parsed (prod origin `https://app.example.com`) | Result |
|---|---|---|
| `JAVASCRIPT:alert(1)`, `" javascript:..."`, `"java\tscript:..."`, `"\u0000javascript:..."` | `javascript:` | refused |
| `data:text/html,...` | `data:` | refused |
| `http:evil.example` | `http://evil.example/` | refused |
| `https:evil.example` | `https://app.example.com/evil.example` (same scheme, so relative) | allowed, same origin |
| `HTTPS://evil.example` | `https://evil.example/` | allowed (any https) |
| `https://a@evil.example` | host `evil.example` | allowed (any https) |
| `//evil.example/x`, `/\evil.example/x`, `\\evil.example` | `https://evil.example/...` | **allowed in prod**, refused in dev (http origin) |
| `/billing/mock-portal?customer=x` | same origin | allowed |

The parser lowercases the scheme and strips leading C0/space and embedded tab/newline before scheme detection, so
case, whitespace and control-character tricks cannot get `javascript:` or `data:` through. The check and
`location.assign` use the same parser. `assign` resolves relative input against the document URL rather than
`location.origin`, but both are same-origin, so the result agrees. The script-execution threat the T-75 review raised
is closed.

**Is allowing any https host acceptable?** Yes, for this threat model. The URL comes from our own authenticated
`POST /api/billing/{checkout,portal}`, which builds it from Stripe's API response or from `APP_BASE_URL` (mock), never
from request input. To abuse it, an attacker would need to control our server or Stripe's reply. At that point an
open redirect is the least of the problems. The guard is defence in depth against a misconfiguration or a bad
provider reply, and blocking script and plain-http does that job. A host allowlist (`checkout.stripe.com`,
`billing.stripe.com`, same origin) would be stricter. It would also couple the SPA to provider hostnames, and Stripe
custom domains change them. Optional (S2).

## MockPortal reflection of `?customer=`

`customer` is read with `URLSearchParams.get` and rendered as a JSX text child inside `<code>`. React escapes it. There
is no `dangerouslySetInnerHTML`, `href` or attribute sink, so HTML injection is not possible. The page sits behind the
signed-in branch of `App.tsx` (`if (!me) return null`), and the strict CSP (`script-src 'self'`) still applies. The
worst a crafted link can do is display arbitrary text in a box labelled "Customer ref". That is acceptable for a mock
page.

## Critical issues

None.

## Suggestions

- **S1 Doc and test overstate what is refused** (`frontend/src/redirect.ts` lines 3-5; `redirect.test.ts` line 22).
  The comment says `//other-host` is refused, and the test asserts that. It only holds because the test stubs an
  `http://localhost:3000` origin. In production the origin is https, so `//evil.example`, `/\evil.example` and
  `\\evil.example` resolve to `https://evil.example` and are followed under the "any https" rule. This is not a
  vulnerability, since any https URL is allowed by design, but the comment and test give a false guarantee. Fix: reword
  the comment ("protocol-relative URLs inherit the page's scheme, so in prod they are treated like any https URL"). Add
  a test with an `https://` stubbed origin that documents the prod behaviour, plus cases for `/\evil`,
  `JAVASCRIPT:` (uppercase), a leading space or `\t` inside `javascript:`, and `http:evil`.
- **S2 (optional) Host allowlist.** If you want an open-redirect guarantee rather than a scheme guarantee, allow
  same-origin plus `*.stripe.com` (or a list delivered in `/api/billing/plans`). The trade-offs are in the guard
  section above.
- **S3 Assign the parsed URL.** `safeRedirect` validates `target` but navigates to the raw `url`. Today the browser
  re-parses it identically, but `window.location.assign(target.href)` makes "what was checked is what is followed" true
  by construction.
- **S4 Mock portal refused in some dev setups.** The mock portal URL is `{APP_BASE_URL}/billing/mock-portal`, and
  `APP_BASE_URL` defaults to `http://localhost:5173`. The guard refuses it, showing BAD_REDIRECT, whenever the SPA is
  served from another http origin: `vite preview` on 4173, or the backend serving `dist/` on 8000. Before this change
  it navigated cross-port. Prod and https demos are unaffected. Options: handle the mock portal like mock checkout
  (detect a `mock_` customer, or have the mock return a path, then call `navigate()`), or note in the README that
  `APP_BASE_URL` must match the origin you browse.
- **S5 UI gate and server gate can disagree.** `disabled={!verified}` (`pages/app.tsx` line 211) ignores
  `REQUIRE_EMAIL_VERIFICATION=false`, which `verified_owner` honours. That setting is only allowed with the outbox email
  provider (`config.py` line 127), so this affects dev only, and the outbox still lets you verify. Still, the UI is
  stricter than the API there. Also, "Choose <plan>" is not disabled for unverified owners, although the server rejects
  checkout for them. Consider exposing the gate in `/api/auth/me` and applying it to both buttons the same way.
- **S6 MockPortal test.** Add a case with `?customer=<img src=x onerror=alert(1)>` that asserts the text appears and no
  `img` element is created. This pins the escaping.

## Tests

The billing tests check behaviour that matters:
- a `javascript:` portal URL is refused, `assign` is never called, the alert shows, and the button is re-enabled;
- an `http://evil` checkout URL is refused;
- the unverified owner sees a disabled button and the hint, and the verified owner sees no hint;
- the MockPortal test renders the ref and checks that the back link navigates.

`redirect.test.ts` covers the allow and refuse matrix, with the S1 caveat about the origin stub.
