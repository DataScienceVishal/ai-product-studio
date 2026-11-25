# T-73 review: refuse checkout while past_due

Reviewer, 2026-11-25. Branch `origin/p/_starter/T-73-past-due-checkout` at 50b9efa, diff `main...50b9efa`
(`app/routes/billing.py` +5, `tests/test_billing.py` +26). Read only; suite not run (lead is running it).

**Verdict: PASS** (no blocking issues; three small follow-ups below).

## Summary

Closes T-72 review item S1: a tenant in `past_due` can no longer start a second provider subscription next to
the unpaid one. The check sits right after the `already_subscribed` check, after the rate limit and the
transaction commit, and before any provider call, so no checkout session is ever created for a refused tenant.

## Checks asked for

- **Order vs plan validation.** Refusing before `PLANS.get` is right. It matches `already_subscribed`, the state
  error is the one the customer can act on, and it reveals nothing (the caller is the verified owner of the tenant).
  A past_due tenant sending `plan="bogus"` gets 409, not 422. That is fine.
- **Provider mismatch.** The `active` check requires `sub.provider == billing.name` (so a tenant left `active` by
  mock events can buy for real after the switch to Stripe). The new `past_due` check has no such condition. A
  tenant left `past_due` by the mock provider (demo DB later pointed at Stripe) is refused forever: no Stripe
  event will ever arrive for a mock ref. Low likelihood in production, but it is a stuck state that did not exist
  before and the fix is one clause (S1).
- **Stuck customers.** Stripe `unpaid` also maps to `past_due` (`app/billing.py:333`). With Stripe's "mark as
  unpaid" dunning setting the subscription stays `unpaid` indefinitely and never sends `deleted`, so the customer
  stays blocked until support acts. Without a portal route, "contact support" is acceptable for the starter
  (selling is locked, no live payments). But the message tells the customer to "Update your payment method",
  and the app gives them no way to do that (S2).

## Critical issues

None.

## Suggestions

- **S1** `app/routes/billing.py:45`: mirror the active check:
  `if sub.status == "past_due" and sub.provider_ref and sub.provider == request.app.state.billing.name:`.
  Add a test: past_due through the mock provider, then the app's billing name differs, and checkout returns 200.
- **S2** `app/routes/billing.py:47-49`: until a portal route exists, word it as an action the customer can take,
  e.g. "Your last payment failed, so a new checkout would charge you twice. Contact support to update your card
  or change plan." Add a board follow-up: a Stripe Customer Portal session endpoint (`/api/billing/portal`). That
  is the real way out and should land before G4. Also record in the playbook or NEXT.md that the Stripe dunning
  setting should be "cancel subscription" after retries, not "mark unpaid", so blocked tenants unblock themselves.
- **S3** tests: (a) assert that no checkout session was created on refusal (for example, the mock
  `billing.sessions` is unchanged), so the test pins "provider never called" and not just the status code;
  (b) one Stripe-shape test where `customer.subscription.updated` with `status=unpaid` leads to the 409;
  (c) recovery: past_due, then active on the same ref, then checkout returns 409 `already_subscribed` (not
  `subscription_past_due`).

## Test quality

The three tests check behaviour through the public API: refused while past_due, allowed after cancel, allowed on
trial. The two "allowed" controls make sure the check is not too broad. The past_due test fails without the fix:
the old code would return 200. That is good for a 5-line change.
