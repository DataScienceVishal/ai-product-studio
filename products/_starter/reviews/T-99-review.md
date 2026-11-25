# Review: p/_starter/T-99 (dbbe767), selling_unlocked patches every LIMITED_PROVIDERS reader

**Verdict: PASS**

## Summary

The change is test-only and touches one file. It acts on suggestion S2 from the T-94 review. The `selling_unlocked`
fixture in `backend/tests/test_hardening.py:25-32` now uses `monkeypatch.setattr` to set `LIMITED_PROVIDERS` to one shared
`{"mock"}` set in three modules: `app.billing`, `app.routes.billing` and `app.routes.notes`. The cap in `notes.py` and the
plans label in `routes/billing.py` therefore see the same unlocked configuration. The identity test in `test_billing.py`
stays green, because it does not use this fixture.

## Evidence

- `app.billing.LIMITED_PROVIDERS` exists on this tree (`app/billing.py:61`), so `setattr` with the default
  `raising=True` cannot fail silently.
- I ran `tests/test_hardening.py tests/test_billing.py tests/test_cookies_and_limits.py` and got 153 passed. The
  coordinator reports the full backend at 673 passed. I did not repeat that run.
- monkeypatch restores all three modules after each test, so nothing leaks between tests.

## Critical issues

None.

## Suggestions

None. This fixture would be a natural place to assert `trial_sized is False` on `/api/billing/plans` with
`BILLING_PROVIDER=stripe` later on, but that is optional.
