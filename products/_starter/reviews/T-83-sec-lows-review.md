# Review: p/_starter/T-83-sec-lows (8ee125d)

Reviewer, 2026-11-25. Diff: `git diff main...p/_starter/T-83-sec-lows` (8 files, +51/-5). Fixes L1, L2 and I1 from
`products/_starter/reviews/T-83-security.md` (on origin/main at 11c25d2; the branch is based on 6f29e7d, so it
does not contain that report yet. The merge is trivial, no overlapping files).

## Verdict: PASS

No blocking issues. One test gap worth closing (S1 below) before or soon after the merge.

## Tests (re-run by reviewer)

- Backend: `/tmp/claude-0/venv/bin/python -m pytest` against the local Postgres: **564 passed, 1 skipped** (67.6 s).
- Frontend: `npx vitest run`: **155 passed (6 files)**. `npx tsc --noEmit`: clean.
- These match what the builder reported.

## What I checked

**L1: 403 for an unverified owner on `POST /api/billing/portal`** (`backend/tests/test_verification.py:61-72`)
- The test gives the tenant a customer first, so the only thing that can refuse is the verification gate. It checks
  `403` and `error == "email_not_verified"`, then verifies the email and expects `200`. If `verified_owner` were swapped
  for `owner` on the route, the first assertion would fail: this test would catch the regression. Good.
- Nit: the `update(Subscription)` has no `WHERE`. That is safe because each test gets its own database with one
  tenant, but `.where(Subscription.tenant_id == ...)` would say what it means.

**L2: mock portal only when the server says mock**
- `routes/health.py:41-42` returns `billing_provider: app.state.billing.name`. The value is the class constant
  `"mock"` or `"stripe"` (`billing.py:146`, `:202`). There are no keys, secrets, URLs or tenant data. `/api/config` is
  public (it is in the `PUBLIC` set in `test_hardening.py:422`), so anyone can see which provider a deployment uses.
  That is already visible from the checkout redirect to Stripe, so nothing new leaks. Acceptable.
- Fail-closed: `api.ts:29` starts with `billingProvider = ""`. The value is set only when the response is OK and
  `billing_provider` is a string. A failed, hung (5 s abort) or non-OK `/api/config` leaves it `""`, and
  `isMockBilling()` is a strict `=== "mock"`. `main.tsx` waits for `loadClientConfig()` before it renders, so
  `MockPortal` cannot render before the config arrives. Correct.
- `MockPortal` (`app.tsx:284-286`) returns a fixed "Page not found" card before it reads `?customer=`, so no attacker
  text reaches the DOM when the provider is not mock. The test `billing.test.tsx:162-170` covers `"stripe"` and `""`,
  checks that the spoof string is absent and that the mock heading is not shown. A mutation from fail-closed to
  fail-open (`!== "stripe"`) would be caught by the `""` case.
- Old config shape: the only consumers of `/api/config` are `api.ts` (`loadClientConfig`) and the exact-equality
  assertion in `test_ai.py:964`, which was updated. `api.test.ts` uses objects with only `api_timeout_seconds`, which
  still works (the provider falls back to `""`). There are no e2e or Playwright references to `/api/config` or the
  mock portal. Nothing else relied on the old shape.
- Residual risk, accepted: with `BILLING_PROVIDER=mock` the page still echoes `?customer=`. That only affects demo
  deployments, and the security report allowed "and/or" for this fix.

**I1: URL-encoding** (`billing.py:164`)
- `quote(customer_ref, safe='')` is correct. The new test `test_billing.py:773-775` covers space, `&`, `=`, `#`, `/`
  and non-ASCII. The existing `test_billing.py:700` (`cus_1`) still passes unchanged.

## Suggestions (non-blocking)

**S1: nothing tests that `loadClientConfig` actually reads `billing_provider`.** As a check, I deleted the assignment
line in `api.ts` (in a scratch copy, not the repo), and all 155 vitest tests still passed. That is because the
component tests set the flag through `setBillingProviderForTest`. The same goes for changing the initial value from
`""` to `"mock"`, which would fail open on a failed `/api/config`: no test would notice, because `afterEach` resets
the flag through the setter. Fix: in `api.test.ts`, add a case where
`reply(200, { api_timeout_seconds: 30, billing_provider: "mock" })` gives `isMockBilling() === true`. Then a
non-string value (`{ billing_provider: 1 }`) and a rejected fetch should both give `false`. To catch a fail-open
default, call `loadClientConfig()` with a rejected fetch first. About 10 lines.

**S2:** add a backend assertion that a Stripe-configured app serves `billing_provider: "stripe"`. Today only `"mock"`
is asserted (`test_ai.py:964`).

**S3:** `setBillingProviderForTest` is exported from production code. That is fine at this size. A comment, or
`vi.mock` on the module, would stop it being called outside tests.
