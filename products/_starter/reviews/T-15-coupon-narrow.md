# Review: p/_starter/T-15-coupon-narrow (head ff78f3e)

**Verdict: PASS**

## Summary
The change narrows the coupon-cache drop in `StripeBilling.create_checkout` (products/_starter/backend/app/billing.py:282-287) so that only `billing_rejected` drops it. An outage (`billing_unavailable`) now leaves the coupon cached. It also adds `test_checkout_outage_keeps_the_cached_coupon`, and `stripe_provider()` now echoes `OFFERS["EARLY50"].coupon_id`, which is a cosmetic consistency change. This is what products/_starter/reviews/T-15-leftovers.md suggested.

## Evidence
- Full backend suite in a detached worktree at ff78f3e, run against a real Postgres: **488 passed, 1 skipped**.
- Mutation M1 (go back to `if coupon_id:`): the new test fails at `assert 'studio-early50-50pc-3m-v1' in set()`. The test bites.
- Mutation M2 (never drop, `if False:`): `test_failed_checkout_drops_the_cached_coupon_so_the_next_one_rechecks_it` fails. Both directions are guarded.

## Are there other codes a deleted or invalid coupon could produce?
No. `_call` (billing.py:201-236) only raises two codes:
- `billing_rejected`: any status >= 400 other than 429. That includes 400 (Stripe's "No such coupon" is a 400 `resource_missing`) and 404. It also covers a 2xx body that can't be parsed.
- `billing_unavailable`: 429, 5xx, transport errors, and running out of retries.

The 404 tolerance (`return {}`) only applies to `method == "DELETE"`. The checkout is a POST, so a 404 there still raises `billing_rejected` and drops the cache. A deleted or archived coupon therefore always takes the drop path. 429 and 5xx carry no information about the coupon, so keeping the cache on those is correct.

## Critical issues
None.

## Suggestions (non-blocking)
1. A 2xx reply that can't be parsed also maps to `billing_rejected` and drops the cache. That is harmless (one extra idempotent coupon check), but the comment could say "any billing_rejected" rather than "a 4xx".
2. The "incomplete reply" raise (billing.py:288-289) sits outside the try, so it never drops the cache. That is correct, because the request succeeded, but a short note would stop a future edit from moving it inside.
3. The new test could also cover 429, which goes down the same path. Optional.
