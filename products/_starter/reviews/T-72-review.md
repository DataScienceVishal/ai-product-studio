# T-72 review: billing provider_ref, unknown plan, abandoned AI reservations, T-71 nits

Reviewer, 2026-11-25. Branch `p/_starter/T-72-billing-auth` at 8bf98b8, diff `main...8bf98b8` (12 files, +254/-20).

**Verdict: CHANGES** (one blocking item: the money bug is narrowed, but the same failure is still reachable through another path).

## Evidence

- Full backend suite in a clean worktree: `python -m pytest -q -o addopts=""` gives **535 passed, 1 skipped in 67.8 s**
  (matches the builder's numbers).
- Mutation testing (each change made alone, then reverted):

| Mutation | Result |
|---|---|
| M1 `other_sub = False` (no ref comparison) | 4 new billing tests fail (the 5th is the control) |
| M2 drop `and not other_sub` from the tie-break | `test_same_second_old_cancel_then_new_activation_ends_active` fails |
| M3 remove the unknown-plan check | `test_active_event_with_unknown_plan_is_refused_and_can_be_redelivered` fails |
| M4 no sweep in `reserve` | `test_abandoned_reservation_stops_counting_against_the_cap` fails |
| M5 `STALE_RESERVATION = 0` | `test_a_recent_reservation_still_counts` fails |
| M6 `refuse` back to `rollback()` | **survives** (no test covers it; see S4) |

The regression tests test behaviour and fail without the fix. Good work there.

## Critical (blocking)

### C1. An old subscription that becomes active again takes over, then its cancel cancels the paying customer
`app/routes/billing.py:84-85`. Any `active` event with a different ref is treated as a *new* subscription and
replaces `provider_ref` (and the plan). Only cancel/past_due are ignored. But an old subscription can produce an
`active` event after a new one exists:

1. s1 goes `past_due`.
2. Checkout is allowed while past_due (`billing.py:43` only blocks `active`), so the customer pays for s2 (plan pro).
3. Stripe's retry of s1's invoice succeeds: `customer.subscription.updated` with `status=active` for s1. Stripe also
   sends `subscription.updated` (still active) for metadata edits or `cancel_at_period_end` toggles.
4. That event has `other_sub=True, status=active`, so `provider_ref` becomes s1 and the plan drops to s1's plan.
5. s1 is later deleted, and that event now matches the current ref: **the customer is cancelled while s2 is still
   charging them.**

I reproduced it with a throwaway test (mock events e1 checkout s1, e2 past_due s1, e3 checkout s2 pro, e4 active s1,
e5 cancel s1, in increasing timestamps). Output: `after s1 recovers: active starter` (pro downgraded),
`after s1 deleted: canceled starter`. This is the exact failure T-72 item 1 set out to stop.

**Fix:** let only an event that *starts* a subscription take over the ref. Add `starts_subscription: bool = False`
to `BillingUpdate` (`app/billing.py:72-80`). Set it True for mock `checkout.completed` and for Stripe
`checkout.session.completed` and `customer.subscription.created`. Leave it False for `customer.subscription.updated`
and every cancel or past_due event. Then in `apply_update`:

```python
if other_sub and not update.starts_subscription:
    db.commit(); log.info("event for a different subscription ignored"); return True
```

Use the same flag for the tie-break exemption at line 91. I tried the simpler guard
`other_sub and (status != "active" or sub.status == "active")` first. It breaks 4 of the builder's tests, because
those tests rightly cover s2 being bought while s1 is still active (a provider switch, line 43), so keying on the
event kind is the right cut. Add regression tests:
(a) the 5-step scenario above, with e4 as a Stripe-shaped `customer.subscription.updated` for s1, must end active on
s2/pro; (b) with s2 current, an `updated`/active event for s1 changes neither the ref nor the plan. S1 covers stopping
the double subscription from forming at all.

## Suggestions (non-blocking)

- **S1** `routes/billing.py:43`: checkout while `past_due` with a live `provider_ref` creates a second Stripe
  subscription, so the customer is billed twice. Either refuse (409, "update your card" via the portal) or cancel the
  old ref with `billing.close(None, old_ref)` once the new activation lands. Log it as a follow-up if it's out of scope.
- **S2** Stripe-format coverage: the new tests use only the mock event shape. Add one test that feeds
  `customer.subscription.deleted` for an old `sub_...` id through `StripeBilling.parse_webhook`, so the
  `provider_ref=obj["id"]` versus `obj["subscription"]` mapping (`billing.py:323/333`) is pinned for the old-sub case.
- **S3** Replay of an ignored event: add an assertion that redelivering the ignored old-sub cancel returns
  `applied: false`. I checked by hand that it does, but nothing pins it.
- **S4** `ai.py:490`: `refuse` now commits instead of rolling back. That is safe today, because the only caller
  (`routes/notes.py:114`) does only reads before `reserve`. But it is a quiet contract: any future caller that writes
  before calling `reserve` would have those writes committed on a 429. Say so in the docstring ("commits on refusal
  too") or add a test. M6 survives.
- **S5** `ai.py:464-468`: the per-call sweep filters `tenant_id, model='pending', created_at < now-15m`. It uses
  `ix_ai_usage_tenant_created` as a range from the start of history (rows are kept 400 days), so every AI call scans
  the tenant's whole history under the advisory lock. That is fine at starter scale. When volume grows, add a partial
  index `(tenant_id, created_at) WHERE model = 'pending'` in a migration.
- **S6** Abandoned sweep versus a slow call: this is safe. `settle` (`ai.py:515`) overwrites the row by id whatever
  its `model`, so a call that finishes after being marked `abandoned` restores its real cost. The 15-minute window is
  3x the 300 s maximum deadline, plus 2 s for the slot wait. Worth one test: sweep, then `settle`, then the row
  counts. That would pin this property.
- **S7** `routes/billing.py:62`: `"trial"` is in `PLANS`, so an `active` event with `plan="trial"` passes the new
  check and sets an active subscription to the trial plan. That is not a free upgrade (it is the smallest allowance),
  but checkout refuses `trial` (line 46), so the webhook should too (`update.plan == "trial"` → `unknown_plan`).
- **S8** `mock_complete` (`routes/billing.py:165`), the risk the builder flagged: the plan comes from a session
  created by `checkout`, which already validated it against `PLANS`, and sessions live in memory, so a catalogue
  change on restart also drops them. In practice the 400 can't be reached there, and if it were, an `AppError` 400
  is the right answer. No change needed.

## Checked and fine

- Event ordering and the same-second tie-break still behave as in T-71 for same-ref events. A past_due on the current
  sub applies (`other_sub` is False). A tenant with no `provider_ref` yet is unaffected (`other_sub` needs both refs).
  An event with no ref falls back to the old behaviour.
- Unknown-plan refusal happens before `BillingEvent` is added, so a corrected redelivery with the same id applies
  (tested). Stripe will retry the 400 for up to 3 days, which is the intended effect. Cancel events with an unknown
  plan still cancel.
- Purge sweep runs in the same transaction as the other purges, and concurrent sweeps are serialised by row locks.
- Invite triage tests and T-71 nits (`LINE_BAD` shared, tighter asserts, renamed tests): correct and behavioural.
- Security: no new endpoints, and the logs don't leak secrets or personal data (the plan string is truncated to 40 characters).
