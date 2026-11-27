# Review: p/_starter/T-178 (head 21efb09)

Reviewer, 2026-11-27. Scope: `git diff main...p/_starter/T-178` (4 files, +18/-9). The branch fixes nits R1 to R3
from `products/_starter/reviews/T-177-review.md`.

Verdict: PASS

## Summary

- **R1.** `main.bicep` now has `@allowed(['', 'mock', 'stripe'])` on `param purgeBillingProvider`. It compiles with
  the Bicep version that CI pins (v0.32.4). The empty string is a valid allowed value, and the compiled ARM is
  `"allowedValues": ["", "mock", "stripe"]` with `defaultValue: ""`. The only thing that sets this parameter is
  `main.bicepparam:33`, through `readEnvironmentVariable('PURGE_BILLING_PROVIDER', '')`. That variable is written
  only by `purge-job.sh settings` (called from `live-release.sh:56`), and that path first checks the value against
  `^(mock|stripe)$` (`purge-job.sh:52`). On a first release the variable is absent, so the value is `''`. Every
  caller therefore passes only `''`, `mock` or `stripe`. Nothing else in the repo sets the parameter.
- **R2.** When the cancels job goes to mock, `--remove-env-vars <present>` now travels in the same
  `az containerapp job update` as `--set-env-vars ... BILLING_PROVIDER=mock`. A scheduled run can no longer start
  between two separate updates. The read-back check after the update is unchanged: provider plus exact set of
  references.
- **R3.** The README wording now matches the behaviour.
- A new test checks that the switch to mock makes exactly one `job update` on cancels, and that this one update
  contains both `BILLING_PROVIDER=mock` and `--remove-env-vars BILLING_WEBHOOK_SECRET STRIPE_SECRET_KEY`.

## Evidence

- `bash products/_starter/infra/test-deploy-workflow.sh`: `passed: 137  failed: 0` (actionlint was skipped because it
  is not installed).
- Bicep v0.32.4 (the version CI pins, downloaded from the Azure/bicep release): `bicep build main.bicep` and
  `bicep build shared.bicep` succeed. The only output is the BCP081 "no types available" warnings that main already
  has. `jq '.parameters.purgeBillingProvider'` on the compiled JSON shows the allowed values above.
  `test-bicep-identities.sh` passes against the compiled JSON ("all checks passed").
- azure-cli 2.93.0 wheel, `azure/cli/command_modules/containerapp/`:
  - `commands.py:58` maps `job update` to `update_containerappsjob`, which calls `update_containerappsjob_logic`
    (`custom.py:1118`).
  - Inside the loop over the named container, that function applies `set_env_vars` (`_add_or_update_env_vars`) and
    then `remove_env_vars` (`_remove_env_vars`) to the same `c["env"]`.
  - The update goes out as a single `ContainerAppsJobClient.update`, which is `send_raw_request(..., "PATCH", ...)`
    (`_clients.py` around line 893).
  - Nothing in `_validators.py` or `_params.py` makes the two flags mutually exclusive. `remove_env_vars` is
    `nargs='*'` (`_params.py:80`).
  - In 2.93.0, removing a variable that doesn't exist only logs a warning. The script's filter to names that are
    present is therefore belt-and-braces, which is fine.
- Containerapp preview extension: `.github/workflows/_starter-deploy.yml` never runs `az extension add` and never sets
  dynamic install. The only `az` setup steps are `azure/login` and `az bicep install`. So core `containerapp` runs,
  which is the code verified above.
- Bash: with `set -euo pipefail` on bash 5.2, I ran the exact pattern (`remove=()`, then
  `[ -n "$present" ] && remove=(--remove-env-vars $present)` as the last command of an `elif` body, then
  `${remove[@]+"${remove[@]}"}`). With `present=""` it expands to nothing and does not exit. With two names it expands
  to three words.
  - The `${arr[@]+"${arr[@]}"}` form is the standard workaround for bash < 4.4, where `"${arr[@]}"` on an empty
    array fails under `set -u`. It is the same idiom `extra` already uses.
  - The `&&` list's non-zero status does not trigger errexit, because the failing command is not the last one in
    the list. The "mock with no references removes nothing" test exercises this path, and it passes.
  - The runners are ubuntu (bash 5), so old-bash behaviour doesn't matter in practice.
- shellcheck 0.x (shellcheck-py, run only for this review): the changed `purge-job.sh` lines are clean, and
  `SC2206` is the right code for the unquoted array assignment. One warning remains, SC2034 on line 61 (see S1),
  and main has it too.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. `purge-job.sh:61`.** `stripe_names="BILLING_WEBHOOK_SECRET STRIPE_SECRET_KEY"` is dead (shellcheck SC2034,
  already on main). Either use it to build the jq filter, or delete it. CI does not run shellcheck, so this goes
  unnoticed.
- **S2. `purge-job.sh` (the `[ -n "$present" ] && remove=(...)` line).** This relies on the errexit exemption for
  `&&` lists at the end of an `elif` body. That is correct, but it is fragile if someone later adds a command after
  it. A plain `if [ -n "$present" ]; then remove=(...); fi` would say the same thing with no subtlety.
- **S3.** If someone later adds `az extension add --name containerapp` (for preview features), recheck R2 against
  that extension's `update_containerappsjob`. A one-line comment next to the workflow's az setup would keep that
  dependency visible.
