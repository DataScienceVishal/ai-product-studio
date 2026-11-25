# T-72 build: billing and auth follow-ups

Branch `p/_starter/T-72-billing-auth`. Backend suite: `cd products/_starter/backend && .venv/bin/python -m pytest`
gives 535 passed, 1 skipped. Frontend untouched.

## Item 1 (money bug): FIXED
`apply_update` (app/routes/billing.py) now compares `provider_ref`. An event for a different subscription id than
the tenant's current one is ignored unless it is an activation: an old subscription's cancel or past_due cannot
touch the current one, and a newer activation with a new ref replaces the ref (and is exempt from the
same-second cancel-wins tie-break, since it is not a reactivation of the cancelled subscription).
Tests (5 new): old-sub delete after new checkout, old-sub past_due, same-second old-cancel then new activation,
same-second new activation then old-cancel, current-sub cancel still works. Checked: with the fix removed, the
first four fail on main's code; the fifth is the control.

## Item 2: triage
- (a) invite accepted by a signed-in user: NOT REAL. Accept always creates a new user for the invited email; an
  invite for an email that already has an account is refused (409), so nobody is moved or orphaned. Two tests added.
- (b) pending AI rows: PARTLY REAL. Failure paths already settle the row (test added). A killed process leaves a
  "pending" row that counted forever. Fixed: `release_stale_reservations` zeroes pending rows older than 15 minutes
  (marked `abandoned`), run in `reserve` per tenant and in the daily purge. Tests fail without the fix (checked).
  Trade-off: a killed call's real cost is not counted after 15 minutes (bounded by one estimate). DATA.md updated.
- (c) unknown plan on an active event: REAL. Now rejected with 400 `unknown_plan` and an error log, before the
  event id is recorded, so a corrected redelivery applies. Cancel events with an unknown plan still cancel.
  Tests added (fails on main, checked).

## Item 3: T-71 nits: DONE
OSError comment; `_CONTROL` removed (auth imports `textsafe.LINE_BAD`); out-of-range-created test asserts 400 and
is renamed; invalid-JSON test renamed; blank-title tests now use values the old model accepted ("   ", NBSP, EM
space) and the strip test checks create, edit and list; company-name test pins the resulting names.

## Review round 2 (reviewer CHANGES, C1)
- C1 FIXED: `BillingUpdate.starts_subscription` (true only for mock `checkout.completed`, Stripe
  `checkout.session.completed` and `customer.subscription.created`). Only those may replace `provider_ref`/plan or skip the
  same-second tie-break; any other event for a non-current subscription id (cancel, past_due, an old sub becoming
  active again) is ignored. Tests: the reviewer's 5-step scenario in Stripe payload shape (fails with the old rule,
  checked), Stripe old-sub deleted plus replay returning applied false, `subscription.created` for a new id takes over.
- S7 done: an active event with plan `trial` is refused (`unknown_plan`).
- S4/M6: `reserve` docstring states it commits on refusal; new test fails if `refuse` goes back to `rollback` (checked).
- S6: test that a call settling after being swept restores its real cost.
- Noted follow-ups, not done: S1 (checkout while past_due can create a second paid subscription: refuse with 409 or
  close the old ref), S5 (partial index for the sweep when volume grows).
- Suite: 541 passed, 1 skipped.
