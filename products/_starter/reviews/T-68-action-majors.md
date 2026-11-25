# Review: p/studio/T-68 (GitHub Actions major bumps, Dependabot PR #4 cherry-pick)

Reviewer: `reviewer` (opus), 2026-11-25
Diff: `git diff main p/studio/T-68`, one commit `c4a2802`, 4 files, 23 lines changed, all of them `uses:` pins.

## Verdict: PASS

No breaking change in any of the six majors touches an input, default or behaviour our workflows rely on.
Merge as-is. No edits needed.

## How this was checked

- The GitHub REST and GraphQL APIs were blocked in this session (403), so release pages could not be fetched.
  Instead I cloned each upstream repo (`git clone --filter=blob:none`) and read the **changelog / README /
  RELEASES.md and `action.yml` at the exact tags**. That is the same content the release pages summarise,
  and it ties each finding to the pinned commit.
- I confirmed that every old and new SHA is the tag commit (`git tag --points-at`):
  checkout `11d5960a`=v4.4.0 → `3d3c42e5`=v7.0.1; setup-python `a26af69b`=v5.6.0 → `6d4fd22b`=v7.1.0;
  setup-node `49933ea5`=v4.4.0 → `949feb24`=v7.1.0; cache `0057852b`=v4.3.0 → `55cc8345`=v6.1.0;
  upload-artifact `ea165f8d`=v4.6.2 → `cf430e03`=v7.0.2; azure/login `7184910d`=v2.3.1 → `a641126d`=v3.1.0.
- I ran `git diff <old-tag> <new-tag> -- action.yml` for each action, to get every changed input, default and runtime.
- I grepped all four workflows for inputs that the majors removed or changed: `always-auth`, `registry-url`,
  `enable-AzPSSession`, `allow-no-subscriptions`, `auth-type`, `audience`, `include-hidden-files`, `overwrite`,
  `fetch-depth`, `allow-unsafe-pr-checkout`. **None of them is used.**
- Tests on the branch:
  - `python3 -m unittest discover -s scripts/tests`: 43 OK. That includes `test_workflow_pins`, 3 OK; its regexes
    match the new `@<40-hex> # vX.Y.Z` lines.
  - `bash products/_starter/infra/test-deploy-workflow.sh`: passed 102, failed 0. It greps `uses: azure/login@`
    and the client-id/tenant-id/subscription-id secrets, so it still matches.
  - actionlint is not installed here. The Studio Lead's actionlint 1.7.12 clean run is accepted.

## Per-action findings

### actions/checkout v4.4.0 → v7.0.1 (all 10 uses, 4 workflows)
Sources: [CHANGELOG.md@v7.0.1](https://github.com/actions/checkout/blob/v7.0.1/CHANGELOG.md),
[README.md@v7.0.1](https://github.com/actions/checkout/blob/v7.0.1/README.md),
[action.yml@v7.0.1](https://github.com/actions/checkout/blob/v7.0.1/action.yml)
- **v5: node24 runtime, needs runner >= v2.327.1.** Every job is `runs-on: ubuntu-latest` (GitHub-hosted,
  auto-updated), so this is OK.
- **v6: `persist-credentials` writes the token to a separate file under `$RUNNER_TEMP`,** pulled in by
  `includeIf`, instead of `.git/config`. The README says "No workflow changes required — git fetch, git push,
  etc. continue to work". Only `azure-spend.yml:112-135` uses the persisted token
  (`git fetch`/`git push origin HEAD:main`/`git reset --hard origin/main`), and it runs on the host in
  `$GITHUB_WORKSPACE`, not in a Docker container action, so the v2.329.0 container caveat doesn't apply.
  Nothing reads the token from `.git/config` or unsets `http.*.extraheader`. `workflow-lint.yml` sets
  `persist-credentials: false`, which still works the same way. The other checkouts keep the default (`true`),
  as before. This is a small security improvement: the token is no longer inside the workspace `.git`.
- **v7: refuses fork-PR checkout under `pull_request_target`/`workflow_run`** unless `allow-unsafe-pr-checkout`
  is set. None of our workflows uses those triggers (push, workflow_dispatch, schedule only). Also, v4.4.0
  already carried this guard (backport #2502), and `action.yml` differs only in `using: node20 → node24`.
- v7 ESM migration: internal only. `fetch-depth` default is still 1. Unchanged for azure-spend's depth-1 fetch and rebase loop.

### actions/setup-python v5.6.0 → v7.1.0 (CI: backend, e2e, infra)
Sources: [README.md@v7.1.0](https://github.com/actions/setup-python/blob/v7.1.0/README.md),
[action.yml@v7.1.0](https://github.com/actions/setup-python/blob/v7.1.0/action.yml), commit log v5.6.0..v7.1.0
- **v6: node24** (runner >= v2.327.1). Hosted runners: OK.
- **v7: ESM only.** README: "No changes to action inputs, outputs, or behavior."
- `action.yml` diff: only additions (`mirror`, `mirror-token`, `pip-version`). `pip-install` was added and then
  removed inside the range (#1201, #1336), and we never used it. Our inputs `python-version`, `cache: pip` and
  `cache-dependency-path` are unchanged.
- `cache-dependency-path: products/_starter/backend/requirements-dev.txt` is inside the workspace, so the
  reverted "files outside workspace" change (#1186) doesn't matter.
- The pip cache key now includes the Linux distro (#1323), so the first run after merge misses the cache once.
  Cosmetic.

### actions/setup-node v4.4.0 → v7.1.0 (CI: frontend, e2e)
Sources: [README.md@v7.1.0](https://github.com/actions/setup-node/blob/v7.1.0/README.md),
[action.yml@v7.1.0](https://github.com/actions/setup-node/blob/v7.1.0/action.yml)
- **v5: node24, plus automatic caching when no `cache` input is given.** We always set `cache: npm`
  explicitly, so the behaviour is unchanged. setup-node isn't used in the deploy or spend workflows, where
  automatic caching would be a cache-poisoning concern.
- **v6: `always-auth` removed.** Not used.
- **v7: dummy `NODE_AUTH_TOKEN` fallback removed** (it only matters with `registry-url`). We don't set
  `registry-url`, and we use npm, not Yarn 1.
- `node-version: "22"`, `cache: npm` and the single-file and multi-line `cache-dependency-path` forms are all
  still supported (the new outputs are additive).

### actions/cache v4.3.0 → v6.1.0 (e2e Playwright browser cache)
Sources: [README.md@v6.1.0](https://github.com/actions/cache/blob/v6.1.0/README.md),
[RELEASES.md@v6.1.0](https://github.com/actions/cache/blob/v6.1.0/RELEASES.md)
- **v5: node24** (runner >= 2.327.1). **v6: ESM and `@actions/*` majors.** Both are internal.
- `action.yml` diff is the runtime line only. `path: ~/.cache/ms-playwright` and
  `key: playwright-${{ runner.os }}-${{ hashFiles(...) }}` are unchanged in meaning. The cache service is the
  same (v2 backend since v4.2), so existing entries stay valid.

### actions/upload-artifact v4.6.2 → v7.0.2 (e2e logs on failure)
Sources: [README.md@v7.0.2](https://github.com/actions/upload-artifact/blob/v7.0.2/README.md),
[action.yml@v7.0.2](https://github.com/actions/upload-artifact/blob/v7.0.2/action.yml)
- **v6: node24.** **v7: new `archive` input (direct, unzipped upload), default `true`.** So the default
  behaviour is unchanged: `e2e-logs` is still one zip.
- The v4+ rules still hold and already applied before this change. Artifacts are immutable per name: we
  upload `e2e-logs` once per job, and a re-run is a new run, so this is fine. `include-hidden-files` defaults
  to `false`: the logs are `migrate.log`, `api.log`, `build.log`, `web.log` and `failure.png`
  (`products/_starter/scripts/e2e.sh:34-54`), none hidden. `retention-days: 7` is still valid.
  `if-no-files-found` defaults to `warn`, as before.

### azure/login v2.3.1 → v3.1.0 (deploy x4 sign-ins, rollback x1, azure-spend x2)
Sources: [README.md@v3.1.0](https://github.com/Azure/login/blob/v3.1.0/README.md),
[action.yml@v3.1.0](https://github.com/Azure/login/blob/v3.1.0/action.yml), commit log v2.3.1..v3.1.0 (#578 node24)
- **The only breaking change is node20 → node24** (#578). Hosted runners: OK.
- `action.yml` diff: two new optional inputs, `max-context-population` (PowerShell only) and
  `mask-client-id` (default `true`, same masking as v2). No defaults changed: `enable-AzPSSession` false,
  `allow-no-subscriptions` false, `auth-type` SERVICE_PRINCIPAL, `audience` api://AzureADTokenExchange,
  `environment` azurecloud.
- `src/Cli/**` (the az CLI OIDC and creds login path) has **no diff** across the range. `src/common` changes
  are only the two new inputs and the user-agent string now built from `GITHUB_ACTION_REF`. The PowerShell
  refactor doesn't run because we don't enable AzPSSession.
- Our usage stays valid: OIDC with `client-id`/`tenant-id`/`subscription-id` from `secrets.*`, which the v3
  README explicitly recommends, and the `creds:` service-principal JSON fallback in azure-spend (still
  supported). The repeated sign-ins before the registry push and the DB step (the issue #372 workaround) are
  unaffected.

## Critical issues
None.

## Suggestions (non-blocking)
1. `products/_starter/SECURITY.md:331` still says "Actions are pinned by tag (`actions/checkout@v4`, ...)". That
   was fixed in T-30 and is now two majors out of date. Add an "(Update, T-30/T-68: SHA-pinned, now checkout v7,
   setup-python v7, setup-node v7, cache v6, upload-artifact v7, azure/login v3)" note, the same way line 333 does.
2. The first `_starter-ci` run after merge will miss the pip cache once (setup-python's new distro-aware key).
   Expect a slower backend job once. It isn't a regression.
3. When actionlint is available in CI (`workflow-lint.yml`), it confirms the node24 `uses:` metadata on push to
   main. Check that run after merge, because actionlint could not run in this review environment.
