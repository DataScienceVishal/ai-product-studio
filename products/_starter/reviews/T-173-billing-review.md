# Review: `p/_starter/T-173-billing` (commit b6ff2f2)

Reviewer, 2026-11-27. Diff: `git diff 2d25a90 b6ff2f2` (merge base with `origin/main`), 5 files, +194/-20.
Scope: S1, S3, S5, S7, S8 from `reviews/T-172-billing-review.md`.

## Verdict: CHANGES

The code is correct. I found no path that grants access before payment, and none that withholds it after a real
payment, as long as the Stripe endpoint receives `checkout.session.*` events. After S5 those events are the only thing
that starts a Stripe subscription, and no README, infra file or ADR tells an operator to enable them. That is a small
docs fix (M1), but if it is missed, every paying customer silently stays on the trial.

## Evidence

- Full backend suite on the branch tree (local Postgres 16, scratch venv, `python -m pytest -q -o addopts=`):
  **`767 passed, 1 skipped, 1 warning in 105.17s`**. This matches NEXT.md and the README.
- Revert spot-checks. Each fix was undone in turn and its tests re-run, then the files were restored (checked with `cmp`):
  - S5 gate (`routes/billing.py:124` set to `if False:`), `-k "s5 or s8"`: **1 failed**, 3 passed. Only
    `test_s5_subscription_created_active_does_not_grant_access_by_itself` failed. S8 still passed (see S-1).
  - S1 delete (`routes/billing.py:155` set to `pass`): **1 failed** (`..._is_retried_by_the_provider`).
  - S3 GET fallback removed: **1 failed** (`test_s3_cancelling_an_already_canceled_subscription_counts_as_done`).
  - S7 id check removed: **1 failed** (`test_s7_...`).
- Stripe docs, checked myself on docs.stripe.com (page text treated as data only):
  - S5 is confirmed. https://docs.stripe.com/billing/subscriptions/overview, "Payment methods with delayed payment
    confirmation", says a subscription "can move directly to active after creation and bypass incomplete". The same
    page says: "For payment methods with longer processing periods, subscriptions are immediately activated. In these
    cases, the status of the PaymentIntent might be processing for an active subscription until the payment succeeds."
    So `active` on `customer.subscription.*` does not prove payment. The builder's reading is right.
  - For S3, I found no documented reply to a repeated `DELETE /v1/subscriptions/{id}`, the same as the builder.
    Confirming with a GET is the sound approach.

## Money-correctness walk-through (Stripe)

| Scenario | Result |
|---|---|
| Trial tenant, card. `subscription.created` (active) arrives, then the paid `checkout.session.completed` | created is ignored (its id is recorded; `last_event_at` and ref are untouched). Checkout starts `sub_1` as active. **Correct.** |
| The same events in reverse order | checkout starts `sub_1`. created now matches the tracked id, so it passes the gate, and it is stale (older timestamp), so it is ignored. **Correct.** |
| Bacs/SEPA: `completed` arrives with `payment_status=unpaid`, then `subscription.created/updated` (active, processing), then `async_payment_succeeded` | the first is parsed to `None` and the subscription events are ignored. Access starts only at `async_payment_succeeded`. **Correct** (`test_s5_...does_not_grant_access_by_itself`). |
| Bacs payment fails (`async_payment_failed`, then `past_due` / `incomplete_expired` for `sub_1`) | no access is granted. On a trial tenant with no ref, the `past_due` / `canceled` event is applied and the trial ends early. This behaviour predates T-173 (S-3). |
| An ignored id is later tracked | the recorded created event id only blocks that one event id. Later updates for the same id apply once checkout has set the ref. **Correct.** |
| Tracked `sub_1`: past_due, then active (card fixed) | the ref matches, so it applies. **Correct** (`test_s5_updates_...still_apply`). |
| Tracked `sub_1` past_due, new checkout `sub_2` | created `sub_2` is ignored. The paid checkout replaces `sub_1`. **Correct.** |
| Live `sub_1`, extra `sub_2` | created `sub_2` is ignored and nothing is cancelled. The paid checkout for `sub_2` is treated as a duplicate and cancelled. **Correct.** |
| `latest_invoice` expanded and `paid` | accepted as proof. Webhooks normally carry only the id, so this branch will rarely run. Harmless. |

S1, the 503 path (`routes/billing.py:141-158`). The event row is committed before the network call. After a failure,
the row is deleted and committed, then 503 is returned. No tenant row changed on this path, so a partial commit can't
leave inconsistent state, and a redelivery re-runs the same check. If `sub_1` has lapsed by then, the redelivered paid
checkout correctly replaces it with `sub_2`. A Stripe-side success with a lost reply is covered by S3: the DELETE
gets a 4xx, the GET shows `canceled`, and that counts as done. Two residual edge cases are acceptable (S-4):
- a crash or DB error between the first commit and the delete;
- a concurrent manual resend that gets `applied: false` with a 200 while the first delivery is failing.

S3 (`billing.py:348-359`). Only `billing_rejected` (a 4xx other than 404) triggers the GET, and only `status ==
"canceled"` counts as done. A live subscription re-raises the original error. Outages (`billing_unavailable`) raise
without a GET. The id is now URL-quoted. **Sound.**

S7 (`routes/billing.py:86-88`). Non-string, empty and over-255 ids get a 400 before anything is recorded. **Correct.**

## Critical issues (must fix)

**M1. Operators are never told which Stripe events the webhook needs. `checkout.session.*` is now mandatory.**
Where: `products/_starter/README.md` "Billing" section (around line 128-136, next to the portal and dunning setup
notes) and `infra/README.md` (around line 97, `billing_provider: stripe`).
Why it matters: since S5, `customer.subscription.created/updated` with `active` never starts a subscription
(`routes/billing.py:124`). If the Stripe endpoint is subscribed only to `customer.subscription.*`, which is a natural
choice and worked before this branch, every customer who pays stays on `trialing` and loses access when the trial ends.
Nothing logs an error: only an INFO line, "unconfirmed active subscription event ignored".
Fix: add a "Stripe webhook events" bullet listing exactly the events to enable:
`checkout.session.completed`, `checkout.session.async_payment_succeeded`, `customer.subscription.created`,
`customer.subscription.updated` and `customer.subscription.deleted`. It should say that without the checkout events no
subscription is ever activated. Optionally, raise that INFO line to WARNING when the tenant has no `provider_ref` and
the trial is near its end, so a missing event shows up in the logs.

## Suggestions

- **S-1. The S8 test cannot fail on the thing it names** (`tests/test_billing.py:1076-1087`). `MockBilling.cancel_subscription`
  is now idempotent (`billing.py:219-221`). With the S5 gate removed, the created `sub_2` is cancelled at r2, the r3
  cancel is a no-op, and `cancelled == ["sub_2"]` still holds. I proved this: S8 passed with the gate reverted. Add
  `assert provider.cancelled == []` right after r2. Likewise, the comment in `test_s3_second_cancel_...` ("the second
  event skips the call") is inaccurate. The second event does call `cancel_subscription`; the mock swallows it. Use a
  counting fake if "asked once" matters.
- **S-2. `current_period_end` is now usually `None` after a Stripe checkout.** Checkout events carry no period end. In the
  common order (created, then checkout) the created event is now ignored, and in the reverse order it is stale. Until
  the first renewal `subscription.updated`, `has_access` treats an active row with no period end as open-ended. If a
  `deleted` webhook is then lost, access never expires. Possible fixes:
  - let an event for the tracked id fill `current_period_end` when it is `None`, even when the event is otherwise stale;
  - or have the checkout start read the subscription with a GET.
- **S-3. (Older than T-173.)** On a trial tenant with no ref, a `past_due` or `canceled` (`incomplete_expired`) event for a
  never-paid subscription is applied and ends the trial early. Consider treating events for an untracked id like
  `other_sub` when the tenant is still `trialing`.
- **S-4.** In the 503 path, if the `delete` and `commit` themselves fail, the event id stays recorded and the cancel is never
  retried. The ERROR line is the only trace. Make the log message say so, or alert on it. Low priority.
- **S-5.** In NEXT.md, S2 (timeouts), S4 and S6 are still open. Keep them on the board.

## Security and performance

The only new input is the event id, which is validated. There are no new endpoints, authorization changes or
secrets. The GET fallback adds at most one Stripe call, and only on a rejected cancel. There are no new queries.

## Re-review at c45a86d

Commits reviewed: 16dc9f4 (the fixes), 6a05196 (merge of `origin/main`) and c45a86d (test count).

### Verdict: PASS

- **M1 is fixed.** `products/_starter/README.md` has a new "Stripe webhook setup" paragraph. It lists the five events
  exactly, and it says that without the two `checkout.session.*` events a paying customer stays on the trial.
  `infra/README.md` lists the same five events under `billing_provider` and points to the product README.
- **S-1 is fixed.** `test_s8_...` now asserts `provider.cancelled == []` after the `customer.subscription.created` for
  `sub_2`. Mutation checks on c45a86d, with the files restored afterwards (checked with `cmp`):
  - S5 gate reverted (`routes/billing.py:124` set to `if False:`), `-k "s5 or s8"`: **2 failed**, 2 passed. Both
    `test_s5_subscription_created_active_does_not_grant_access_by_itself` and `test_s8_...changes_nothing` fail.
  - `MockBilling.cancel_subscription` made non-idempotent, `-k "s8 or s3 or b1"`: **1 failed**
    (`test_s3_second_cancel_of_the_same_extra_subscription_is_not_a_false_todo`), 9 passed. S8 passes here, as it
    should: with the gate in place it cancels only once.
- **The merge kept the T-173 team content.**
  - `git diff origin/main c45a86d` touches only the six billing and docs files.
  - It shows no changes to `routes/team.py`, `models.py`, `migrations/`, `tests/test_team.py` or `reviews/`.
  - `migrations/versions/20261127_0009_invitations_email_index.py` is present.
  - The NEXT.md section "## T-173 team (branch p/_starter/T-173-team)" is present (line 375).
- **Full backend suite on c45a86d** (local Postgres 16, scratch venv, `python -m pytest -q -o addopts=`):
  **`771 passed, 1 skipped, 1 warning in 108.52s (0:01:48)`**. This matches the 771 in NEXT.md.
- **Process note:** 16dc9f4 deleted this review file (`reviews/T-173-billing-review.md`, -99 lines), probably from a
  stale working tree. This commit restores it unchanged from 5624243 and adds this section. Builders: don't delete
  review files.

Suggestions S-2 to S-5 above are still open. None of them blocks the merge.
