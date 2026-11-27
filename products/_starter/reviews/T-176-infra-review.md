# Review: p/_starter/T-176-job (commit 2d53d08), scheduled cancels job

Reviewer, 2026-11-27. Scope: `git diff main...p/_starter/T-176-job` (9 files, +196/-44). Context: T-175 review S1,
`backend/app/maintenance.py`, `backend/app/routes/billing.py:249-281`.

## Summary

Adds `caj-<slug>-cancels`, a scheduled Container Apps job that runs `python -m app.maintenance cancels` every 30
minutes. It closes T-175 review S1: pending takeover-cancels are now retried even for tenants that get no more billing
events, or that were deleted. The job copies the purge job: same pull identity plus `id-<slug>-app` (the rows-only
role), same image variable (`purgeImageNow`), same follow rule. `purge-job.sh follow` now loops over both jobs and reads
each one back. The workflow comments, READMEs, the deploy-role comment and BUDGET.md are updated. The change is small
and does what S1 asked for.

## Evidence

- `infra/test-deploy-workflow.sh`: passed 122, failed 0. This includes the new stand-in-az test: `follow` updates and
  verifies both `caj-starter-purge` and `caj-starter-cancels`, and `follow` is called 3 times (promote, failure
  rollback, manual rollback).
- `infra/test-deploy-role.sh`: 67 passed, 0 failed.
- `infra/test-db-setup.sh`: 33 passed, 0 failed.
- `infra/test-bicep-identities.sh` needs the compiled JSON, so I couldn't run it here (no az or bicep locally). In CI
  run 45989891060, the `infra` job (bicep build of main, shared and deploy-role, then the identities test, then
  cost-guard) passed. `backend` was still running when I checked.

## The points I was asked to check

1. **Secrets wiring.** This is correct. `cancelsSecrets` always has `database-url`. When `useStripe` is set, it also
   has `billing-webhook-secret` and `stripe-secret-key`, and those are the exact names `stripeEnv` uses in
   `secretRef`. Both lists use the same `useStripe` condition, so no `secretRef` can point at a missing secret. All
   three values come from `@secure()` params. No output exposes them: the new output is just `cancels.name`. No
   script echoes them: `purge-job.sh` only touches image and email vars. A job has no revisions, so a conditional
   secret list is safe here. The web app's always-define rule doesn't apply. An empty key becomes `not-configured`:
   Stripe then rejects every call, the row's `attempts` goes up and an ERROR is logged. There is no attempt cap, so
   no row is ever lost.
2. **BILLING_PROVIDER is set before the image moves.** Between the Bicep deploy and `promote`, the job runs the live
   (old) image with the new release's provider and Stripe secrets. That window is harmless. The sweep builds one
   client for the configured provider (`maintenance.py`, `{provider.name: provider}`) and skips rows for any other
   provider (`sweep_pending_cancels`: `if client is None: continue`). A mismatch can only defer rows, never cancel
   the wrong thing. The B1 guard (never cancel the tenant's current ref) is in both images. Main already has the
   `cancels` command, so the old image can run it. The residual issue is in rollback, not in the window (see S1).
3. **Identity.** `identity: webIdentity` and `identitySettings: webIdentitySettings` are used, and `appDbAuthEnv`
   gives the `id-<slug>-app` client id. The database URL is the app role's (rows only), never the migrator's. The
   identities test covers this with the `cancels:app:migrate` spec.
4. **Timing.** `replicaTimeout: 900` is shorter than the `*/30` schedule. With `parallelism: 1` and
   `replicaCompletionCount: 1`, one execution ends before the next one fires. One case remains: a run that times out
   and retries uses up to 2 x 15 minutes, so it can just overlap the next scheduled run. That is safe because rows
   are taken with `FOR UPDATE SKIP LOCKED` and a cancel is idempotent. `replicaRetryLimit: 1` is sensible, since the
   command exits 0 even when some rows fail, so a retry only happens after a crash or timeout.
5. **Deploy role.** `Microsoft.App/jobs/read`, `jobs/write`, `start/action` and `executions/read` are already in the
   role, and the role scopes by type, not by name. Nothing new is needed. `az containerapp job update --set-env-vars`
   is already used on the purge job without `listSecrets`.
6. **Tests.** They do assert the new job: its command, args and container name; that its image is the purge job's
   image; the cron parameter and its `*/30` default; Consumption plan; parallelism; that the timeout is at least 600
   and under 1800; retry limit 1; that the identity and DB env are the app role's; that the billing env follows
   `useStripe` and the AI key is absent; and the output. The stand-in-az test checks that `follow` reaches both jobs.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. A rollback leaves the cancels job on the failed release's billing settings.** `purge-job.sh follow` resets
  only the image and the email vars. `BILLING_PROVIDER` and the Stripe secrets stay as the last Bicep deploy set them.
  The `rollback_to` workflow doesn't redeploy Bicep either. Example: a release switches stripe to mock, fails after
  the Bicep step and is rolled back. The live app is on Stripe again and still writes `stripe` to-dos, but the sweep
  runs `mock` and skips every one of them. Only the per-tenant webhook retry is left, which is the gap S1 was meant to
  close. No data is lost or wrongly cancelled. The only harm is that duplicate subscriptions can go on billing
  customers until the next good deploy, and a provider switch is rare.
  Fix (one of these):
  (a) have `follow` also copy `BILLING_PROVIDER` from the revision. This needs both Stripe secrets always defined on
  the job, with the placeholder, like `webSecrets`.
  (b) have the sweep build a client for every provider whose credentials are present.
  (c) at least document this in `infra/README.md` and the rollback summary ("after a provider-switch rollback,
  redeploy the live release").
- **S2. Weak env and secret assertions.** "cancels job secrets: defined" only checks `has("secrets")`. Add a check
  that the job's `secretRef` names are a subset of its secret names, for both values of `useStripe`. Also check that
  `stripeEnv` and the Stripe secrets appear only under `useStripe`. That would catch a future rename that breaks the
  deploy at runtime, which the current tests wouldn't.
- **S3. Partial `follow`.** If the purge update succeeds and the cancels update fails, the script exits with the two
  jobs on different images. Rollback re-runs `follow` for both, so this recovers, and the error message names the
  job. That is acceptable. Consider saying in the header comment that `follow` is safe to re-run (idempotent).
- **S4. Naming.** `purge-job.sh`, `purgeImage` and the `PURGE_*` variables now drive both jobs. A later rename
  (`follow-jobs.sh`, `jobImage`) would make that clearer. Not for this change.
- **S5. BUDGET.md.** The estimate assumes about 10 s a run. During a Stripe outage, each pending row can take about
  17 s and a run can last up to 900 s. Even then, 1,440 x 900 s at 0.25 vCPU is about 324k vCPU-s a month, about $8
  with no free grant. That is a worst case, not something to expect. It's worth one line in the budget note.

## Verdict

**PASS.** The secrets are wired correctly, the job uses the rows-only identity, the timing is safe, and the tests
assert the new job. S1 (rollback billing-settings drift) should become a board task before G4.
