# T-179 security and privacy pass: product starter changes since 69c9f50 (T-172 to T-178)

- Scope: `git diff 69c9f50..main -- products/_starter` (main at e168afe). This covers duplicate and takeover subscriptions,
  dead markers, `needs_paid_confirmation`, `checkout.session.async_payment_succeeded`, `pending_cancels` (migrations
  0010 and 0011), the cancels sweep and its Container Apps job, invite and accept locking (migration 0009), and the
  `purge-job.sh` follow changes. Files reviewed: `backend/app/billing.py`, `backend/app/routes/billing.py`,
  `backend/app/routes/team.py`, `backend/app/routes/account.py` (deletion, as it interacts with the new billing state),
  `backend/app/maintenance.py`, `backend/app/models.py`, `backend/app/db.py`, migrations 0009-0011, `infra/main.bicep`,
  `infra/main.bicepparam`, `infra/purge-job.sh`, `infra/deploy-role.bicep`, `README.md` and `DATA.md`.
- Earlier findings are not repeated. A5 (the invite `email_taken` oracle) is pre-existing and out of scope.
- Reviewer: security agent, 2026-11-27. I did not modify any product code. The probes were written in the scratchpad,
  copied into `backend/tests/` for one run each, then deleted. `git status` was clean afterwards.

## Verdict: CHANGES

There are 0 high, 3 medium, 1 low and 5 nits. **Nothing is exposed right now.** The starter is not deployed, Stripe is
test-mode only, and no secret appears in the diff, so nobody needs to ping Vishal. The mediums concern real customers'
money and personal data once Stripe test mode becomes live mode, so fix them before the selling ADR.

What passed:
- **Webhook signature.** It is unchanged and still HMAC with a 300 s tolerance and constant-time compare. The event id
  is now type-checked (`_check_fields`) before it is recorded.
- **Replay and dedup.** These hold. On a failed duplicate cancel the dedup row is removed only so that Stripe's
  redelivery retries the cancel.
- **Out-of-order events.** The `FOR UPDATE` on the subscription row plus `last_event_at` and the tie-break still order
  events correctly.
- **Activation without payment.** `needs_paid_confirmation` and the `payment_status` gate stop delayed-payment
  activation. A new subscription only becomes current through a paid checkout event.
- **Dead markers.** They are sha256-hashed into `billing_events` and cannot collide with real event ids.
- **Team invites.** They are tenant-scoped, and the cross-tenant revoke on accept only touches rows for the same,
  now-registered email.
- **Infrastructure.** The cancels job gets no AI key (`AI_PROVIDER=fake`, no `azure-openai-api-key` secret). Secrets
  are referenced through `secretRef` only. `purge-job.sh` validates every value with a strict regex before it reaches
  `$GITHUB_ENV` or a command line, and its read-back prints only names and `secretRef` names, never values.
- **`deploy-role.bicep`.** The change is a comment only.

## Findings

### M1 (medium, privacy and money): a takeover or duplicate leaves a second Stripe customer that account deletion never removes
- Where:
  - `backend/app/billing.py:306-327`: `create_checkout` never sends `customer`, so every subscription-mode Checkout
    creates a new Stripe Customer.
  - `backend/app/routes/billing.py:226-227`: a takeover overwrites `provider_customer` with the new customer.
  - `backend/app/routes/billing.py:188-210`: the duplicate path cancels only the extra subscription and never records
    its customer.
  - `backend/app/routes/account.py:64-68`: deletion closes only the one stored customer.
- Failure scenario A (takeover): the tenant pays, sub_1 on cus_A goes past_due, and they buy again (sub_2 on cus_B).
  The app cancels sub_1, but cus_A stays at Stripe with its name, email, billing address and saved card. When the
  tenant deletes their account, only cus_B is deleted. cus_A (personal data at a processor) is kept for ever. This
  contradicts DATA.md: "account deletion (the provider customer is deleted first)". If the sub_1 cancel is still
  failing at that moment (see L1), the old subscription can keep charging a card on a customer that the app no longer
  references anywhere except `pending_cancels.ref`. The customer cannot reach it through the portal either, because
  the portal opens cus_B.
- Failure scenario B (duplicate): two checkout tabs are both paid. sub_2 is cancelled, but cus_B is never stored, so it
  is never deleted.
- Evidence (probes `test_p1`, `test_p2`, both passed, which confirms the gap):
  - Takeover: after it, the subscription row is `('active', 'sub_2', 'cus_B')` and `cancelled: ['sub_1']`. After
    `DELETE /api/account` (204), `closed: [('cus_B', 'sub_2')]` and cus_A is never closed.
  - Duplicate: after it, the row is `('active', 'sub_1', 'cus_A')` and `cancelled: ['sub_2']`. After the delete,
    `closed: [('cus_A', 'sub_1')]` and cus_B is never closed.
  - Stripe's API reference for creating a Checkout Session says that in subscription mode, if `customer` is blank,
    Checkout creates a new Customer (https://docs.stripe.com/api/checkout/sessions/create, accessed 2026-11-27).
- Fix, preferred: pass `customer=<sub.provider_customer>` in `create_checkout` when the tenant already has one for this
  provider. Then all subscriptions share one Customer, and deleting it cancels them all.
- Fix, additionally: store the customer ref on `pending_cancels`, and record the duplicate's customer so the cancel
  path can delete it. Add a test that a takeover followed by deletion closes every customer the tenant ever had.
- Fix the DATA.md `subscriptions` row so it says exactly which customers are deleted.

### M2 (medium, money): a slow provider makes Postgres kill the cancel transaction, so failed attempts are never counted and the operator alert never fires
- Where:
  - `backend/app/routes/billing.py:273` (the row is locked with `FOR UPDATE`) through `:291` (the provider call) and
    `:296` (the commit). The transaction stays open across the provider call.
  - `backend/app/db.py:24` (`idle_in_transaction_session_timeout` defaults to 15 s, and `maintenance.main` does not
    override it).
  - `backend/app/billing.py:231,367`: the cancel can take 8 s + 1 s + 8 s = 17 s, which is more than 15 s.
- Failure scenario: Stripe's API hangs on reads. Each attempt waits two 8 s read timeouts, so the cancel takes about
  17 s. Postgres ends the idle-in-transaction session at 15 s. The failure path's `db.commit()` then raises
  `25P03`, so these never happen:
  - `attempts` is not incremented and `last_attempt_at` is not set.
  - The backoff never applies, so the sweep retries every 30 minutes.
  - The webhook's `attempts < 3` limit never bites, so every billing event for the tenant spends 17 s on it.
  - `ESCALATE_AT` never reaches 10, so the CRITICAL "pending cancel needs operator" line never appears.

  Meanwhile the old subscription can keep billing the customer. The row lock is also released mid-call, which reopens
  the takeover race that T-175 used the lock to close.
- Evidence (probe `test_p4`): a `Database` with `idle_in_transaction_timeout_ms=1000` stands in for 15 s, and a cancel
  sleeping 2 s stands in for 17 s. Results:
  - Three sweeps returned `{'cancelled': 0, 'failed': 1}` each.
  - The row was `attempts=1` with the same `last_attempt_at` before and after.
  - The log showed `pending cancel could not be processed ... InternalError: database error (sqlstate 25P03)`.
  - There was no CRITICAL line.
- Fix: keep the provider call shorter than the idle timeout. Options:
  - cap the cancel budget at about 10 s: one attempt with an 8 s timeout inside this lock, or `CANCEL_TIMEOUT` of 4 s
    with 2 attempts;
  - or run the sweep's session with a larger `idle_in_transaction_timeout_ms` (for example 60 s), and keep the webhook
    inline retry under 15 s;
  - or claim the row with a short "in progress until" lease column, commit, call the provider, then record the result
    in a new transaction.

  Whichever option, also count an attempt when the record-the-failure commit itself fails: re-read the row in a fresh
  transaction and increment it. Add a test along the lines of the probe.

### M3 (medium, money): a duplicate subscription is cancelled after it was paid, with no refund and no operator prompt
- Where: `backend/app/routes/billing.py:188-210` and `backend/app/billing.py:358-372`. `DELETE /v1/subscriptions/{id}`
  cancels the subscription but does not refund the invoice already paid.
- Failure scenario: the owner opens two checkouts (two tabs, or the back button and choose plan again). A Checkout
  Session stays open for 24 h by default, and the `already_subscribed` check at `:64` only runs when a session is
  created. The owner pays both. The second subscription is detected as a duplicate and cancelled, but its first
  invoice (for example £79) stays charged. The only signal is a WARNING, "duplicate subscription ... cancelling the
  extra", which does not say a refund is owed. README presents duplicates as handled. Probe `test_p2` confirms that the
  cancel happens and that nothing else records the payment.
- Fix: in the duplicate path, refund the extra subscription's latest paid invoice. In test mode that means
  `POST /v1/refunds` with the invoice's payment intent and an idempotency key from the event id. Or, at minimum, log
  ERROR "refund owed" with the subscription id and say so in README.
- Prevention: with M1's fix (pass `customer`), expire the tenant's other open Checkout Sessions on completion
  (`POST /v1/checkout/sessions/{id}/expire`), or set a short `expires_at` (30 minutes) on each session.

### L1 (low, privacy and money): account deletion succeeds while a pending cancel for the tenant is still failing
- Where: `backend/app/routes/account.py:64-72`. Deletion closes only the current customer and does not look at
  `pending_cancels`.
- Scenario: the tenant has a pending cancel with 12 failures (escalated) and deletes the account. They are told
  everything is gone. The old subscription may still be live at Stripe, and the row stays indefinitely with
  `tenant_id` NULL. Probe `test_p3` showed the delete returning 204 and the rows
  `[(None, 'sub_1', 12, 'RuntimeError: down')]`.
- DATA.md does document that the row outlives the tenant, so the retention claim is accurate. The gap is that the user
  is not told.
- Fix: in `delete_account`, try the tenant's pending cancels synchronously (like `close`) and fail closed with the same
  503 if one is still live. Or, at minimum, log ERROR with the ref, so the operator's manual cancel at the provider
  covers it.

### N1 (nit): pending-cancel delete and dedup are not tenant-scoped
- Where: `backend/app/routes/billing.py:236-237` and `:259`. Both key on `(provider, ref)` only.
- This is not exploitable: refs are unique at Stripe and metadata is set server-side in signed events. For defence in
  depth, add `PendingCancel.tenant_id == update.tenant_id` (or `IS NULL`) to the delete, so a mis-attributed event
  can never drop another tenant's to-do.

### N2 (nit, least privilege): the cancels job gets secrets it does not need
- Where: `infra/main.bicep` (`cancelsStripeEnv`, `cancelsSecrets`). The job receives `BILLING_WEBHOOK_SECRET`, which it
  never verifies with but which Settings require. It also receives the full `sk_test_` key.
- Fix:
  - When the Stripe test keys are created, give the job (and ideally the web app) a restricted `rk_test_` key that is
    limited to Subscriptions write, Customers write and Checkout Sessions write. The adapter already accepts `rk_test_`.
  - Consider making the webhook secret optional when the process is a maintenance command.

### N3 (nit): the README test count is stale
- `README.md:36` says 820 passed, 1 skipped. Measured today: **825 passed, 1 skipped**.

### N4 (nit): the "no provider text" claim for `last_error` holds only by convention
- Where: `backend/app/routes/billing.py:294` stores `f"{type(error).__name__}: {error}"`.
- The claim is true today: `AppError` messages are fixed, and httpx errors are wrapped in them. A future adapter that
  raises with the provider's message (which could quote customer details) would break the DATA.md claim.
- Fix: store `error.code` for `AppError` and the class name only for anything else.

### N5 (nit, info): accepting an invite removes it from other tenants' lists
- Where: `backend/app/routes/team.py:448-449`.
- When x@corp accepts tenant B's invite, tenant A's pending invite to x@corp disappears from A's list. A can therefore
  learn that x joined somewhere. This adds nothing new: A could already learn it through the existing A5
  `email_taken` answer on invite. No change is needed. If A5 is ever fixed, keep the revoked invite visible as
  "expired" rather than removing it.

## Evidence

| Command | Result |
|---|---|
| `pg_ctlcluster 16 main start`, plus a `studio` user | Postgres 16 accepting connections |
| `.venv/bin/python -m pytest -o addopts="" -q` (whole backend suite) | **825 passed, 1 skipped** in 129.66 s |
| `pytest tests/test_billing.py tests/test_pending_cancels.py tests/test_team.py` | all passed |
| `alembic upgrade head && alembic check` on a fresh database | ran through 0011; "No new upgrade operations detected." |
| `bash infra/test-deploy-workflow.sh` | passed: 137, failed: 0 (actionlint not installed, skipped) |
| `pip-audit -r backend/requirements.txt` | No known vulnerabilities found. No dependency files changed in the diff. |
| Secret scan of the added lines in the diff (`sk_/rk_ live/test`, `whsec_`, `AKIA`, private keys, `AccountKey=`, password literals) | no matches |
| Probe `test_p1` (takeover, then account deletion) | `closed: [('cus_B','sub_2')]`, cus_A never closed |
| Probe `test_p2` (duplicate, then account deletion) | `cancelled: ['sub_2']`, `closed: [('cus_A','sub_1')]`, cus_B never closed |
| Probe `test_p3` (deletion with an escalated pending cancel) | 204, row `(None, 'sub_1', 12, 'RuntimeError: down')` remains |
| Probe `test_p4` (idle-in-transaction timeout during the cancel) | 3 failed sweeps, `attempts` stays 1, `25P03` in the log, no CRITICAL |

The probe sources are in the scratchpad (`test_zz_probe_t179.py`, `test_zz_probe2_t179.py`). They were not committed.

Suggested board tasks:
- "starter: one Stripe customer per tenant, and delete every customer on account deletion (T-179 M1)"
- "starter: the cancel attempt must fit inside the idle-in-transaction timeout, and count failed commits (T-179 M2)"
- "starter: refund or flag the paid invoice of a cancelled duplicate subscription, and expire other open checkouts
  (T-179 M3)"
- L1 and the nits can go in one "T-179 lows" task.
