# Review: p/_starter/T-15-coupon (head e4a49a8)

Reviewer gate, 2026-11-24. Diff: `git diff main...p/_starter/T-15-coupon` (7 files, +215 / -7).

**Verdict: PASS**

## Summary

The early-customer offer is now applied on the server. `StripeBilling.ensure_coupon` creates a coupon with a fixed id
(`studio-early50-50pc-3m-v1`), and `create_checkout` sends `discounts[0][coupon]` with no `allow_promotion_codes`. If Stripe
says `resource_already_exists`, the code reads the coupon back with GET and rejects it if its terms differ. Only
`ensure_coupon` passes `accept_error_codes`, so every other 400 still raises `billing_rejected`. The test-mode lock is
unchanged: the constructor still refuses keys that are not `sk_test_`/`rk_test_`, `test_cookies_and_limits.py` still covers
`sk_live_`, and the `livemode` guard on webhooks is untouched. The README, `.env.example` and NEXT.md match the code. NEXT.md
says plainly that the change has never been run against real Stripe test keys.

Checked against the Stripe docs (docs.stripe.com, fetched today):
- Checkout Session create: `discounts` is "the coupon or promotion code to apply to this Session. Currently, only up to one
  may be specified", and `discounts[].coupon` is "the ID of the coupon". The form key `discounts[0][coupon]` is correct.
  Stripe does not accept `allow_promotion_codes` and `discounts` in the same request, so dropping it is required, not just
  tidier.
- Error codes: `resource_already_exists` is "a resource with a user-specified ID (for example, plan or coupon) already
  exists". The shape `{"error": {"code": ...}}` on HTTP 400 is what the code reads.
- Coupons: `id`, `percent_off`, `duration=repeating` and `duration_in_months` are valid create parameters. On GET,
  `percent_off` comes back as a float (`50.0`). Python's `50.0 == 50` holds, so the comparison is correct. All plans bill
  monthly, so "3 months" means 3 invoices.

## Evidence

- Backend: `.venv/bin/python -m pytest`: **484 passed, 1 skipped** in 60s on local Postgres 16. This matches the README count.
- Frontend: `npx vitest run`: **114 passed (114)**.
- Do the tests fail when the code is reverted? Yes. I broke the code one way at a time, ran `tests/test_billing.py` and
  `tests/test_hardening.py`, then restored the file (working tree clean afterwards):

| Mutation | Test that fails |
|---|---|
| main's billing.py restored | `test_coupon_id_changes_with_the_offer_terms` (plus the checkout-form tests) |
| drop `valid is False` check | `test_existing_coupon_with_other_terms_is_refused[change3]` |
| drop `duration_in_months` check | `test_existing_coupon_with_other_terms_is_refused[change1]` |
| skip the GET read-back | `test_existing_coupon_with_other_terms_is_refused` |
| no per-process cache | `test_coupon_is_created_once_then_cached` |
| accept any 400 on the coupon | `test_other_400s_on_the_coupon_are_billing_rejected[None]` |
| re-add `allow_promotion_codes` | `test_checkout_without_offer_has_no_discount_and_no_promotion_codes` |
| drop the coupon Idempotency-Key | `test_checkout_with_offer_applies_the_coupon_server_side` |
| F1: drop `_count_ignoring_quotes` from `_split_top_level` | `test_one_line_pages_object_with_paired_apostrophes_is_unreadable` |

## Critical issues

None.

## Suggestions (non-blocking; fix in the next billing touch or before first real test-key run)

1. **The fixed coupon Idempotency-Key causes avoidable failures.** In `backend/app/billing.py` `ensure_coupon`,
   `idempotency_key=f"coupon-{coupon_id}"` is the same for every process, every instance and every day.
   - Two checkouts can arrive at once on a cold process, or on two instances. The second POST, sent while the first is still
     running, gets **409 `idempotency_key_in_use`** (in Stripe's error-code list). `_call` turns any status of 400 or above
     into `billing_rejected`, so that customer sees a 502 on their first checkout.
   - For 24 hours Stripe replays the stored 200 for that key. If the coupon is deleted in the dashboard within that window,
     a restarted process is told it "created" the coupon, caches the id, and every checkout with the offer fails until
     restart.
   - Fix: use a fresh key per `ensure_coupon` call, for example `f"coupon-{coupon_id}-{uuid4().hex}"`. Retries inside `_call`
     still reuse it. A duplicate create is already handled by the `resource_already_exists` path, so the fixed key adds
     nothing and only causes the two problems above. Add a test for a 409 or a concurrent duplicate.
2. **A coupon deleted after it is cached is never re-created.** `self._coupons` is never cleared. If the coupon is deleted
   or archived later, every offer checkout returns `billing_rejected` until restart. Option: if the checkout POST fails while
   a coupon was attached, drop the id from `_coupons` so the next request re-checks it. Low priority in test mode.
3. **Coupon `name` length.** Stripe caps coupon names at 40 characters. `"EARLY50 50% off for 3 months"` is 28, but a longer
   offer code would make every checkout with that offer fail. Truncate to 40, or assert it in
   `test_coupon_id_changes_with_the_offer_terms`.
4. **F1 has a false positive (it fails safe).** In `backend/tests/test_spa.py` `_count_ignoring_quotes`, a comma inside a
   quoted string in a PAGES entry now marks the object as unreadable. Verified: `{ "/a": () => <Page title="Hi, there" />,
   "/c": C }` gives `(set(), ['PAGES[path]'])`. The test fails loudly rather than passing silently, which is the right way to
   fail, but the new assertion message doesn't name this cause. Add "a comma inside a quoted string in a PAGES entry" to the
   message. Alternatively, run the quote-ignoring count only when the text contains an apostrophe.
5. Minor: in `test_billing.py`, `from app.errors import AppError` sits above the `app.billing` import. The old
   `stripe_provider()` handler still returns `{"id": "studio-coupon"}` for the coupon, which is harmless because the code
   doesn't use the POST reply's id. Cosmetic only.

## Security and performance

- Authorization is unchanged: `/api/billing/checkout` still needs `verified_owner`, is rate-limited per tenant, and checks
  the offer against `OFFERS` on the server. Removing `allow_promotion_codes` closes a gap: before, a customer could enter
  any promotion code that existed in the Stripe account, and the app would never check or record it.
- No secrets in the diff. The coupon id contains no tenant data.
- Cost: one extra Stripe call per offer per process (two if the coupon already exists). It is cached afterwards. The route
  is a sync `def`, so it runs in the threadpool and the extra call does not block the event loop.

## Re-review a2c8e71

**Verdict: PASS**

- `app/billing.py:249` `ensure_coupon` now creates the Idempotency-Key as `coupon-<id>-<uuid4 hex>`, once per call. `_call` sets the header before its retry loop (`billing.py:206-208`), so internal retries reuse the key while separate calls don't. Concurrent first checkouts no longer 409, and stale results no longer replay. Correctness doesn't depend on the key, because the `resource_already_exists` + GET path still handles races.
- `billing.py:248` limits the coupon name to 40 characters, Stripe's maximum.
- `tests/test_billing.py:207-208` checks the prefix plus 32 hex characters. **Revert check:** with `billing.py` from a2c8e71^, `test_checkout_with_offer_applies_the_coupon_server_side` FAILS (`'coupon-studio-early50-50pc-3m-v1'.startswith('coupon-studio-early50-50pc-3m-v1-')` is False, exit 1). With the fix restored it passes.
- Backend suite: 484 passed, 1 skipped (`test_spa.py:103` frontend not built), 0 failed, exit 0. The `ERROR app.ai` lines in the `-rA` output are captured logs, not failures.
- Frontend vitest: 5 files, 114 tests passed.

Nit (non-blocking): no test uses a code long enough to exercise the 40-character limit. Add one when a longer offer code appears.
