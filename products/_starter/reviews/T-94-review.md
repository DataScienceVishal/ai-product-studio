# Review: p/_starter/T-94 (e84ac73), Billing page says plan AI allowances are trial-sized

**Verdict: PASS**

## Summary

`LIMITED_PROVIDERS` moves from `routes/notes.py` to `app/billing.py`. `GET /api/billing/plans` adds
`ai_allowance {trial_sized, monthly_tokens, daily_tokens}`. The Billing page adds "once live billing starts" to each plan
and a note giving the trial allowance. Tests are on both sides, and BRIEF and ADR 0001 are updated. The label matches the cap
logic for every configuration that can exist today.

Evidence: I ran `tests/test_billing.py tests/test_cookies_and_limits.py tests/test_hardening.py tests/test_ai.py`
and got 278 passed. The lead reports the full backend at 673 passed and 0 skipped, vitest at 205 passed, and the build and
check_built_html both OK. I did not repeat those runs.

## Checks

- **Is the label truthful?** In `notes.py:109`, `limited = sub.status == "trialing" or sub.provider in LIMITED_PROVIDERS`,
  and when limited, `plan = PLANS["trial"]` (100,000 a month). `daily_cap=plan.ai_daily_tokens if limited`, which is
  30,000. So limited paid plans do get the daily cap, and the numbers on the note match the cap. They come from
  `PLANS["trial"]`, so the page and the cap cannot drift apart.
- **Configured provider vs the subscription's stored provider.** `settings.billing_provider` is
  `Literal["mock","stripe"]`, and both are in `LIMITED_PROVIDERS`, so `trial_sized` is always True today. New tenants
  start as `provider="none", status="trialing"` (auth.py:164), so they are limited because they are trialing.
  `apply_update` sets `sub.provider` to the provider that sent the webhook, which is the configured one. A purchase made
  from this page is therefore governed by the same provider the label checks, so the label answers the right question
  ("what will I get if I buy now?"). The two can only diverge after a future selling ADR removes `"stripe"`. Then an old
  `mock` active subscription would still be capped while the page shows the full allowance (see S1). That cannot happen
  today and the effect is small.
- **Public endpoint exposure.** The response reveals the trial token sizes and whether billing is test-mode. The page
  already prints "Test mode: no real payment is taken", and any trial sign-up sees the same caps. It exposes no tenant
  data and no secrets. Acceptable.
- **Stale references.** `test_cookies_and_limits.py:117` imports `LIMITED_PROVIDERS` from `app.routes.notes`. That
  still works, because the name is bound there by the import and the new identity test proves it is the same object.
  The `selling_unlocked` fixture in `test_hardening.py:28` patches only `notes.LIMITED_PROVIDERS`. The cap still reads
  that binding, so the tests stay valid. README:213 and the older reviews only name the set, not where it lives, so they
  are accurate or historical.
- **Docs.** The BRIEF and ADR 0001 text matches the code.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1.** When the selling ADR removes `"stripe"`, decide what happens to existing `mock` subscriptions in a stripe
  deployment. Either migrate them or keep the label provider-aware per tenant, for example with an authenticated
  `/api/billing/me` that reports `limited` for the caller. Add a line about this to the "Remove stripe" comment in
  `app/billing.py:58-60`.
- **S2.** Point `test_cookies_and_limits.py:117` at `app.billing` and make `selling_unlocked` patch both bindings
  (`app.routes.notes` and `app.routes.billing`). The fixture would then simulate the whole unlocked configuration rather
  than only the cap.
- **S3.** `api.ts` types `daily_tokens` as `number | null`, which matches `Plan.ai_daily_tokens: int | None`. Nothing
  else to change there.
