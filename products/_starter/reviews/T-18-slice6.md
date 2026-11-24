# Review: T-18 slice 6 (ADR 0003 phase 2), branch `p/_starter/T-18-slice6` @ 44b06c4

Reviewer run, 2026-11-24. Diff: `git diff main...44b06c4 -- .github products/_starter` (commit 96bff29, state/ideas
only, ignored).

## Verdict: CHANGES

The code is right and the new check is well built. What has to change is the documentation: the accepted
ADR's decision 2 still says the opposite of what the code now does, and the recovery advice in the README
doesn't work. Both are text-only fixes. No code changes are needed to pass.

## Summary

- `passwordAuth` defaults to `Disabled` in `modules/postgres.bicep` and `shared.bicep`, and `shared.bicepparam`
  sets it explicitly. `main.bicepparam` now defaults `dbAuth` to `entra`.
- New `infra/check-auth-config.sh` runs in the release job with no `if:`. It runs after `deploy_shared` and the
  check that the shared resources exist, and before the image push and the app deploy.
- Tests: `test-deploy-workflow.sh` checks that the step exists, has no condition and runs in the right order. It
  also runs the script against six stubbed `az` answers. `test-bicep-identities.sh` asserts the new defaults and
  the two parameter files.

## Evidence

| Check | Result |
|---|---|
| `bash infra/test-deploy-workflow.sh` | passed: 77, failed: 0 (actionlint not installed, skipped) |
| `bash infra/test-db-setup.sh` (local PG16) | passed: 33, failed: 0 |
| `bash -n` on check-auth-config.sh, test-deploy-workflow.sh, test-bicep-identities.sh | clean |
| `shellcheck` 0.11 on check-auth-config.sh | clean. test-bicep-identities.sh has SC2034/SC2154 warnings, all from existing indirect variables, none in this diff |
| Mutation: drop the `passwordAuth != Disabled` test | caught ("fails when passwordAuth is Enabled") |
| Mutation: invert the `az` failure branch | caught |
| Mutation: `jq -er` changed to `jq -r` | not caught, but harmless: `null` still fails the equality test, so the check still fails closed |
| Extra stubs: empty `az` output, lower-case `disabled`, unset `RESOURCE_GROUP` | all exit 1, with no secret in the output |
| Bicep build | not run here, per the brief (CI's `check` job builds both templates and both param files) |

**Fail closed and no secrets: confirmed.** The script prints only the server name, the two setting values and
at most 300 bytes of `az` stderr. `az postgres flexible-server show --query authConfig` returns no secret.

**Nothing on Azure still needs password sign-in.**
- The web app, the purge job (`purgeEnv` includes `appDbAuthEnv`) and the migration job all get `DB_AUTH=entra`
  from `main.bicep` when `dbAuth=entra`.
- The db-setup step signs in with the Entra admin token.
- `PG_ADMIN_PASSWORD` is only the random value ARM needs, made inside the `deploy_shared` step.
- Local development (`.env.example` `DB_AUTH=password`), CI Postgres (`PGPASSWORD: studio` in
  `_starter-ci.yml`) and `test-db-setup.sh` use local servers. They are correctly untouched.

## Critical issues (must fix before merge)

### C1. ADR 0003 decision 2 now contradicts the code, while the status says "accepted"
`ADR/0003-entra-postgres.md` lines 95 to 103 still say:
- the first shared deploy runs with "both methods on" (`passwordAuth: Enabled`), so the server can't be locked
  out if the admin step fails;
- phase 2 comes "after the starter's first Entra release passes its smoke tests".

This branch turns password sign-in off before any deploy has ever run, so the first `deploy_shared` creates the
server with passwords already off. That reverses a design point the security gate approved
(`reviews/T-18-adr-security.md`). It may be a reasonable reversal (see C2), but it happens silently. Only the
slice table row changed.

**Fix:**
- Rewrite the Phase 1 and Phase 2 bullets of decision 2 to say the server is created with `Disabled` from the
  first deploy, and why.
- Add to the "Only the first real deploy can verify" list (line 240): *creating* a server with
  `passwordAuth: Disabled` while `administratorLogin` and `administratorLoginPassword` are still supplied is
  accepted. The list today only covers *re-deploying* after phase 2.
- Log the reversal in `state/DECISIONS.md` when merging.

Keeping the status "accepted" is fine. The design passed the security gate, and slices 1 to 6 implement it.
Items that only a real deploy can verify stay tracked in the ADR. They don't make it "proposed".

### C2. The builder's doubt about lockout, and why the README's recovery advice is wrong
**Judgement:** a server created with passwords off is acceptable, and the lockout fear is overstated.
- The Entra admin (`flexibleServers/administrators`) is a **control-plane** ARM resource. Adding it never needs a
  database sign-in.
- If that step fails on the first deploy, the server is empty. Re-running `deploy_shared`, or adding the admin
  through ARM (`az postgres flexible-server microsoft-entra-admin create` by an Owner, which is in scope for
  `rg-ai-studio`), recovers it fully. No data is at risk.
- That is safer than ADR phase 1 (a window where password sign-in is on), so no code fix is needed.

But `infra/README.md` lines 82 to 84 give two pieces of advice that are wrong:
- "If the Entra admin step fails there, the server has no way in". This is not true: ARM is the way in.
- "deploy once with `postgresPasswordAuth=Enabled` and flip it back". This would not help:
  - The admin password is random per run, masked, and never kept, so nobody could sign in with it anyway.
  - The workflow has no input to set `Enabled`. That needs a code change to `shared.bicepparam`.
  - That run's release fails `check-auth-config.sh` by design.

**Fix:** replace those lines with the real recovery: re-run `deploy_shared`, or have the Owner add the Entra
admin through ARM. Then check with `az postgres flexible-server microsoft-entra-admin list`. Keep the "logged
break-glass" pointer to the ADR's failure-modes table for anything else.

## Suggestions (non-blocking)

- **S1** `infra/main.bicep:38-43`: the template default is still `dbAuth = 'password'`, and the description says
  "the deploy workflow flips this in ADR 0003 slice 4". If `main.bicep` is deployed without `main.bicepparam`, the
  apps come up in password mode against a server that refuses passwords. Set the default to `entra` and update
  the description, to match the bicepparam comment ("a deploy that forgot DB_AUTH must not produce
  password-mode apps"). Extend the jq test to cover it.
- **S2** The `rollback` job does not run `check-auth-config.sh`. A rollback changes no server settings, so this
  is fine. Say so in one line, so that "every release" isn't read as covering rollbacks.
- **S3** `test-deploy-workflow.sh`: add one assertion that the check's output does not contain a planted marker.
  For example, the stub writes `SECRETMARKER` to stderr and also returns a valid JSON body. That pins the "prints
  no secrets" promise for when the script changes later.
- **S4** README `## Entra ID database sign-in` (line 152): the new sentence is one very long line. Wrap it to
  match the file.
- **S5** Reviewer environment note: `pip download` left a `.whl` in `infra/` during this review. It was removed
  and is not committed. No action for the builder.

## Top issue
C1/C2: the code makes the first deploy password-off, but ADR 0003 decision 2 and the infra README still describe
a phase-1 password window and a recovery path that doesn't work. Fix the text; the code can stay.

## Re-review at 9d815d9

### Verdict: PASS

I checked commit 9d815d9 (`_starter: T-18 slice 6 review fixes`) against cca8ba8.

| Item | Status | Evidence |
|---|---|---|
| C1 | Fixed | ADR 0003 decision 2 no longer has a phase 1 with both methods on. It now says passwords are off from the first deploy, with recovery through ARM. The first-deploy list now includes "server was created with `passwordAuth: Disabled`". The context line at line 12 was updated to match. The DECISIONS.md entry is the lead's job at merge. |
| C2 | Fixed | infra/README.md step 7: the "no way in" claim and the "deploy once Enabled" advice are gone. Recovery is now "fix the cause and re-run `deploy_shared`", checked with `az postgres flexible-server microsoft-entra-admin list` (it must list only the deploy service principal). |
| S1 | Fixed | `main.bicep` defaults `dbAuth` to `'entra'`. `test-bicep-identities.sh` asserts that default. CI builds the template and runs this test. |

Re-run results:
- `test-deploy-workflow.sh`: 77/77.
- `test-db-setup.sh` on PG16: 33/33.
- `bash -n`: clean on all three scripts.
- shellcheck: `check-auth-config.sh` clean. `test-bicep-identities.sh` has the same 8 warnings as before, all from existing indirect variables.

### Nits left (non-blocking, can go to a follow-up task)

- `main.bicep:38`: the `dbAuth` description still says "the deploy workflow flips this in ADR 0003 slice 4".
  Lines 209-210 still describe password mode as the normal case.
- ADR 0003 failure-modes row (line 259): "`deploy_shared` fails in phase 1; password auth still on". Password
  sign-in is no longer on at that point. The recovery in that row is still valid.
- Comments that still say "phase 1 only" about the random admin password: `shared.bicepparam:13`,
  `_starter-deploy.yml:177` and `modules/postgres.bicep:15`. Better: "required by ARM, unusable while password
  sign-in is off".
- S2 to S4 from the first review are still open (all optional).
