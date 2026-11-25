# Review: p/_starter/T-71-bughunt-fixes (head c7a9cf1)

Reviewer: reviewer agent, 2026-11-25. Diff: `git diff origin/main...HEAD` (6 files, +181/-7).

## Verdict: PASS

All four T-70 findings are fixed. Each regression test fails when its fix is taken out. The full suite is green. Nothing below blocks the merge. The suggestions are small follow-ups.

## Evidence

- Full backend suite on the branch: `518 passed, 1 skipped in 59.55s`
- Mutation checks. I made each edit in a scratch copy of `backend/` and never touched the worktree:
  - M1, tie-break removed (`or tie_after_cancel` dropped): `1 failed, 1 passed`. `test_same_second_checkout_after_cancel_does_not_reactivate` fails. The cancel-second test passes, as it should, because it is the control case.
  - M2, webhook `except (ValueError, ...)` disabled: `6 failed`. These are all 4 malformed-event params, the out-of-range `created` test and the invalid-JSON test.
  - M3, note fields set back to `str`: `5 failed, 13 passed`. Those are NUL in title and body, the other-control-chars test, and blank titles `"   "` and `"\t \xa0"`. The `""` blank case and `test_note_title_is_stripped` pass without the fix, so the old model already covered them. They guard against regressions but do not test this change.
  - M4, auth `SafeLine` and `_CONTROL` removed: `10 failed`. These are all 9 NUL-email cases on login, reset and signup, plus the invite.

## Questions asked

### 1. Is 400 right for a correctly signed but malformed event?
Yes. Keep 400 and do not switch to 200-and-log.
- A real Stripe event always has `id`, `created` and an object payload. So a signed event that our parser cannot read means our parser is wrong (for example after an API-version change), not that the event is junk.
- A non-2xx makes Stripe retry for up to 3 days. That window lets us ship a parser fix and still apply the event.
- 200-and-log would drop a real billing change for good, and the subscription row would drift from Stripe without anyone noticing. Losing billing data is worse than a few days of retries and Stripe's failing-endpoint emails.
- With the default mock provider, only our own code sends these events, so a clear 400 is the right answer.
- The old behaviour was a 500. That is also non-2xx, so retries happened before too, but with an error-level stack trace each time. The new path logs at warning level with `exc_info`, which is enough to diagnose.
- Note: invalid JSON was also a 500 before this branch. Mutation M2 shows this, because `test_webhook_invalid_json_and_bad_signature_behaviour_unchanged` fails without the fix. The test name says "unchanged" but it actually tests a fix. Renaming it is optional.

### 2. Does the tie-break have a hole?
I found no hole in the cases it targets.
- Cancel arrives second at the same timestamp: the row is `active`, the update is `canceled`, so `tie_after_cancel` is False and the cancel applies. The test covers this.
- `customer.subscription.updated` with status `active` or `trialing`, or `past_due`, at the same second after a `deleted`: the row is `canceled` and the update is not `canceled`, so the update is ignored. Good.
- `updated` with status `canceled` after `deleted`, same second: it applies, which does no harm.
- Ties that do not involve a cancel (checkout versus past_due in the same second) still go last-writer-wins. That is acceptable.

Gaps that already existed and that this branch does not widen (follow-ups, not blockers):
- `apply_update` does not compare `update.provider_ref` with `sub.provider_ref`. A `deleted` event for an *old* subscription (s1) that is strictly newer than a checkout for a *new* subscription (s2) would cancel a paying customer. The same-second rule makes this a little more likely: a s1 deletion applied first blocks the s2 checkout that follows in the same second. Fix: ignore a cancel or update whose `provider_ref` is set and differs from the row's current `provider_ref` when the row is active.
- If `occurred_at` is None, the order check is skipped entirely. `_when` returns None for bad or overflowing `created`, but it does not catch `OSError`. That is why the 10**18 case now reaches the new 400 path instead of being applied with no timestamp, which is the better outcome. Consider making it explicit: an event without a usable `created` should be rejected rather than applied with no ordering.

### 3. Does SafeLine on the login email change behaviour for valid emails?
Yes, in one narrow case. `SignIn.email` and `ResetRequest.email` are now `SafeLine`, which checks for control characters *before* the route's `.strip().lower()`. I ran a probe test against the branch:
- `" Probe@Acme.test "` with spaces: login returns 200, unchanged.
- `"probe@acme.test\n"` with a trailing newline or tab: login returns **422**. Before this branch it returned 200.

Signup accepts the same input, because `_email` strips before its `_CONTROL` check. So you can sign up with a value that you then cannot log in with. Real-world impact is small, because browser `type=email` inputs strip surrounding whitespace, but API clients and pasted values can hit it. Fix: use `StrippedLine` for those two fields, which strips first and then checks. The 422 on reset-request does not leak whether an account exists, because the answer depends only on the input.

## Critical issues
None.

## Suggestions
1. `app/routes/auth.py:57,62`: use `StrippedLine` instead of `SafeLine` for `SignIn.email` and `ResetRequest.email`, so login and reset handle surrounding whitespace the same way signup does (see question 3).
2. `app/routes/billing.py` `apply_update`: check `provider_ref` before applying `canceled` or `updated` events, so an old subscription cannot cancel a new one (an existing gap that the tie-break makes slightly worse).
3. `app/routes/billing.py`: catching `OSError` is fine because `parse_webhook` does no I/O, but add a short comment that it covers `datetime.fromtimestamp` on huge values, so nobody later widens the try block around DB or network calls.
4. `app/routes/auth.py:28`: `_CONTROL` repeats `textsafe._LINE_BAD`. Import one pattern from `textsafe` instead.
5. `tests/test_billing.py`: `test_webhook_with_out_of_range_created_is_not_a_500` accepts 200 or 400. Assert the one intended answer (400 today). Rename the "unchanged" invalid-JSON test.
6. `tests/test_text_input.py`: `test_company_name_control_chars_are_normalised` only checks that NUL is gone. Also assert the resulting name, so the normalisation rule is pinned.
