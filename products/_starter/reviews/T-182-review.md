# T-182 review: refund of duplicate subscriptions, deletion settles pending cancels, shared deadlines

- Branch: `p/_starter/T-182` at 53b1d1a, diff against `main` (8 files, +511 / -21)
- Reviewer: reviewer agent, 2026-11-28
- Verdict: **PASS** (no must-fix; suggestions below, S1 and S2 worth a follow-up task)

## Evidence

- Full backend suite on the exact branch tree, Postgres 16, `.venv/bin/python -m pytest -o addopts="" -q`:
  **875 passed, 1 skipped, 1 warning in 127.98 s.** Matches the README count.
- Stripe public docs checked on 2026-11-28:
  - `GET /v1/invoice_payments` takes `invoice` and `status` (`paid`), and each item carries
    `payment.type = "payment_intent"` and `payment.payment_intent` (docs.stripe.com/api/invoice-payment/list).
    The adapter's `data[0].payment.payment_intent` read matches.
  - `charge_already_refunded` is a real Stripe error code ("The charge you're attempting to refund has already been
    refunded", docs.stripe.com/error-codes). `_call` returns it on a 400 through `accept_error_codes`, which is correct.
  - Checkout `expires_at` must be 30 min to 24 h after creation. 31 min is inside that range.

## What each finding fix does, checked

| Item | Where | Result |
|---|---|---|
| M3 refund | `app/routes/billing.py:236-254`, `app/billing.py:475-507` | OK. The refund targets `update.provider_ref`, which the `duplicate` condition requires to differ from `sub.provider_ref`, so the kept subscription can never be refunded. The key comes from a hash of the event id, so a redelivery after a 503 sends the same key. A second event for the same extra subscription (new key) hits `charge_already_refunded`, so it cannot refund twice either. No DB transaction is open: the `db.commit()` before the cancel releases the row lock. |
| M3 prevention | `app/billing.py:391`, mock `:203,:215` | OK. 31 min `expires_at`; the mock returns 410 on completing an expired session. |
| L1 | `app/routes/billing.py:460-485`, `app/routes/account.py:89` | OK. The id list is committed before any provider call. Each `attempt_pending_cancel` holds one row lock for a single cancel, at most `CANCEL_WORST_CASE_SECONDS` (9 s, now a real wall-clock bound thanks to S1). That is under the 15 s idle-in-transaction timeout. No lock is held between rows or across the 20 s total. A row that stays live (a failure, SKIP LOCKED by the sweep, or the budget running out) gives a 503 and deletes nothing, so it fails closed. |
| N1 | `app/routes/billing.py:281-285`, `:351-361` | OK. The delete is scoped to this tenant or to orphan (NULL tenant) rows. Another tenant's row is logged and left alone. |
| N3/N4 | `app/routes/billing.py:369-371` | OK. `last_error` stores only the code or the class name. The refund-failure log carries only the error code. The test confirms that provider text never reaches the logs. |
| S1 | `app/billing.py:305-361, 463-475` | OK. Each try gets `min(timeout, time left)`, and no try or backoff starts once the deadline is spent. The test drives a 7 s first try and asserts the total is at most 9 s. |
| S2 | `app/routes/billing.py:449-454` | OK. The loop stops starting rows after 5 s. Note that this caps when a row may *start*, not the total: the worst case is about 5 + 9 s. |

Tests in `tests/test_t182.py` test behaviour, not implementation: the cancel and refund ledger, 503 then redelivery
without a double refund, log redaction, the fake-clock deadline, and a tenant-isolation case for both deletion and the
start-event delete. Good.

## Critical issues

None.

## Suggestions

**S1 (medium, money): a crash between the commit and the refund loses the refund for good.**
`app/routes/billing.py:147` flushes the event id, and the duplicate branch commits it (`:220`) *before* the cancel and
the refund. If the worker dies or is restarted (for example a deploy or OOM) during the ~9 s cancel plus ~12 s refund
window, the redelivery finds the event id and returns early. The extra subscription then stays charged and unrefunded,
and the only trace is the "cancelling the extra" WARNING. The cancel has had the same window since T-173, but this window
is now about twice as long and covers a refund. Fix: in the duplicate branch, commit without the event id (roll it back
or delete it, as the orphan path does at `:155-165`), do the provider calls, then insert the event id. The provider
side is already idempotent (a cancelled subscription counts as done; the refund key or `charge_already_refunded`
covers a repeat).

**S2 (medium, money): "no paid invoice" is final.** `app/billing.py:493-503` returns False, and the webhook logs it at
INFO and acknowledges. If Stripe has not yet marked the first invoice `paid` when `checkout.session.completed` is
processed, or the payment was not a PaymentIntent, nobody refunds the duplicate and no alert fires. Fix: when the
subscription's plan price is above 0 and False comes back, log `refund_owed` at ERROR (or raise 503 once, so the
redelivery retries). Keep INFO only for a provably free invoice (`amount_paid == 0` with a 100% offer).

**S3 (low, ops): a permanent refund rejection loops for days.** A non-retryable 4xx on the refund (for example
`charge_disputed`) deletes the event id and answers 503, and Stripe redelivers for about 3 days. Each delivery
re-cancels (harmless) and logs `refund_owed` at ERROR again. Consider treating `billing_rejected` (as opposed to
`billing_unavailable`) as final: log CRITICAL once and acknowledge.

**S4 (low): webhook latency.** In the worst case one webhook now runs cancel (9 s) + refund (12 s) + inline retry
(5 + 9 s), about 35 s. If the provider times out, it redelivers while the first delivery is still running. This is safe
(the event id is committed, so the second delivery is ignored), but the cap should be documented next to
`INLINE_RETRY_BUDGET_SECONDS`, or the refund moved to the sweep.

**S5 (low, UX/GDPR): one stuck pending cancel blocks account deletion forever.** This follows from failing closed,
and is the intended design. A row that the provider permanently rejects (escalated at attempts >= 10) needs an
operator path: the CRITICAL log exists, so add a note in the runbook/README that an operator must clear or hand-cancel
it before the owner can delete the account.

**S6 (nit):** `_record_pending_cancel` (`app/routes/billing.py:353-356`) runs two SELECTs for the same row. One
`select(PendingCancel.id, PendingCancel.tenant_id)` is enough. `settle_pending_cancels` ignores pending cancels for a
provider other than `billing.name`. That is fine today (one provider per deploy), but worth a comment.

**S7 (nit):** a refund key based on the subscription ref (`refund-<sha256(provider_ref)>`) instead of the event id
would make every event for the same duplicate share one Stripe idempotency key. That is slightly cleaner than relying
on `charge_already_refunded` for cross-event repeats. Optional.

## Verdict

**PASS.** Money paths are correct for the cases the task names: no refund of the kept subscription, no double refund on
redelivery or across events, and no DB lock held across provider calls longer than 9 s. The suite is green (875 passed,
1 skipped). S1 and S2 should become a follow-up board task, because each can leave a customer charged for a duplicate
without a refund.
