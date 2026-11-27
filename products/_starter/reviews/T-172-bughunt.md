# T-172 bug hunt: starter billing and team flows (QA, about 25 min)

Method: throwaway pytest probes (`backend/tests/test_zz_probe_t172.py`, deleted afterwards) using the suite's fixtures
against a local Postgres 16, run with `python -m pytest`. No product code changed, nothing committed. Every result
below was observed in a run. Line numbers refer to the files as at this date.

Scope note: there is no role-change route and invites always create `member`, so each tenant has exactly one owner.
Demoting the last owner, self-demotion and non-owner role changes cannot happen (no endpoint exists). Nothing to test there.

## Confirmed bugs

### B1. Medium: a second paid checkout silently replaces the first subscription, so the customer is billed twice and the first is orphaned
- Where: `app/routes/billing.py:107-110` (`other_sub` / `starts_subscription` rule) and `:125-126`; `checkout` at `:48-56` only blocks when a subscription is already recorded as active.
- Repro: owner calls `POST /api/billing/checkout {"plan":"pro"}` and again `{"plan":"starter"}` (two tabs, both before paying; both succeed, 200). Complete both sessions (`POST /api/billing/mock/complete/<id>` twice, or Stripe: pay both Checkout pages).
- Observed: the second completion overwrites `provider_ref` (`mock_sub_<second>`), plan becomes `starter`. The first subscription is no longer tracked: its later `past_due` or `canceled` events are ignored as "different subscription" (`:108-113`), and with Stripe it keeps charging the card.
- Expected: the second completion for a tenant that already has an active subscription should not take over silently; at minimum log and flag for refund or cancel the extra one, or create checkout sessions only when none is open.
- Suggested test: two checkouts, complete both, assert the tenant has one provider_ref and that the other subscription is queued for cancellation (or the second `complete` is refused). Currently the second wins.

### B2. Low-Medium: Stripe `checkout.session.completed` activates the plan even if `payment_status` is `unpaid`
- Where: `app/billing.py:346-353` never reads `obj["payment_status"]`.
- Repro: `StripeBilling.parse_webhook` with a signed `checkout.session.completed` whose object has `"payment_status":"unpaid","status":"complete"` and tenant metadata. Observed: `BillingUpdate.status == "active"`.
- Expected: `None` (wait for `checkout.session.async_payment_succeeded` / the subscription event). Delayed payment methods (for example bank debits) send exactly this. Test-mode only for now, but this is the Stripe contract the selling ADR will rely on.
- Suggested test: parse that payload and assert the update is `None` or not `active`; also assert `async_payment_succeeded` activates.

### B3. Low: signed webhook with a non-string `plan` gives HTTP 500, and an over-long `offer` gives HTTP 500 after the event id is recorded path
- Where: `app/routes/billing.py:85` (`update.plan not in PLANS` raises `TypeError: unhashable type: 'list'`, not in the `except` list at `:165` because it runs after parsing); `:123-124` writes `sub.offer` (String(40)) with no length check, so a 100-char offer gives `DataError 22001` at commit (`:134`).
- Repro (mock provider, signed): `{"id":"e1","type":"checkout.completed","created":<now>,"data":{"tenant_id":"<tid>","plan":["pro"]}}` returns 500 `internal_error`. Same with `"offer":"x"*100`.
- Expected: 400 `bad_event`, so the provider does not retry and the error log is not filled. Stripe-sourced metadata is ours, so real risk is low; `provider_ref` (String 255) has the same unbounded-write shape.
- Suggested test: both payloads must return 400, and a later valid event with a fresh id must still apply.

### B4. Low: an event with no `created` field bypasses the ordering check and can reactivate a cancelled tenant
- Where: `app/routes/billing.py:116` (`update.occurred_at and ...`); `app/billing.py:199` (`_when(None)` gives None).
- Repro (mock, signed): `subscription.canceled` with `created=now`, then `checkout.completed` for the same subscription with no `created`. Observed: second applied, status `active`.
- Expected: missing timestamp treated as stale-unknown (reject 400, or refuse to override a later cancel). Stripe always sends `created`, so mock-only in practice.

### B5. Low: an "active" subscription whose period ended more than 3 days ago is locked out of both access and checkout
- Where: `app/billing.py:382-383` (`has_access` false) versus `app/routes/billing.py:48-49` (checkout 409 `already_subscribed`, "contact support").
- Repro: complete a mock checkout, set `current_period_end` to 10 days ago (a lost renewal webhook). Observed: notes AI refuses (no access), `POST /checkout` gives 409 `already_subscribed`, and `POST /portal` gives 409 `no_billing_customer` (mock never stores a customer id; Stripe would have one, so the portal route is the escape hatch only with Stripe).
- Expected: checkout should be allowed when `has_access` is false, or the error should point at the portal. Note the mock customer id gap too: `MockBilling.completion_event` never sends `customer`, so "Manage billing" is unreachable in mock for every tenant.

### B6. Low: re-sending an invite to an address that already has a pending invite fails at the pending cap, and resends eat the daily quota
- Where: `app/routes/team.py:74-77` (cap check runs before the "revoke older invite for same email" at `:80`) and `:70-73`.
- Repro: set `max_pending_invites=2`, invite a@ and b@, then invite a@ again. Observed: 409 `too_many_pending`. With `invites_per_day=3`, three invites to the same address then a fourth returns 429.
- Expected: a resend replaces the old invite, so the pending count does not grow; the resend should succeed at the cap.
- Suggested test: at cap, re-invite an existing pending email returns 201 and the old link stops working.

### B7. Low: an address invited by two tenants leaves the loser's invitation pending but dead, with no feedback
- Where: `app/routes/team.py:78` only checks existing users; `:136-147` (accept).
- Repro: tenant A and tenant B both invite m@x.test (both 201). m accepts A's link (201), then B's link: 409 `email_taken`. Tenant B's `GET /api/team` still lists m@x.test as pending until it expires (7 days).
- Expected: once the address becomes an account, other tenants' pending invites for it are revoked, or the owner sees them as failed. Also note invite-time `email_taken` (409) tells any verified owner whether an address has an account anywhere (enumeration, same accepted risk as signup, rate limited 20/min).

## Checked and fine
- Webhook signature: empty secret, missing header, bad MAC, non-digit or stale timestamp, future timestamp, multiple `v1` values all give 400 `invalid_signature` (code and existing tests). Oversized body gives 413.
- Replay: same event id twice gives `applied: false` the second time; unknown-plan events are refused before the id is recorded (redelivery works after a fix).
- Out of order: `subscription.canceled` at t then stale `checkout.completed` at t-100 leaves the tenant `canceled` (stale event ignored, id kept).
- Unknown event types, missing tenant, bad tenant UUID, Stripe `livemode: true`, Stripe statuses `paused`, `incomplete`, unknown: all return `received: true, applied: false`, no state change.
- Event for a deleted tenant: no error.
- Members (invited, role `member`): checkout, portal, invite, remove member, `mock/complete` all 403.
- Unverified owner: portal 403 `email_not_verified` (consistent with checkout and invites).
- Portal for a tenant without a customer id or on another provider: 409 `no_billing_customer`.
- Invites: expired, revoked, reused, wrong-case email, existing account, registered after invite, other tenant's invitation and member ids (404), signed-in user accepting (existing tests, re-read, plus my probes). Removed member: delete again gives 404, re-invite after removal gives 201. Removing self gives 422 `cannot_remove_self`. Non-UUID member id gives 422.
- Concurrent accept of one token: the unique email index yields one account (409 for the loser); code path reviewed, not load-tested.

## Not probed
- Non-ASCII `Stripe-Signature` header (httpx refuses to send it; `hmac.compare_digest` on a non-ASCII str raises `TypeError`, which the webhook turns into 400 `bad_event` instead of `invalid_signature`: cosmetic, by code reading only).
- Real Stripe API behaviour; concurrent duplicate webhook delivery under load (code uses a PK insert plus `FOR UPDATE`, looks right).
