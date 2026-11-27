# T-161 security and privacy pass: product starter and CI changes since e40fea6

- Scope: `git diff e40fea6..HEAD -- products/_starter .github` (HEAD f628601). T-100 covered everything up to e40fea6,
  so its findings are not repeated here. Code reviewed: `backend/app/ai.py`, `backend/app/aicost.py`,
  `backend/app/routes/notes.py`, `backend/tests/test_ai.py`, `infra/main.bicep` (comment only), `infra/README.md`,
  `infra/test-deploy-workflow.sh`, `.github/workflows/_starter-deploy.yml`, `.github/workflows/azure-spend.yml`, plus the
  doc-only changes to `.env.example`, `README.md` and `ADR/0002-azure-deploy.md`. The main change is T-101, the runtime
  check on the model Azure reports, which closes part of T-100 M1. The other change is the separate read-only spend
  identity and the half-set-secret checks in the workflows.
- Reviewer: security agent, 2026-11-26. Code not modified. Probes were run from the scratchpad, not added to the repo.

## Verdict: CHANGES

1 medium, 2 low, 3 info. Nothing is exposed right now. The starter is not deployed (`state/BUDGET.md` lines 16-18 say
"planned"), and the deploy input `ai_provider` still defaults to `fake` (`_starter-deploy.yml:33-37`). Nobody needs to
ping Vishal.

Suggested board task for M1: "T-xx starter: make the T-101 model-guard trip survive restarts and scale-to-zero (persist
it in the database) (T-161 M1)".

## Findings

### M1 (medium, money at risk): the guard switches the AI off only until the next cold start, and the app scales to zero
- Where: `backend/app/ai.py:294` (`self.disabled = False` in `__init__`), `:314` (`self.disabled = True`, in memory
  only), `:75` (`ensure_ai_enabled` reads only that attribute); `infra/main.bicep:491` (`minReplicas: 0`).
- What is wrong: the trip is held in the Python process. Container Apps stops the only replica after a few idle minutes
  and starts a fresh process on the next request, so every cold start forgets the trip. Each new process lets at least
  one more call through to the expensive model, plus any calls already in flight. For a low-traffic demo, most
  summaries come right after a cold start, so the guard rarely stops anything. The only other signal is one `log.error`
  line per process, and nobody reads the logs. The daily spend report notices a day or two later at best.
- Evidence (probe `test_p3_restart_resets_flag`): three `AzureOpenAI` instances built the way a restart builds them,
  each getting `gpt-5.4-pro-2026-03-05` back while checked at `gpt-5-mini` prices, made **3 expensive calls**. Each
  instance tripped (`disabled is True`), and each new one started enabled again.
- Cost: one gpt-5.4-pro summary of a 20,000-character note is about 20k input x $30/M + 2,700 output x $180/M = about
  $1.10. Only the global daily token cap still applies. T-100 put its worst case at about $17.60 a day, or the $80
  credit in about 4.5 days. A trial tenant can trigger cold starts just by waiting between requests, so the scenario
  still needs an operator mistake but no longer needs heavy traffic.
- Fix: persist the trip. When `_check_reported_model` trips, write a row (for example a new `ai_guard` table with
  `fingerprint`, `reported_model` and `tripped_at`). The fingerprint is a hash of deployment, endpoint host and price
  settings, so a reviewed config change clears it on its own. `ensure_ai_enabled` (or `reserve`, which already holds
  the global lock) then refuses while a row matches the current fingerprint. A short in-process cache is fine.
  Optionally, `/api/health` could report `ai: "disabled"` so the first-deploy checklist and a smoke test can see it.
  Add a test: provider A trips, a fresh provider B built from the same settings against the same database refuses
  without calling Azure.

### L1 (low): any explicit price, even one equal to the table price, lets unknown models through for a deployment that is in the table
- Where: `backend/app/ai.py:457` (`price_explicit=explicit is not None`) and `:307` (`if self.price_explicit: return`).
- What is wrong: the docstring says an explicit price is "what the operator declared the deployment costs". That is
  true for a deployment that is not in the table, such as `chat`. For `gpt-5-mini`, though,
  `AI_PRICE_PER_MILLION_TOKENS` is only a way to raise the price (for example by about 10% for a Data Zone
  deployment), and nobody setting it is declaring the price of some other model. Today, setting it switches off the
  "unknown model" net for every deployment. Several real expensive models are unknown to the table: probe
  `test_p2_table_gaps` returns `None` for `gpt-5.4`, `gpt-5.2-pro`, `o3-pro`, `gpt-5.5-pro-2026-06-01` and `gpt-4.1`.
- Evidence (probe `test_p1_...`): deployment `gpt-5-mini`, explicit price 2.0, Azure reports `o1-pro-2025-03-19`. Both
  summaries return **200 200** and `disabled` stays **False**.
- Fix: in `build_provider`, set `price_explicit` only when the deployment is not in the table:
  `price_explicit = explicit is not None and deployment.strip().lower() not in MODEL_PRICES_PER_MILLION`. Add a test
  for the case above. Optionally, add the missing pro and reasoning models to the table so they are priced rather than
  treated as unknown.

### L2 (low): the reported model string goes into `ai_usage.model` without checks, so odd values can make spend uncounted
- Where: `backend/app/ai.py:394` (`model=reported ...`, raw), `:573` (`settle` writes it), `models.py:108`
  (`String(80)`), `ai.py:507` (`_PENDING` means `model = 'pending'`), `:516` (stale pending rows are zeroed).
- What is wrong: T-101 made the reported model drive money decisions, but the same untrusted string is written raw.
  There are two bad cases:
  - `"pending"`: the settled row looks like a live reservation. It counts against the tenant's `max_in_flight` for 2
    minutes, and after 15 minutes the sweep turns it into `abandoned` with 0 tokens, so the real spend disappears from
    every cap.
  - More than 80 characters: `settle` fails with a `DataError` after the model has already run. The client gets a 500
    and the reservation stays `pending`, so after 15 minutes the spend is zeroed again.
- Evidence (probe `test_p4_...`):
  - `"pending"`: **200 200**, rows `('note_summary', 'pending', 12, 7)` x2.
  - 81 x `"x"`: **500 500**, `DataError ... sqlstate 22001`, rows `('note_summary:reserved', 'pending', 1553, 0)` x2.
- Why low: it needs the upstream to send a strange `model` value. The endpoint comes from a secret and Azure is
  trusted, so this is defence in depth against a misconfigured or OpenAI-compatible proxy endpoint. Note that the T-101
  log line already truncates the value to 80 characters (`ai.py:315`), but the stored value is not truncated.
- Fix: normalise once in `complete`. Accept only `^[A-Za-z0-9._:-]{1,64}$`, and use `"unknown"` for anything else,
  including the reserved words `pending` and `abandoned`. Use the result for both the price check and `AIResult.model`.
  Optionally, also have `settle` truncate to the column width. Add tests for `"pending"` and a 200-character name.

### I1 (info): the spend workflow's service-principal fallback still runs from any branch
- Where: `.github/workflows/azure-spend.yml:71` (`elif [ "$HAS_COST_SP" = "true" ]; then mode=sp`).
- This was already there before T-161, and the new ordering does not make it worse. If neither OIDC identity is set
  and `AZURE_COST_CREDENTIALS` is, a `workflow_dispatch` from any branch signs in with the long-lived service
  principal. The OIDC paths are correctly limited to main, and when a spend or deploy client id is set the run never
  falls through to the SP: it uses that identity or fails. The fix is already planned: delete `AZURE_COST_CREDENTIALS`
  and this branch after the first green run with `id-github-spend` (comment at `azure-spend.yml:14`).

### I2 (info): the deploy role still has the cost-query actions
- Where: `infra/README.md` ("Once the spend identity is live, both `Microsoft.CostManagement/query/*` ... can be
  dropped"). This is documented and harmless while the deploy identity is still a spend fallback. Track it with the
  I1 clean-up so the deploy identity ends up least-privilege.

### I3 (info): the reported model in the error log
- `ai.py:315-317` logs only the reported model (truncated to 80 characters) and the two prices. There is no tenant id,
  prompt, answer, endpoint or key in that line. The logs are JSON (see the probe output), so a newline in the value
  cannot forge a log line. Fine as is.

## Checked and fine

- **T-101 coverage of T-100 M1.** A known, more expensive model is refused even with an explicit price
  (`test_known_dearer_model_is_refused_even_with_an_explicit_price`). A date suffix is stripped and case is ignored. The
  longest-prefix match does not price `gpt-5.4` or `gpt-5.4-pro` as `gpt-5` (prefix plus `-` rule). A missing or
  non-string `model` counts as unknown. The check runs before the parse and no-answer branches, so a billed reply with
  no answer still trips it (`test_billed_no_answer_reply_from_a_dearer_model_still_trips_the_guard`). The first
  expensive call is still settled with its real tokens. `ensure_ai_enabled` runs before `reserve` in `notes.py:113`, so
  a refusal leaves no reservation (asserted in `test_dearer_reported_model_keeps_first_call_then_refuses_the_rest`).
  `complete()` checks again for any other caller. `checked_price=None` only happens when `resolve_price` raises, and
  `Settings._safe_settings` (`config.py:142`) already refuses to start in that case.
- **Error messages.** The refusal is a 503 `ai_budget_reached` with "The AI is switched off until the team fixes its
  configuration." It reveals no model, price, deployment or endpoint.
- **Workflows.** The new expressions in `env:` (`HAS_DEPLOY_ID`, `HAS_SPEND`, `HAS_SPEND_ID`) evaluate
  `secrets.X != ''` to a boolean, so no secret value reaches the shell. There is no `${{ }}` inside the new `run:`
  lines. `$GITHUB_REF` is read from the environment, not interpolated. The new `azure/login` step is pinned to the same
  full SHA (`a641126d...`, v3.1.0) as the others. Triggers are still `schedule` and `workflow_dispatch` only (no
  `pull_request_target`). Permissions are unchanged (`contents: read` at the top, `id-token: write` only on the jobs
  that sign in). The spend identity is preferred and, when set, the deploy identity is never used. A half-set client id
  fails loudly rather than falling back to broader credentials, in both workflows. The `::notice::` lines name the
  identity, never an id. `test-deploy-workflow.sh` checks the 40-row deploy gate truth table and the spend sign-in
  table.
- **Secrets scan** of the full diff (Stripe live/test keys with a body, `whsec_`, AWS `AKIA`, GitHub tokens, PEM private
  keys, `AccountKey=`, Slack tokens, Telegram bot tokens, JWTs): **no matches**.
- **Privacy.** No new data is collected. Prompts and answers are not logged. `store: False` is still sent on the
  Responses API. `ai_usage` gains no personal fields.
- **Dependencies.** No change to `requirements*.txt` or the frontend lockfile in scope, so T-100's `pip-audit` and
  `npm audit` results (0 known vulnerabilities) still stand.

## Tests run

- `python -m pytest tests/test_ai.py` (Python 3.11 venv, local Postgres 16): **145 passed, 1 warning** in 14.4 s.
- `bash infra/test-deploy-workflow.sh`: **passed: 117, failed: 0** (actionlint skipped, not installed).
- Probes (scratchpad, `-p tests.conftest`): 9 ran. Results are quoted under M1 (P3), L1 (P1, P2) and L2 (P4).
