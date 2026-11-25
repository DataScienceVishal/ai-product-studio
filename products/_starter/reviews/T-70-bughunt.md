# T-70 bug hunt on products/_starter (time-boxed, 20 min)

Probe tests: /tmp/claude-0/-home-user-ai-product-studio/30953883-273e-59e5-940b-a0279dbfe073/scratchpad/qa/test_probe.py and test_probe2.py
(copy into backend/tests/, run `pytest tests/test_zz_probe*.py -s`; they reuse the `owner`, `new_client`, `app` fixtures).

## Confirmed bugs

### 1. NUL character in text input returns HTTP 500 (Medium)
Postgres text cannot hold U+0000; nothing rejects it before the insert.
- `POST /api/notes {"title":"a\u0000b","body":"x"}` -> 500 internal_error (expected 422).
- `POST /api/notes {"title":"ok","body":"x\u0000y"}` -> 500 (same for PUT).
- `POST /api/auth/login {"email":"a\u0000@z.test","password":"x"}` -> 500 (expected 401/422).
- `POST /api/auth/signup` with email `a@b.cc\u0000` -> 500 (the email regex only excludes whitespace, and NUL is not `\s`).
Any authenticated user (or anonymous, on login/signup) can generate error-level logs and 500s at will.
Likely fault: backend/app/routes/notes.py:30-32 (NoteIn), app/routes/auth.py:25 (EMAIL regex) and :37. Fix: shared validator rejecting `\x00` for all str fields.
Related: signup `company_name` with `\u0000` returned 201, so it is being stored or stripped somewhere. Check how (auth.py SignUp model).

### 2. Whitespace-only note title accepted, saved as empty string (Low)
`POST /api/notes {"title":"   "}` -> 201 with `"title": ""`. `min_length=1` is checked before `.strip()`.
Expected 422. Fault: notes.py:30-32 and :64, :80 (strip after validation). Signup already rejects a blank company name.

### 3. Malformed but correctly signed webhook payloads return 500 (Low)
Needs a valid signature, so not an external attack. A provider bug or replayed odd event would turn into retries and error logs.
Each of these, sent with a valid `x-billing-signature`, gives 500:
- body `[]` or `"str"` (`event.get` on non-dict), billing.py:168 (Mock) and :313 (Stripe)
- event without `id` (KeyError at `event["id"]`, billing.py:179 / :324)
- `data.current_period_end = 10**18` (`datetime.fromtimestamp` ValueError/OverflowError, billing.py:177 Mock; `_period_end` :307 Stripe)
- `created = 10**18` also gave 500 in my run.
Expected: 200 `{"received":true,"applied":false}` or 400. Fix: wrap parse in try/except (ValueError, KeyError, AttributeError, OverflowError, OSError) and use `_when()` for period end.

### 4. Same-second ordering: cancel then checkout with equal `created` reactivates (Low)
billing.py/routes/billing.py:77 uses `occurred_at < last_event_at`, so an equal timestamp is applied.
Repro: webhook `subscription.canceled` created=T, then `checkout.completed` created=T (id different) -> status goes back to `active`.
Stripe timestamps are whole seconds, so same-second events are plausible. Expected: a deterministic rule (for example, treat equal as stale for checkout.completed, or use the event type's priority).
Also: after a cancel, an older (T-5) checkout is correctly ignored (held up).

## Held up (probed, no bug)
- Cross-tenant note GET/PUT/DELETE/summarize by guessed id: all 404.
- Member role: GET /api/team 200 (own tenant only, no invitations list); account export, checkout, invite all 403.
- CSRF: cookie-authenticated POST/DELETE without X-Requested-With: 403.
- Invites: single use, expired, revoked, replaced by re-invite, invite for registered email (existing tests, plus my accept probe 201 once only).
- Password reset confirm signs out all sessions (read code; my probe 422 was wrong field name `password`, real field is `new_password`).
- Bad UUID path, negative limit, huge offset: 422. 20,001-char body: 422. 5 MB body: 413. Webhook limited to 256 KB.
- Unicode (Hindi, Tamil, Urdu, emoji) notes: 201. IDN-ish email accepted.
- AI caps: all checks use `> cap`, so use exactly equal to the cap is allowed and one token over is refused; per-tenant advisory lock. Not exercised at runtime beyond reading ai.py:454-489.
- Webhook with signature wrong or absent, unknown tenant (sub None path returns applied True), replayed event id (applied False) covered by code reading and existing tests.

## Unconfirmed (suspicions)
- A signed-in user B who accepts an invitation to tenant A is moved into A (201, /me shows Acme). Their old tenant becomes orphaned if B was its only owner (with notes, subscription). It may be intended, but there is no warning. Test: probe2 "B accept while signed in". Worth a product decision; not necessarily a bug.
- Failed or crashed AI calls leave `model="pending"` usage rows counting their full estimate against monthly/daily caps with no sweep (ai.py:485). Could not confirm that a crash path exists outside process kill.
- Event with `"id": {"a":1}` is accepted as applied (str() of dict). Harmless.
- Webhook `plan` unknown with `status active` activates the subscription while keeping the old plan (billing route apply_update :86-87). Possible free upgrade if provider metadata is wrong.
- Not tested: concurrent double-click on checkout/invite, real browser, frontend.
