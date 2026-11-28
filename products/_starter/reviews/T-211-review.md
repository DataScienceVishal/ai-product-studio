# Review: p/_starter/T-211 (HEAD 8472be8) against main

Reviewer run, 2026-11-28. Scope: suggestions 1, 3 and 4 of `reviews/T-210-review.md`.

## Summary

- `AppError.provider_status` added (`app/errors.py:13-17`), set only by `StripeBilling._call` on a non-accepted 4xx (`app/billing.py:353-354`). Other `billing_rejected` raises (unreadable or incomplete 2xx replies, coupon mismatch) leave it `None`.
- Refund path (`app/routes/billing.py:165-179`): permanent (ack + ERROR `refund_owed`) only when `billing_rejected` and `provider_status in {400, 402}`; everything else answers 503 so Stripe redelivers.
- No-paid-invoice window (`app/routes/billing.py:156-164`): `occurred_at=None` now counts as expired (`will_retry=False`, ack). This closes the endless-retry hole from T-210.
- README runbook updated to match.

Tests: `.venv/bin/python -m pytest -o addopts="" -q` on this tree with Postgres 16 gave **888 passed, 1 skipped** (127 s). That matches the README figure.

## Money checks

| Risk | Finding |
|---|---|
| Lost refund | Every path that does not refund logs ERROR `refund_owed` with the subscription ref, so an operator can find it. A permanent 400/402 is acknowledged once, with an operator line. A transient one keeps logging on every redelivery until Stripe stops (about 3 days); after that, the last ERROR line is the record. Nothing is silently dropped. |
| Double refund | Safe. Retries reuse `refund_key(event_id)`. If the 24 h Stripe idempotency key expires mid-redelivery, the second POST `/refunds` for the whole payment_intent gets `charge_already_refunded`, which the adapter treats as done (`billing.py:513-515`). The 409 test proves one refund after a transient failure and a redelivery. |
| Infinite loop | None. The no-timestamp hole is closed. Transient 4xx and missing-status cases are bounded by Stripe's redelivery limit, not by our code. |
| Provider text in logs | Unchanged and fine. Only `error.code` is logged, and `provider_status` is an int. The tests check that `4242` and `idempotency` stay out of logs and messages. |

## Builder's two notes: verdict

1. **A non-400/402 4xx (401/403/404/409/...) retries for about 3 days, logging `refund_owed` each time.** Acceptable. 401/403 are key or permission problems that heal once the config is fixed. 409 is a concurrent idempotent request. 404 could be permanent, but retrying it costs nothing and cannot double-refund. Repeated ERROR lines are noisy but they are the alert we want. No change needed.
2. **`billing_rejected` without `provider_status` is treated as transient on the refund path.** Acceptable, and it is the safer choice. On this path, the status-less case is a 2xx that `_call` could not parse (`billing.py:358`). The refund may already have happened, so retrying with the same key, or getting `charge_already_refunded` after the key expires, is the right way to find out. Acknowledging it would risk recording a refund we cannot confirm.

## Critical issues

None.

## Suggestions (non-blocking)

1. `tests/test_t210.py`: `test_400_and_402_refund_rejections_are_acknowledged_as_refund_owed` only exercises 402. The existing T-210 test now covers 400 (`provider_status=400`), so behaviour is covered, but either parametrize this test over (400, 402) or rename it.
2. `test_no_paid_invoice_without_a_timestamp_is_treated_as_expired` also takes `database` and `client` fixtures it does not use. Its inline imports could move to the top of the module.
3. Optional: add `provider_status` to the `refund_owed` log `extra`. It is an int, so it is safe, and it would let an operator tell 401 (fix config) from 404 (refund by hand) without opening Stripe.

## Verdict

**PASS**
