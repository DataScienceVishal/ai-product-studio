# Review: p/_starter/T-174-billing (1d240d3)

Reviewer: reviewer agent, 2026-11-27. Diff: `origin/main...origin/p/_starter/T-174-billing` (billing.py, routes/billing.py, test_billing.py, README).

## Verdict: CHANGES

## Tests

Full backend suite in a clean worktree: exit 0, 781 collected, 1 skipped (780 passed), which matches the README.
(`pyproject.toml` already sets `addopts = "-q"`, so `-q` on the command line gives `-qq` and pytest prints no summary line.
The count above comes from `--co` plus the exit code.)

## Summary

- S-2 (period end after a paid checkout): the provider is read outside the row lock and the result is written only if the
  row still has the same ref and an empty period end. A failed read is logged and does not fail the webhook. Good.
- S2 (cancel timeout and retry): `_call(timeout=, attempts=)` is correct. A 4xx is never retried. A rejected DELETE is
  checked once with a GET. The tests check the timeout extension and the number of attempts. Good.
- S6 (takeover cancel): the cancel runs after the commit, so it is outside the lock. It cancels only `old_ref`, never the
  new ref, and only when the old row is not already canceled. When the old subscription belongs to another provider, the
  app logs a to-do and does not call cancel. Good.
- Changed test `test_b5_active_subscription_past_its_grace_can_check_out_again`: **the change is right.** A row that is
  `active` past its period end plus grace may still be billing at Stripe (a lost renewal webhook, or Stripe still
  retrying). Once the new subscription replaces it, nothing tracks the old one, so leaving it running would charge the
  customer twice. Expecting the lapsed ref to be cancelled is the intended money-safe behaviour.
- S-3 (failed first payment keeps the trial): the rule is too broad. See B1.

## Critical issues

### B1. The S-3 rule ignores a legitimate cancellation, so an out-of-order delivery grants paid access (regression)

`app/routes/billing.py` lines 130-135:
`if update.provider_ref and update.status != "active" and sub.status == "trialing" and not sub.provider_ref: ignore`.

The rule treats every non-active event for a trialing tenant as "a failed first payment". Stripe does not guarantee
event order. Redeliveries after downtime or a 5xx come in any order. Take a trial tenant who pays for `sub_1` and then
cancels it immediately, or whose subscription is cancelled at once by support or a refund:

1. `customer.subscription.deleted` (sub_1, t2) arrives first. The rule ignores it and records nothing about sub_1.
2. `checkout.session.completed` (sub_1, t1 < t2) arrives next. It is not stale because `last_event_at` was never set,
   so the tenant becomes `active` on a subscription that is already dead at Stripe.

I reproduced this with a throwaway test (not committed) using `_stripe_apply`: deleted at now-10, then checkout
completed at now-20. Result: `('active', 'starter', 'sub_1')`, `current_period_end = None`.

On main, the delete set `canceled`/sub_1/t2, so the late checkout was stale and ignored. Now the tenant gets access until
the dead subscription's period end. If the S-2 lookup also fails, `current_period_end` stays None, `has_access` returns
True with no end date, and no later event ever arrives for a dead subscription. That is **permanent free access**.

Fix (pick one, and add a test for the order above):
- In the S-3 branch, when `update.status == "canceled"`, set `sub.last_event_at = max(sub.last_event_at, occurred_at)`
  and keep a record of the dead ref. Leave the status `trialing`, because trial access depends only on
  `trial_ends_at`. The late checkout for that ref is then stale.
- Or, more robust: have the post-commit Stripe read (`subscription_period_end`) also return the subscription's status.
  If Stripe says `canceled` or `incomplete_expired`, set the row to `canceled` under the lock. This also covers the
  past_due-before-checkout variant.

Narrowing the rule to `past_due` / `incomplete_expired` alone does not fix this: `incomplete_expired` maps to `canceled`
in `parse_webhook`. That is why the decision has to be keyed on "was this ref ever paid", not on the status.

## Suggestions (non-blocking)

1. **The takeover cancel is lost silently on a crash and only logged on failure** (`_cancel_replaced`, lines 195-207).
   This is the intended best-effort design, but in the past_due case Stripe's smart retries keep trying the old invoice.
   If the customer's new card is now the customer's default, the old subscription can charge it again, so the customer
   pays twice. A log line is easy to miss. If the process dies between the commit and the cancel, there is no log line
   at all. Consider a durable to-do: a `pending_cancel_ref` column or a small table, retried on the next event for the
   tenant or by a sweep, and cleared on success. Until that exists, put the to-do in an alert the operator actually reads.
2. When `billing is None`, `_cancel_replaced` logs "belongs to another provider", which is the wrong message. Log a
   separate message for "no provider client".
3. `CANCEL_TIMEOUT` is also used for the period-end GET. Rename it to `WEBHOOK_CALL_TIMEOUT`.
4. **Worst-case webhook time on a takeover.** It is cancel (about 17 s) plus lookup (about 17 s), roughly 35 s, which can
   exceed Stripe's response window. This is harmless for correctness: the event id is committed first, so a redelivery
   is a no-op. The cost is noise in Stripe's dashboard. Consider doing the lookup only when no cancel happened, or
   moving both into a background task.
5. **Stale check across subscriptions (existing behaviour, worth noting).** The out-of-order check compares
   timestamps of *different* subscriptions. A paid `checkout.session.completed` for a new ref whose `created` is older
   than the old ref's last event is dropped as stale, and that new subscription then bills untracked. Takeover now
   depends on this path, so consider exempting `starts_subscription` events for a new ref from the cross-ref stale
   rule, or cancelling the new ref when it is dropped.
6. **Test gaps:**
   - Add a regression test for B1.
   - Add a test that the takeover cancel runs after the commit, for example by having the fake cancel read the row
     from a second session and check that the new ref is already there.
   - `_PeriodStripe` subclasses `MockBilling`; calling it `_PeriodLookupFake` would avoid confusion with the Stripe
     adapter.

## Checked, no issue

- Idempotency on redelivery. Takeover and period-end events are deduplicated by event id. The duplicate-cancel 503
  path still deletes the event id so Stripe retries.
- The current subscription is never cancelled. `old_ref` is captured before the row is updated, and the duplicate path
  cancels only `update.provider_ref`.
- No network call is made while the row lock is held. `_fill_period_end` commits its read before calling the provider
  and locks the row again before writing.
- The README note matches the code.

---

# Re-review: c1781b6 (B1 fix)

Reviewer: reviewer agent, 2026-11-27.

## Verdict: CHANGES

## Tests

Full suite in a clean worktree: exit 0, 781 passed, 1 skipped (`tests/test_spa.py:152`, frontend not built). The new
test `test_s3_early_cancel_of_an_untracked_subscription_blocks_its_late_checkout` covers the B1 order. The original B1
case is fixed.

## The builder's residual risk is not acceptable: staleness must be per ref

The fix stores the dead ref's event time in the tenant-wide `last_event_at`. The stale check (`occurred_at <
last_event_at`) also applies to *other* refs, so a paid subscription for a different ref can be dropped. I reproduced
this with a throwaway test (not committed):

- `customer.subscription.deleted` for sub_1 at now-10.
- Then `checkout.session.completed` (paid) for sub_2 at now-20, delivered after.
- Result: `('trialing', 'trial', None)`.

Why this matters more than the bug it fixes:

- **It is silent and nothing tracks the dropped subscription.** sub_2 is a live subscription the customer pays for every
  month. The app drops it with an INFO line ("stale billing event ignored"), never cancels it at Stripe, and the tenant
  gets no paid access. When the trial ends the customer is locked out while still being charged. Support cannot see it,
  because the row has no ref.
- **It can happen.** A trial owner opens two checkout tabs. Tab A's card fails, so Stripe leaves that subscription
  `incomplete` and later sends `incomplete_expired`, which maps to `canceled`, at t2. Tab B is paid at t1 < t2. Both
  events then sit in Stripe's retry queue during an outage and are redelivered in any order. Stripe documents that it
  does not guarantee event order.
- **The two failures are not equal.** B1's failure gives one tenant access it did not pay for. This one charges a
  customer for nothing. The second is the worse money bug, and it is the one the rule now introduces.
- **The update is too broad.** It also moves `last_event_at` forward for `past_due` events on untracked refs. That is not
  needed for B1, because a non-terminal event does not prove the ref is dead.

### B2. Make the dead-ref marker per ref

`app/routes/billing.py` lines 133-135.

1. Remove the `last_event_at` update from the S-3 branch.
2. When `update.status == "canceled"`, record a tombstone for the ref. This needs no migration: insert a
   `BillingEvent(id=f"dead:{provider}:{update.provider_ref}")` (the 255-char limit holds, because `provider_ref` is
   capped at 255 by `_check_fields`, so trim the prefix or hash if needed). Ignore an IntegrityError on a repeat.
3. Before the stale check, if a `starts_subscription` event's ref has a tombstone, ignore the event.
4. Keep the existing B1 test, and add the sub_1 dead / sub_2 paid-late test above, asserting `("active", "pro", "sub_2")`.

Optional hardening, carried over from suggestion 5 in the first review: when a paid `starts_subscription` event for a new
ref is dropped as stale, log at ERROR with the ref, or cancel it, instead of an INFO line.
