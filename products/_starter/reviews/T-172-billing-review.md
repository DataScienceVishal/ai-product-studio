# Review: p/_starter/T-172 (dbe9a0b), billing fixes B1-B5

Reviewer: reviewer agent, 2026-11-27. Diff: `git diff origin/main...dbe9a0b` (6 files, +229/-12). Bug list: `reviews/T-172-bughunt.md`.

## Verdict: CHANGES

B2, B3, B4 and B5 are correct and tested. B1 is the right design: the network call runs after the commit, so no lock is held
during the Stripe DELETE, and it can only cancel a ref that differs from the tracked one. Two paths still get it wrong, and
I reproduced both with throwaway probes (deleted afterwards, no product code changed):

1. A paid duplicate that arrives out of order is never cancelled, so B1 comes back.
2. A tenant who is active on the mock provider and then pays through Stripe has the real Stripe subscription cancelled.

## Tests

- Full backend suite on the branch tree: **752 passed, 1 skipped** (116 s, local Postgres 16). This matches NEXT.md and the README.
- Mutation checks: I reverted each fix in turn and ran `test_billing.py` + `test_hardening.py`. Every mutant was killed:

| Mutant | Killed by |
|---|---|
| `if duplicate:` replaced with `if False:` | test_b1_failure_to_cancel... (and test_b1_second...) |
| webhook passes `None` instead of the provider | test_b1_failure_to_cancel... |
| `except Exception` narrowed (cancel failure propagates) | test_b1_failure_to_cancel... |
| `payment_status` check removed | test_b2_... |
| `async_payment_succeeded` not handled | test_b2_... |
| `_check_fields` call removed | test_b3_... |
| missing-`created` raise removed | test_b4_... |
| `has_access` removed from checkout 409 | test_b5_active_subscription_past_its_grace... |
| `has_access` removed from `duplicate` | test_b5_active_subscription_past_its_grace... |
| mock `customer` removed | test_b5_mock_completion_stores_a_customer... |

- The six modified older tests still test what they used to. Each now puts s1 in `past_due` before s2 replaces it, and still
  asserts that the old subscription's late events cannot touch the current one. Proof: when I disabled the "event for a
  different subscription ignored" guard (`if other_sub and not update.starts_subscription`), five of them failed
  (old_subscription_cancel_after_new_checkout, old_subscription_past_due, same_second_new_activation, stripe_old_subscription_deleted,
  plus the untouched old_subscription_recovering). The other two (`cancel_of_the_current_subscription_still_works`,
  `subscription_created_for_a_new_id_does_take_over`) still check that a takeover happens. They now cover replacing a
  non-working subscription, which is the only takeover the new rule allows.

## Critical issues (must fix)

### C1. An out-of-order duplicate skips the B1 handling and is never cancelled
- Where: `app/routes/billing.py:127-131` (stale check) runs before `:133-147` (duplicate check).
- Why: the extra subscription's starting event (s2, `created` t-50) can arrive after a newer event for s1 (a
  `customer.subscription.updated` at t). In Stripe this is the normal case: s1 sends created, updated and completed events
  within seconds, and two tabs can be paid seconds apart. The s2 event is then treated as "stale billing event ignored" at
  info level. Its event id is recorded, `cancel_subscription` is never called and no warning is logged. s2 keeps charging
  the card and nobody tracks it, which is exactly B1.
- Repro (probe, Stripe-shaped events through `apply_update`): checkout.session.completed sub_1 @t-100, then
  subscription.updated sub_1 @t, then checkout.session.completed sub_2 @t-50. Observed: `cancelled == []`, tenant stays on
  `('active', 'starter', 'sub_1')`.
- Fix: run the duplicate check before the stale check. Whether s2 is an extra subscription doesn't depend on its timestamp
  relative to s1's last event: a different id starting while the tracked subscription is active with access is an extra.
  A late start event for an older, already-replaced subscription would then also be cancelled, which is right: that
  subscription is orphaned. Add a test with exactly the order above.

### C2. A tenant active on the mock provider who pays with Stripe has the paid Stripe subscription cancelled
- Where: `app/routes/billing.py:133` (`duplicate` never compares `sub.provider` with `provider`).
- Why: `checkout` (`:48`) only returns 409 when `sub.provider == billing.name`, so a tenant active on `mock` (any demo
  tenant: mock completion gives 30 active days) can start a Stripe checkout once the deployment switches to
  `BILLING_PROVIDER=stripe`. That switch is the starter's next step. When the Stripe completion arrives, `other_sub` is true
  and the mock subscription "has access". The real Stripe subscription is cancelled right after payment, with no refund, and
  the tenant stays on the mock plan. Before this branch, Stripe correctly replaced the mock subscription.
- Repro (probe): mock checkout + mock complete, then a Stripe checkout.session.completed for `sub_real` applied with
  provider `stripe`. Observed: `cancelled == ['sub_real']`, sub stays `('active', 'starter', 'mock_sub_...')`.
- Fix: add `and sub.provider == provider` to `duplicate`, so another provider's subscription is never a duplicate, and add a
  test for it.

## Suggestions (not blocking)

- S1. Cancel failures are never retried. The event id is committed before the DELETE, so a failed cancel leaves only an
  ERROR log line while the customer is still being charged. This is documented in NEXT.md, but it is the one money-at-risk
  path. Options: when the cancel fails, delete the `BillingEvent` row and return 5xx so Stripe redelivers (it retries for up
  to 3 days), or keep a small "pending cancels" table.
- S2. Timeouts. `_call` makes up to 3 attempts of 20 s each plus 3 s of backoff, so the webhook can block a threadpool worker
  for about 63 s, well past the point where Stripe gives up and redelivers. A redelivery is harmless (event id already
  recorded, so applied=false), but a burst of these can tie up the threadpool. Consider a short timeout and a single attempt
  for this call.
- S3. Double cancel. One extra subscription usually produces two start events: `customer.subscription.created` (if it is
  already `active`) and `checkout.session.completed`. Both hit the duplicate path and call DELETE twice. `_call` treats a 404
  as done, but if Stripe answers an already-cancelled subscription with a 400, the second call raises `billing_rejected`
  and logs a false "could not cancel ... by hand" to-do. I have not checked Stripe's reply. Verify it with test keys, or skip
  the cancel when an earlier cancel for the same ref was logged.
- S4. Kept vs cancelled is decided by arrival order, not by which session the customer paid last. If the two tabs had
  different plans, the plan the customer chose second may be the one cancelled. This is acceptable for now; state it in the
  README billing notes.
- S5. B2 may be only partly closed. For delayed payment methods, `customer.subscription.created`/`updated` with status
  `active` still activates the plan (`starts_subscription=True` for created). I have not checked whether Stripe reports
  `active` while a Bacs/SEPA first payment is still processing. Check this before the selling ADR relies on it.
- S6. Replacing a lapsed "active" subscription (the B5 path) or a past_due one never cancels the old ref at the provider. If
  the lapse was a lost webhook, the old subscription may still be billing. This happened before the branch too; consider
  calling `cancel_subscription(old_ref)` on takeover.
- S7. `_check_fields` doesn't check `event_id`. `BillingEvent.id` is String(255), so an over-long signed id raises
  `DataError` at flush, which is not caught (only `IntegrityError` is) and gives a 500. Low risk (the event must be signed),
  but it is the same class of bug as B3.
- S8. Test gap: no test sends a Stripe `customer.subscription.created` for s2 while s1 is live (only the mock path and the
  provider method are tested). Add one with the C1 and C2 tests.

## Checked and fine
- No network inside the transaction or row lock: `db.commit()` comes before `cancel_subscription` (`:136-143`). The webhook
  calls `apply_update` through `run_in_threadpool`, and `mock_complete` is a sync route.
- The wrong-ref cancel is impossible on the same provider: `duplicate` requires `other_sub`, which requires a non-empty
  `update.provider_ref` that differs from the tracked one. The ref comes only from a signed event.
- Redelivery of the duplicate event: the event id was committed, so it returns `applied: false` with no second cancel.
- Logs carry only the tenant id and the subscription ref. No secrets or personal data.
- B3: the check runs before `db.add(BillingEvent)`, and the test shows the same tenant applies a fresh event afterwards.
- B4: the mock raises ValueError, which the webhook maps to 400. The `mock_complete` path always sets `created`.
- B5: `has_access` is used the same way in checkout and in `duplicate`. The mock customer id `mock_cus_<hex>` is
  URL-encoded by the portal.
