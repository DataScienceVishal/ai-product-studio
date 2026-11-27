# Review: p/_starter/T-177 (head ac299b0)

Reviewer, 2026-11-27. Scope: `git diff main...origin/p/_starter/T-177` (10 files, +176/-23). This branch closes
T-176-infra-review S1 with option (a), plus infra S2 and S3, and T-176-backend-review S2 and S3.

**Verdict: CHANGES** (one critical issue, C1)

## Summary

- **Backend S2.** `attempt_pending_cancel` gets a keyword-only `backoff_now`. Only the sweep passes it. After the
  `FOR UPDATE SKIP LOCKED` re-read (with `populate_existing`), a row that is no longer due is rolled back, which
  releases the lock, and the function returns `None`. The sweep counts `None` as neither cancelled nor failed. The
  webhook path (`retry_pending_cancels`) does not pass it, so the webhook behaves as before. This part is correct.
- **Backend S3.** The README now documents the operator query. Done.
- **Infra S1 (a).** The cancels job always defines and always references both Stripe secrets, with a placeholder when
  they are unset. `purge-job.sh` reads `BILLING_PROVIDER` from the web revision (`mock` when absent), checks it against
  `^(mock|stripe)$` before it touches any job, and sets it on cancels. Purge is forced to `mock`. Both jobs are read
  back and verified.
- **Infra S2 and S3.** There are jq subset assertions on the compiled JSON, a source-level guard, and an idempotency
  note with a test. Done.

The problem: making the references unconditional breaks the cancels job in a mock deploy where the Stripe GitHub
secrets are unset, which is the default configuration. See C1.

## Evidence (run by me in a detached worktree at ac299b0)

- Backend: `cd backend && .venv/bin/python -m pytest` gave **822 passed, 1 skipped** (the frontend-not-built skip) in
  104 s, against local Postgres 16.
- `infra/test-deploy-workflow.sh`: **passed 130, failed 0** (it was 122 on T-176; the 8 new checks cover T-177).
- `infra/test-deploy-role.sh`: **67 passed, 0 failed**.
- `infra/test-db-setup.sh`: **passed 33, failed 0**.
- `infra/test-bicep-identities.sh`: bicep is not available locally. I ran the three new checks against a hand-made
  compiled-shape `main.json` that contains both forms Bicep emits: variables that stay plain object arrays
  (`cancelsStripeEnv`), and conditional variables that become expression strings
  (`[if(variables('useStripe'), createArray(createObject('name', ..., 'secretRef', 'x')), createArray())]`), with the
  resource env inlined as a `concat(...)` string. All three pass. With a ref renamed in the plain-array form, both
  cancels checks fail. With a ref renamed in the `createObject` form, the web check fails. So the `expand`/`refs`
  regexes do handle both compiled shapes.
- C1 reproduced:
  `BILLING_PROVIDER=mock BILLING_WEBHOOK_SECRET=not-configured ... python -c "from app.config import Settings; Settings()"`
  raises `BILLING_WEBHOOK_SECRET must be at least 32 characters (leave it unset with mock billing)`.

## Critical

### C1. In a mock deploy with no Stripe GitHub secrets, the cancels job crashes on every run

`infra/main.bicep:409-428` (`cancelsStripeEnv`, used unconditionally in `cancelsEnv`) and `:429-442`
(`cancelsSecrets`), together with `backend/app/config.py:133-135`.

- The workflow (`_starter-deploy.yml:287`) requires `STARTER_BILLING_WEBHOOK_SECRET` and `STARTER_STRIPE_SECRET_KEY`
  only for `billing_provider=stripe`. With mock and the secrets unset, `billing-webhook-secret` holds `not-configured`
  (14 characters).
- Before T-177, a mock cancels job had no `BILLING_WEBHOOK_SECRET`, so the app generated a random 32-character one.
  Now the job always gets `BILLING_WEBHOOK_SECRET=not-configured`.
- `Settings()` runs first in `app.maintenance.main()`, and its validator rejects any webhook secret shorter than 32
  characters. Every execution therefore exits non-zero: one retry, every 30 minutes, a failed execution each time.
  The sweep never runs.
- The web app is not affected, because its `stripeEnv` is still conditional on `useStripe`.
- No test catches this. The Bicep tests check the shape, and no test loads `Settings` with the env the job really gets.

This is the starter's default configuration, so every new product built on it would have a broken job from its first
deploy.

The stripe-rollback case that S1 targets does work. Once Stripe has been used, the GitHub secrets exist, and a
`whsec_...` value is 32 characters or more.

Fix (recommended): keep the secrets always defined, which is the real requirement (a job's secrets are not per
revision). Make the env references follow the provider:

1. Go back to `cancelsEnv = concat(..., stripeEnv, ...)` (conditional references).
2. In `purge-job.sh follow`, for cancels only:
   - for stripe, add
     `--set-env-vars ... BILLING_WEBHOOK_SECRET=secretref:billing-webhook-secret STRIPE_SECRET_KEY=secretref:stripe-secret-key`;
   - for mock, add `--remove-env-vars BILLING_WEBHOOK_SECRET STRIPE_SECRET_KEY`. Use a second `job update` call if
     the CLI refuses to combine the two flags.
3. Read back and verify that the two `secretRef` entries are present for stripe and absent for mock.
4. Update the jq and source-level tests to match. Cancels: secrets unconditional, refs a subset of the secrets.
5. Add one backend test that builds `Settings` from the exact env a mock cancels job receives, so this class of bug is
   caught next time.

`jobs/write` already covers `--set-env-vars`/`--remove-env-vars` with `secretref:`, and no secret value is read, so
the deploy role does not change. Confirm in CI that no `listSecrets` call is made.

Rejected alternative: a placeholder of 32 characters or more. It would pass mock validation, but it would put a
constant, publicly known value where a webhook signing secret goes.

## Suggestions

1. **`PURGE_BILLING_PROVIDER` is printed into `$GITHUB_ENV` but nothing reads it** (`purge-job.sh:54`). There is no
   matching parameter in `main.bicepparam` or `main.bicep`. Two consequences:
   - The value is dead.
   - During a release, the Bicep step sets the cancels job's `BILLING_PROVIDER` from the new release
     (`useStripe`, `main.bicep:426`), while its image and email settings stay on the live revision through the `*Now`
     variables. If a run dies between the Bicep step and promote or rollback, cancels is left on the new provider
     until the next deploy. That is the same skip-only harm as S1.

   Either wire it in as `purgeBillingProvider` and `cancelsBillingNow`, like `purgeEmailProviderNow`, or stop printing
   it. With the C1 fix, Bicep would also need the matching conditional references.
2. **The compiled check cannot see whether a ref has moved under `useStripe`.** "both Stripe secrets are always ...
   referenced" (`test-bicep-identities.sh:120-126`) checks only that the refs exist, because the cancels env
   legitimately contains `useStripe` for `BILLING_PROVIDER`. The source-level awk check in `test-deploy-workflow.sh`
   covers this case. Mention that in the comment, or drop the "not conditional" claim from the check name. This
   check changes anyway with C1.
3. **A stale word in a test docstring.** `test_s2_the_webhook_retry_ignores_the_backoff` says "(no due_at)", but the
   kwarg is `backoff_now`.
4. **The sweep re-checks with its start time `now`.** A run can last up to 15 minutes, so a row whose backoff expires
   during the run is skipped until the next run. That is the conservative direction and correct. A rows-attempted-
   meanwhile case gives a negative delta and is skipped, which is also correct. No change needed; a half-line in the
   docstring would help.
5. **README wording.** "It differs in three ways" (`infra/README.md:173-176`) now carries a long parenthetical. Split
   it so that "placeholder when unset" does not read as one of the three differences. After C1, also update the
   sentence to say that the references follow the provider.

## Checked and fine

- Backoff re-check: the lock is released (`db.rollback()`) before `return None`. The sweep counts only True and
  False. The `flaky` test wrapper forwards `**kwargs`, and no other caller or monkeypatch has the old fixed signature.
  The new test really interleaves a committed write from a second session between the list and the lock.
- Shell safety in `purge-job.sh`:
  - Every value that reaches a command line or `$GITHUB_ENV` (image, verify, email provider, billing) is matched
    against an anchored pattern before use, and the script fails before any `job update` (tested with `stripe;rm`).
  - The jq filters are fixed strings, and `--arg` is used for the container name. All values are quoted, with no
    `eval`.
  - Old revisions without `BILLING_PROVIDER` fall back to `mock` (tested).
  - Purge is always `mock` (`want_billing=mock` is reset on every loop iteration, and this is tested).
- Bicep: for either value of `useStripe`, no `secretRef` names a missing secret on web or cancels. The secret
  parameters are `@secure()`, and no output exposes a secret.
- Deploy role: `follow` uses only `containerapp revision show`, `job update --set-env-vars` and `job show`, as before.
  `test-deploy-role.sh` passes.

---

## Re-review: e8bf66c (delta `git diff 7cdbbee..e8bf66c`, 8 files, +161/-39)

Reviewer, 2026-11-27. **Verdict: PASS.** C1 is fixed, suggestions 1-5 are addressed, and nothing critical is left.

### Evidence (detached worktree at e8bf66c)

- Backend: `.venv/bin/python -m pytest`: **825 passed, 1 skipped** in 105 s against local Postgres 16. That is 822
  before plus the 3 new C1 Settings tests.
- `infra/test-deploy-workflow.sh`: **passed 136, failed 0**.
- `infra/test-deploy-role.sh`: **67 passed, 0 failed**.
- `infra/test-db-setup.sh`: **passed 33, failed 0**.
- CI run 46000960916 on e8bf66c (`headSha` e8bf66ca…), checked with `gh run view`:
  - `infra` (bicep build of main, shared and deploy-role, then `test-bicep-identities.sh`, then cost-guard): **success**;
  - `image`: **success**;
  - `frontend`: **success**;
  - `backend`: still in progress when I checked. The same suite passes locally (above).
- I also ran the revised compiled-JSON checks against my hand-made ARM-shape file, updated to the new variables
  (`cancelsStripeEnv` as an `if(variables('cancelsUseStripe'), createArray(...), createArray())` string,
  `cancelsUseStripe` as `equals(variables('cancelsBillingNow'), 'stripe')`, and `cancelsBillingNow` as an
  `if(empty(parameters('purgeBillingProvider')), ...)` string). The two secretRef-subset checks and the
  "only under cancelsUseStripe" check pass. CI ran them against the real compiled output and they pass there too.

### What I checked

1. **C1 is fixed.**
   - Mock with unset secrets: the cancels job gets no `BILLING_WEBHOOK_SECRET` or `STRIPE_SECRET_KEY`, so the app
     generates its random webhook secret as before T-177.
   - Stripe: both references are present, and both secrets are always defined, for either provider value. No
     `secretRef` names a missing secret.
   - The new backend tests pin the settings behaviour for the mock-without-references, placeholder-rejected and
     stripe cases.
2. **The `purgeBillingProvider` wiring.**
   - `live-release.sh` (deploy job, line 246) appends the `purge-job.sh settings` output, including
     `PURGE_BILLING_PROVIDER`, to `$GITHUB_ENV`. The Bicep step runs later in the same `deploy` job, and
     `main.bicepparam` reads it with `readEnvironmentVariable('PURGE_BILLING_PROVIDER', '')`.
   - First release: `live-release.sh` prints only `FIRST_RELEASE` and `LIVE_REVISION`, so the parameter is `''` and
     `cancelsBillingNow` becomes this release's `billingProvider`. That is correct, because the only revision is this
     release.
   - Validation: the value can reach Bicep only from `purge-job.sh`, which checks it against `^(mock|stripe)$` before it
     prints anything.
   - The web app is unaffected. It still uses `useStripe` and `stripeEnv`, which come from this release's
     `billingProvider`.
   - This also closes suggestion 1. The Bicep step no longer moves the cancels job to the new release's provider
     before promote.
3. **`--remove-env-vars` on an absent name.**
   - The script reads the job first and removes only the names that are present. A mock job without references makes
     no remove call at all, and the stand-in az that errors on an absent name tests this.
   - Even unguarded, the Azure CLI containerapp extension's env-var removal only logs a warning ("does not exist") for
     an absent name. With `--only-show-errors` it is silent, so it is safe either way.
   - `$present` is unquoted on purpose. It can only contain the two fixed names that jq's filter selects.
4. **The read-back is strict.** The cancels job must have exactly both `secretRef`s with stripe and none with mock.
   Purge must never have any. A stand-in that ignores removal makes the run fail.
5. **The deploy role.** `--set-env-vars NAME=secretref:x` and `--remove-env-vars` are both `jobs/write`, and neither
   reads a secret value. `test-deploy-role.sh` is unchanged and green.
6. **Suggestions 2-5.**
   - 2: the compiled check now asserts the condition chain from `cancelsStripeEnv` through `cancelsUseStripe` and
     `cancelsBillingNow` to `purgeBillingProvider`.
   - 3: the docstring is fixed.
   - 4: the sweep docstring explains the start-time re-check.
   - 5: the README is rewritten.

### Remaining suggestions (non-blocking)

- **R1.** Add `@allowed(['', 'mock', 'stripe'])` to `param purgeBillingProvider` (`main.bicep:87`). A bad value
  would then fail the deploy instead of silently meaning mock. Today `purge-job.sh` already guarantees the shape, so
  this is defence in depth.
- **R2.** When `follow` switches the cancels job to mock, it removes the references in one call and sets
  `BILLING_PROVIDER=mock` in the next. If a scheduled run starts between the two calls, it sees stripe without
  secrets and fails once. That is harmless and retried at the next run, but you could close it by passing
  `--remove-env-vars` and `--set-env-vars` in one `job update`. Confirm first that the CLI accepts both flags
  together.
- **R3.** Update `infra/README.md:180`. The last sentence ("`purge-job.sh follow` copies `BILLING_PROVIDER`...")
  could also say "and adds or removes the two Stripe references". The paragraph above already says this, so it is
  minor.
