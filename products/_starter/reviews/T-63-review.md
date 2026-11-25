# Review: T-63 read-only spend identity (`p/_starter/T-63-spend-identity`)

Reviewer: `reviewer` agent, 2026-11-25. Commit reviewed: `0e925cb` (diff `main...p/_starter/T-63-spend-identity`, 5 files, +55/-13).

## Summary

The daily `azure-spend` workflow now prefers a new read-only managed identity `id-github-spend`
(Reader + Cost Management Reader on `rg-ai-studio`, secret `AZURE_SPEND_CLIENT_ID`). Mode order is
spend > oidc (deploy identity, temporary) > sp (`AZURE_COST_CREDENTIALS`, temporary) > none. SETUP.md gives
Vishal the `az` commands; engineering playbook and infra README are updated; the static workflow test gains
4 checks.

The change does what the task asks. When the spend identity is configured, the Contributor/deploy identity
cannot be selected, the main-only guard is preserved for both OIDC identities, permissions are unchanged and
job-scoped, nothing prints an ID or secret, and the SETUP.md grants are scoped to the resource group only.

## Evidence

| Check | Result |
|---|---|
| `bash products/_starter/infra/test-deploy-workflow.sh` | passed: 106, failed: 0 (its built-in actionlint step skipped: not on PATH) |
| `python3 -m unittest discover -s scripts/tests` | Ran 43 tests, OK |
| `actionlint` 1.7.12 (scratchpad copy) on `.github/workflows/*.yml` | no findings, rc=0 |
| Mode-selection truth table (the step's shell, all 16 combinations of HAS_SPEND/HAS_OIDC/HAS_COST_SP/ON_MAIN) | see below |

Truth table (extracted `if` chain, run in bash):

- HAS_SPEND=true, on main: `spend` in all 4 combinations of the other secrets. The deploy identity is never chosen.
- HAS_SPEND=true or HAS_OIDC=true, off main: `::error::` and exit 1 (main guard holds for both identities).
- HAS_SPEND=false, HAS_OIDC=true, on main: `oidc` (temporary fallback, logged as such).
- Neither OIDC set, SP set: `sp` on or off main (pre-existing; the commit step is still guarded by `ON_MAIN`).
- Nothing set: `none`.

### Spend secret set but tenant/subscription missing

`HAS_SPEND` and `HAS_OIDC` both require `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID`, so if either shared
secret is missing, **both** are false. The workflow therefore cannot fall back to the Contributor deploy
identity in that case: the requirement "when the spend secret is set the deploy identity is never used" holds
in every combination. What it does instead is fall to `sp` (if `AZURE_COST_CREDENTIALS` is still set) or to
`none`, which prints "No Azure credentials are set" and ends green without updating BUDGET.md.

Decision: acceptable for merge, not a privilege problem. It is a misleading-silence problem (see S1), and the
scenario is practically unreachable while the deploy workflow depends on the same two shared secrets (removing
them breaks deploys loudly). Fix it when the `sp` fallback is removed.

### SETUP.md commands

- Federated credential subject `repo:DataScienceVishal@102427114/ai-product-studio@1468636475:ref:refs/heads/main`,
  issuer and audience are byte-identical to the existing `id-github-deploy` credential. Correct.
- `az identity create ... --location francecentral` matches the deploy identity and the Azure for Students region rule.
- Role names `Reader` and `Cost Management Reader` are the exact built-in names (quoted in the loop). Both use
  `--scope /subscriptions/$SUB/resourceGroups/rg-ai-studio`: no subscription-wide grant.
- `--assignee-object-id` plus `--assignee-principal-type ServicePrincipal` avoids the Graph-replication delay
  for a freshly created identity. Good.
- Reader is needed: Cost Management Reader does not include `resourceGroups/resources/read`, which
  `az resource list -g` uses. Cost Management Reader covers the RG-scope query POST. Reader does not allow
  `listKeys`/`listSecrets`, so no data-plane secrets are reachable.
- Reminder to set `SUB` in a new shell is present.

### Security

- No new `${{ }}` interpolation into `run:` scripts; `$GITHUB_REF` is read from env (no script injection).
- `::notice::` lines name the identity, never an ID. Secrets passed only through `with:` to the SHA-pinned
  `azure/login` (same pin as before).
- `id-token: write` stays job-level; workflow-level permissions remain `contents: read`.
- No `environment:` added.

## Critical issues

None.

## Suggestions (non-blocking)

**S1. Fail loudly on a partial spend configuration.** `.github/workflows/azure-spend.yml:56-62`. If
`AZURE_SPEND_CLIENT_ID` is set but `HAS_SPEND` is false (tenant or subscription missing), the run either uses
the `AZURE_COST_CREDENTIALS` service principal or ends green with "No Azure credentials are set", which is
untrue and leaves BUDGET.md stale. Add a job env `HAS_SPEND_ID: ${{ secrets.AZURE_SPEND_CLIENT_ID != '' }}` and,
before the `sp`/`none` branches, `elif [ "$HAS_SPEND_ID" = "true" ]; then echo "::error::AZURE_SPEND_CLIENT_ID
is set but AZURE_TENANT_ID or AZURE_SUBSCRIPTION_ID is missing (SETUP.md step 3)."; exit 1`. Do it in the
follow-up that removes `sp`, at the latest.

**S2. Redundant condition.** Line 57's `&& [ "$HAS_SPEND" != "true" ]` can never change the outcome (line 56
already took every on-main HAS_SPEND=true case). Harmless and it documents intent, but the new static test
(`test-deploy-workflow.sh:196`) asserts this text rather than the behaviour. Better: a tiny behavioural test
that extracts the `if` chain and runs the truth table above (I did this by hand for this review), so a future
reordering can't pass on grep alone.

**S3. Infra README drop list is incomplete.** `products/_starter/infra/README.md:159` says
`Microsoft.CostManagement/query/read` can be dropped from `deploy-role.bicep` once the spend identity is live;
`Microsoft.CostManagement/query/action` (bicep line 62) is equally unneeded then. Name both.

**S4. Follow-up must be tracked.** BOARD T-63 says "then remove the AZURE_COST_CREDENTIALS fallback and
HAS_COST_SP"; this branch deliberately keeps them until one green spend run. Keep T-63 open (or add a
follow-up task) covering: remove `sp` mode and `HAS_COST_SP`, remove `oidc` fallback so the spend report can
never use the deploy identity, drop the CostManagement actions from the deploy role, update
`test-deploy-workflow.sh:192-198` (the "signs in by OIDC" and "only creds:" checks will need to change), and S1.

**S5. Optional tightening.** A custom role with just `Microsoft.Resources/subscriptions/resourceGroups/resources/read`
could replace Reader, but Reader at RG scope exposes only control-plane config, not secrets. Not worth the
extra role definition now.

## Verdict

**PASS.** Safe to merge after the tests above (106/0 workflow checks, 43 unit tests OK, actionlint clean). S1
and S4 should be done in the fallback-removal follow-up.
