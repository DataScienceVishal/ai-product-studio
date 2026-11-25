# T-83 security and privacy pass: billing portal, redirect guard, verification gate

- Scope: commits 81d0c9b (T-75), 696786d (T-76), c09fbca (T-77), 9ca11e6 (T-78) on `main`, plus the code around them:
  `backend/app/billing.py`, `backend/app/routes/billing.py`, `routes/auth.py`, `routes/team.py`, `deps.py`, `main.py`
  (CsrfGuard, headers), `config.py`, `spa.py`, `frontend/src/redirect.ts`, `frontend/src/pages/app.tsx`, `App.tsx`, `ui.tsx`.
- Reviewer: security agent, 2026-11-25. Code not modified.

## Verdict: PASS

No high or medium findings. Two low findings and three info notes, none of them exploitable today. Board tasks are
optional (low): L1 is worth adding with the next starter change.

## Findings

### L1 (low): no server-side regression test for the verification gate on `POST /api/billing/portal`
- Where: `backend/app/routes/billing.py:65` (gate is `Depends(verified_owner)`, correct); tests in
  `backend/tests/test_verification.py:51` cover invite and checkout only. `test_billing.py:683-770` covers 401, 403
  member, tenant isolation and rate limit for the portal, but not an unverified owner.
- Attack: a later refactor swaps `verified_owner` for `owner` on `/portal` (the UI still disables the button, so nobody
  notices). An unverified owner, i.e. a sign-up with an address they don't control, then opens the provider portal.
  Impact is small today (the portal only shows that tenant's own customer), which is why this is low.
- Fix: add `assert client.post("/api/billing/portal").status_code == 403` and `error == "email_not_verified"` for an
  unverified owner with a customer set, next to `test_unverified_owner_cannot_invite_or_check_out`.

### L2 (low): `/billing/mock-portal` renders an attacker-chosen `?customer=` string in every config, including prod with Stripe
- Where: `frontend/src/pages/app.tsx:283-288` (`MockPortal`), `frontend/src/App.tsx` route, `backend/app/spa.py` CLIENT_ROUTES.
- Attack: content spoofing / phishing. An attacker sends a signed-in user a link to the real app:
  `https://<app>/billing/mock-portal?customer=Payment%20failed%20-%20call%200800%20000%20000%20to%20fix`. The page,
  on the genuine domain, says "Mock billing portal ... Customer ref: Payment failed - call 0800 ...". React escapes it
  (no XSS; the hostile-string test at `billing.test.tsx:170` confirms), and the "mock" wording limits credibility, so low.
- Fix: render the mock portal only when the server says the provider is mock (e.g. expose `billing_provider` or a
  `mock_portal` flag in `/api/config` and fall back to the 404 view otherwise), and/or stop echoing the raw parameter
  (show a fixed "test customer" label, or only show values matching `^[A-Za-z0-9_]{1,64}$`).

### I1 (info): `MockBilling.portal_session` does not URL-encode `customer_ref`
- Where: `backend/app/billing.py:162-163`.
- The value comes only from a signed webhook (`customer` in event data), and it sits after `?`, so it cannot change
  the host or path. No attack. Use `urllib.parse.quote(customer_ref, safe="")` for hygiene.

### I2 (info): `/me` now exposes `email_verification_required`
- Where: `backend/app/routes/auth.py:103-109`.
- Only to the signed-in user, and it is a single deployment-wide boolean that is already observable from the 403s.
  No personal data added. Fine.

### I3 (info): migration 0007 uses a plain `CREATE INDEX`
- Where: `backend/migrations/versions/20261125_0007_pending_usage_partial_index.py:24`.
- Takes a SHARE lock on `ai_usage` (blocks AI-call reservations) for the build. At starter scale this is seconds;
  the comment documents the CONCURRENTLY path. Downgrade drops only that index. No data change, no safety concern.

## Challenge to the declined host allowlist (T-77 S2): not overturned

I looked for a concrete way to make `safeRedirect` follow an attacker's https URL and found none:
- `portal.url` and `checkout.url` come only from our own authenticated endpoints. With Stripe, from the JSON reply
  of `https://api.stripe.com/v1` (hard-coded, TLS, secret key). With mock, from `settings.app_base_url` (env only; prod
  validator forces https and a public host, `config.py` `_safe_settings`).
- No request field reaches these URLs: `return_url` is built from settings, and `test_portal_route_builds_return_url_from_settings_not_headers`
  shows a spoofed `Host`/`Origin` is ignored. The only provider-controlled piece in the mock URL is `customer_ref`
  from a signed webhook, which lands in the query string (I1).
- So an allowlist would only matter if Stripe or our env config were compromised, at which point the attacker has
  much more. The decision stands.

## Checked and fine

- javascript:/data:/blob: URLs: `redirect.ts:19` refuses any non-https, non-same-origin target; `app.tsx:159` (T-78)
  stops `mockPortalPath` from treating `javascript:/billing/mock-portal` as in-app. The browser is sent to
  `target.href` (the parsed value), so check and use cannot diverge. A same-origin `javascript:` URL is impossible
  (its origin is "null").
- `mockPortalPath` on a foreign host (`https://evil.example/billing/mock-portal`) navigates in-app to the path only,
  dropping the host (covered by `billing.test.tsx:238-241`): safer than following it.
- Tenancy: `/portal` reads `subscription_of(db, me.tenant.id)` from the session's tenant only; no id in the request.
  Provider mismatch and missing customer give 409. `mock_complete` checks `session["tenant_id"] == me.tenant.id`.
  Tests: `test_portal_never_shows_another_tenants_customer`, `test_portal_is_owner_only` (member 403, anonymous 401).
- Verification gate is server-side: `deps.verified_owner` on both `/checkout` and `/portal`; the UI's `blocked` flag
  just mirrors it. Turning the gate off is refused by config unless `email_provider == "outbox"`.
- CSRF: `main.py` CsrfGuard requires `X-Requested-With` on every cookie-authenticated POST under `/api/` (only the
  signed webhook is exempt); CORS cannot contain `*`. `/portal` takes no body. Portal is rate limited per tenant (10).
- Caching / leakage of the portal URL (a short-lived bearer link): API responses carry `Cache-Control: no-store`;
  no log line in `billing.py` or `routes/billing.py` includes the URL, customer id or Stripe reply body; Stripe errors
  map to generic 502/503 messages.
- Mock checkout in prod: `mock/complete` returns 404 unless the provider is mock AND `MOCK_CHECKOUT_ENABLED` (default
  off). The mock portal page itself makes no API calls and holds no data (see L2 for its only weakness).
- Stripe live mode remains locked: `StripeBilling.__init__` accepts only `sk_test_`/`rk_test_`.
- `ai.py` `_PENDING = literal_column("'pending'")`: a constant, no user input, so no SQL injection.
- XSS: no `dangerouslySetInnerHTML` anywhere in `frontend/src`; HTML CSP is `script-src 'self'`.
- Secrets: regex scan of the four commits' diffs for Stripe keys, whsec, AWS keys, PEM blocks, hard-coded passwords
  and API keys: 0 matches.

## Tests

- Backend `python -m pytest -q`: could not run. `pytest` is not installed for `/usr/local/bin/python`, the
  `/usr/local/bin/pytest` interpreter lacks `psycopg`, and no Postgres is listening on `/var/run/postgresql:5432`.
  Not installed from the network, as instructed.
- Frontend `npx vitest run`: not run; `frontend/node_modules` is absent (0 entries).
- The test names cited above were read from source, not executed. The T-78 review records the last green run.
