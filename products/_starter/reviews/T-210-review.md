# T-210 review: T-182 follow-ups (S1, S2, S3, S5, S6, S7)

Branch `p/_starter/T-210` at 189589c, diffed against `main` (`git diff main...HEAD`). Reviewer: `reviewer` (opus), 2026-11-28.

## Verdict: PASS

Full backend suite on this exact tree (Postgres 16, `.venv/bin/python -m pytest -o addopts="" -q` from `backend`):
**883 passed, 1 skipped, 1 warning in 125.80 s.**

## Summary

- **S1, store the event id last:** done correctly. The duplicate branch deletes the event row it flushed, commits (so the `provider_customers` row from `_record_customer` stays and the `FOR UPDATE` lock on `subscriptions` is released), makes the cancel and refund calls with no transaction open, then inserts the event id in its own short transaction. If that insert hits an `IntegrityError`, the code rolls back and treats the event as handled (`routes/billing.py:270-281`). This matches the orphan path from T-208. No lock is held while the provider calls run, so the 15 s `idle_in_transaction` timeout cannot be hit. After the commit, nothing touches the ORM between the provider calls and the final insert, so no implicit transaction starts.
- **S2, NoPaidInvoice:** the adapter now tells "no paid invoice" (raises) apart from "free invoice" (`False`) (`billing.py:498-501`). Until the event is 24 h old the route answers 503 with `refund_owed reason=no_paid_invoice`. After 24 h it acknowledges and the ERROR log stays.
- **S3, permanent vs transient:** `billing_rejected` is logged as `refund_owed` and acknowledged. Anything else (including `billing_unavailable` and unexpected exceptions) answers 503.
- **S5:** the README has a runbook for stuck pending cancels and owed refunds. The steps are in the right order (cancel at Stripe before deleting the row).
- **S6, S7:** documented in comments. The single SELECT in `_record_pending_cancel` is equivalent to the two queries it replaces.

### Money questions asked by the Lead

| Question | Answer |
|---|---|
| Lose a refund? | Never silently. Every path that acknowledges without refunding logs `refund_owed` at ERROR: no paid invoice after 24 h, `billing_rejected`, and the edge cases in suggestions 1 and 2. See suggestion 1 for one classification that is wider than it should be. |
| Double refund? | No. A redelivery reuses the per-event key. A different event for the same extra subscription (checkout.completed and subscription.created both arrive) uses a new key, but Stripe caps refunds at the charge amount (`charge_already_refunded`, which counts as done). Two deliveries running at once can both call cancel and refund; Stripe makes both idempotent. |
| Refund the kept subscription? | No. Cancel and refund take only `update.provider_ref`, and `duplicate` requires it to differ from `sub.provider_ref` (`other_sub`). |
| Loop forever? | No. The no-paid-invoice retry stops after 24 h. An event without `created` would get 503 until Stripe stops redelivering (3 days), which is bounded. Stripe always sends `created`, and the mock rejects events without it. |
| Lock across provider calls? | No (see S1 above). |

### Test changes in test_t182 (justified, not weakened)

- `test_stripe_refund_without_a_paid_invoice_does_nothing`: the `None` invoice case was removed because it now raises `NoPaidInvoice` by design. It is covered by `test_t210.py::test_stripe_no_paid_invoice_raises_but_a_free_invoice_returns_false`.
- `test_failed_refund_logs_refund_owed_answers_503_and_the_redelivery_refunds`: the error changed from `billing_rejected` to `billing_unavailable`, because `billing_rejected` is now permanent and acknowledged. The old intent (transient failure: 503, then the redelivery refunds exactly once) is kept, and the permanent case has its own test (`test_permanent_refund_rejection_logs_refund_owed_with_code_and_acknowledges`).

The new tests check behaviour: whether the event id is stored, the refund list, response codes and the log fields. They do not check implementation details.

## Critical issues

None.

## Suggestions

1. **`billing_rejected` is wider than "permanent"** (`routes/billing.py:167`, with `billing.py:352-353`). `_call` maps every non-429 4xx to `billing_rejected`, so the route also acknowledges these errors as "refund it by hand":
   - 409 `idempotency_key_in_use`: Stripe's documented answer when two requests with the same key run at once. That is exactly the "concurrent deliveries both refund" case in the builder's notes. Delivery B gets 409, logs a refund it does not owe and stores the event id. If delivery A's refund then fails transiently, A's 503 redelivery finds the id stored, and the refund is lost apart from B's ERROR line.
   - 403 from a restricted key without refund permission: the cancel works and every refund is acknowledged as owed.
   - 401 or 404.

   Fix: only 400 and 402 (invalid request and card errors such as a disputed charge) should count as permanent. Treat 401, 403, 404 and 409 as transient (503). For example, carry the HTTP status on the AppError, or add a `billing_conflict` code. This is not a must-fix, because every one of these paths logs `refund_owed` at ERROR. It is the first thing to tighten.
2. **The retry window for the start event can see a different state** (`routes/billing.py:270-281`). This existed on main for cancel or refund failures; S1 also exposes it after a crash between the cancel and the final insert. Suppose the extra subscription is already cancelled at Stripe and the redelivery comes after the kept subscription was cancelled. Then `duplicate` is False and the start event is applied: the tenant shows `active` on a subscription Stripe has already cancelled, and its `deleted` event was ignored earlier as "different subscription". The refund is then never retried. This needs two unlikely events in a short window, and it is not a regression. A later task could keep a "cancelled duplicate" marker (like the T-174 tombstone, reusing `billing_events`) before the provider calls, so a redelivery always takes the duplicate path.
3. **`occurred_at is None` counts as age 0** (`routes/billing.py:156`). Treating it as expired (acknowledge and log) would make "no `created`" fail closed for the retry loop instead of relying on Stripe's 3-day limit. This is minor.
4. **SEPA and other delayed payments can take more than 24 h to become `paid`.** Once the window ends, the ERROR line and the runbook are the only safety net. That is acceptable for the starter, and the README says so. It would be worth stating in `DATA.md` or in the billing ADR that the window is 24 h on purpose.

## Evidence

- `git diff main...HEAD --stat`: 5 files changed, +236 / -44.
- Suite: `883 passed, 1 skipped, 1 warning in 125.80s`.
