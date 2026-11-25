# T-100 security and privacy pass: product starter changes since 11c25d2

- Scope: `git diff 11c25d2..HEAD -- products/_starter .github` (HEAD 06e5ad5). The T-83 pass covered everything up to
  11c25d2, so this pass does not repeat its findings. Main changes: the T-91/T-95 AI cost guard (`backend/app/aicost.py`,
  `config.py`, `infra/cost-guard.sh`, `main.bicep`, `main.bicepparam`, `_starter-deploy.yml`), the T-97/T-98 built-HTML
  check (`scripts/check_built_html.py`, `_starter-ci.yml`), T-94/T-99 `LIMITED_PROVIDERS` in `app/billing.py` and
  `/api/billing/plans`, `/api/config` `billing_provider`, `errors.py`, `textsafe.py`, `routes/auth.py`, `routes/notes.py`,
  `main.py` (`redirect_slashes=False`), the frontend (`api.ts`, `App.tsx`, `pages/app.tsx`, `pages/auth.tsx`, `ui.tsx`,
  `pages/legal.tsx`), and `DATA.md`.
- Reviewer: security agent, 2026-11-25. Code not modified.

## Verdict: CHANGES

One medium finding (M1, money at risk through operator misconfiguration, nothing exposed today: the deploy default is
`ai_provider=fake`), and info notes. Nothing is exposed right now, so nobody needs to ping Vishal.

Suggested board task for M1: "T-xx starter: cost guard checks the model Azure reports, not only the deployment name
(T-100 M1)".

## Findings

### M1 (medium): the cost guard prices the deployment *name*, not the model Azure actually runs
- Where: `backend/app/aicost.py:33` (`MODEL_PRICES_PER_MILLION` keyed by deployment name) and `:53` (`resolve_price`);
  `backend/app/config.py:140` (startup check uses `azure_openai_deployment`); `infra/cost-guard.sh` (same name, from the
  `AZURE_OPENAI_DEPLOYMENT` secret). The real model is known at runtime and ignored:
  `backend/app/ai.py:353` returns `model=data.get("model", ...)`, and `routes/notes.py:129` only records it in `ai_usage`.
- Scenario: Azure deployment names are free text. A deployment named `gpt-5-mini` (or `gpt-5`) that runs gpt-5-pro or
  gpt-5.4-pro, or a renamed deployment such as `chat` with the repository variable `AI_PRICE_PER_MILLION_TOKENS` set too
  low (any value above 0 is accepted for an unknown name, and a repository variable is not code-reviewed), passes both
  the deploy check and the app's startup check at the 98,000-token cap. The real worst case is then
  98,000 x 31 x $180 / 1M = about $547 a month, or about $17.60 a day: the studio's whole $80 credit in about 4.5 days.
  This matters here because the studio already has a gpt-5.4-pro deployment drawing on the same credit
  (`state/BUDGET.md` line 26), so pointing the secret at the wrong deployment, or making a new one with a copied name, is
  a likely mistake. The token caps still hold; only the price assumption is wrong. A tenant cannot trigger this. It
  needs an operator mistake.
- Reproduction (passes today, should not when the model is pro):
  `env -i PATH=/usr/bin:/bin AI_PROVIDER=azure AZURE_OPENAI_DEPLOYMENT=gpt-5-mini AZURE_OPENAI_API_KEY=k AZURE_OPENAI_ENDPOINT=https://x.example/ .venv/bin/python -c "from app.config import Settings; print(Settings().ai_global_daily_tokens)"`
  prints `98000`. Nothing then compares a reply's `"model": "gpt-5.4-pro-..."` with the price that was checked.
- Fix: check the model the provider reports. In `AzureOpenAI.complete` (or in `settle`), map `data["model"]` to the
  table by longest matching prefix, ignoring a date suffix (`gpt-5.4-pro-2026-03-05` -> `gpt-5.4-pro`). If that price is
  above the price the startup check used, or the model is unknown and no explicit price is set: log an error with no
  tenant data, keep this call's usage, and turn the AI off for the process (return `AIUnavailable` / 503 `ai_budget_reached`
  on later calls) until the configuration is fixed. Add a test where FakeAI or a mocked httpx reply reports
  `gpt-5.4-pro-2026-03-05` while `AZURE_OPENAI_DEPLOYMENT=gpt-5-mini`: the second summarise must be refused. Optional
  second net: in the deploy job, after sign-in, read the deployment's `properties.model.name` with
  `az cognitiveservices account deployment show` and pass it to `cost-guard.sh` (only if the deploy identity can read
  that resource, which sits outside `rg-ai-studio`, so the runtime check is the one to rely on).

### I1 (info): `check_built_html.py` misses some constructs, but the CSP header still blocks every one of them
- Where: `scripts/check_built_html.py:19-20` (`_URL_ATTRS`) and `handle_starttag`.
- Probe (`python3 -I <probe> scripts/check_built_html.py`): not flagged are `<iframe srcdoc="<script>...">`,
  `<meta http-equiv="refresh" content="0;url=javascript:...">`, `<object data="javascript:...">`, `<base href=...>`,
  `<svg><animate attributeName="href" values="javascript:...">`, `<script src="data:...">`, and
  `<script src="https://cdn.example/x.js">`. Flagged correctly: inline `<script>` (including `type="module"`), `<style>`,
  `style=`, `on*=`, and an entity-encoded `&#106;avascript:`.
- Why it is info: the checker only stops silent breakage. The security control is `HTML_CSP` (`backend/app/spa.py:29`,
  `script-src 'self'`, `default-src 'self'`, `base-uri 'none'`, `form-action 'self'`, `frame-ancestors 'none'`), which
  blocks all of the above. The one that matters in practice is a third-party `<script src>`. The checker passes it, the
  browser blocks it, and a builder might "fix" that by loosening the CSP. Suggestion: also flag `src` on `<script>` or
  `<link rel=stylesheet>` that is not same-origin (starts with `http`, `//` or `data:`), and add a test.

### I2 (info): anonymous callers can see the billing provider
- Where: `backend/app/routes/health.py:42` (`/api/config` returns `billing_provider`); `routes/billing.py:38`
  (`ai_allowance.trial_sized`).
- It tells anyone the deployment is mock or Stripe test mode. That is public on the billing page anyway ("Test mode: no
  real payment is taken"). There is no secret and no tenant data, so it is fine. The frontend fails closed:
  `api.ts` treats anything but a successful `"mock"` as not mock.

### I3 (info): `AI_MONTHLY_BUDGET_USD` has no ceiling in code
- Where: `backend/app/config.py:99`; `infra/cost-guard.sh` reads it from the environment.
- Neither the Bicep app env nor the workflow sets it, so raising it needs a reviewed change to `main.bicep` or the
  workflow. That is acceptable. If a product later wires it to a repository variable, cap it in code (for example at most
  `DEFAULT_MONTHLY_BUDGET_USD` unless an ADR says otherwise).

## Checked and fine

- **Fail-open values.** Price: blank -> table lookup, while `nan`/`inf`/`0`/negative/text are refused (`aicost.parse_price`,
  `Field(gt=0, allow_inf_nan=False)`). An unknown deployment with no price is refused. An explicit price can only raise
  a table price (`max`). Tokens <= 0 or non-finite are refused with azure. Budget <= 0 or non-finite is refused (jq in the
  shell, `Field` in the app). Fake provider: nothing is spent, nothing is checked. `ai_trial_share` NaN/negative fails
  closed at runtime, and the global cap is checked on its own (`ai.py` reserve). `DAYS_PER_MONTH=31` and the output price
  for all tokens make the figure conservative.
- **Guard vs deploy consistency.** The check job and deploy job use the same `secrets.AZURE_OPENAI_DEPLOYMENT || 'gpt-5-mini'`
  and the same `vars.AI_PRICE_PER_MILLION_TOKENS`. `main.bicepparam` reads the same variable, and the tokens come from the
  template default, which nothing overrides. The app re-checks at startup, so a wrong CI check still cannot start an
  over-budget revision.
- **Tenant bypass of AI caps.** `routes/notes.py` still derives `limited` from the server-side subscription
  (`sub.status`, `sub.provider in LIMITED_PROVIDERS`), so a tenant controls nothing in it. Moving the set to `billing.py`
  kept its contents (`{"mock","stripe"}`). Reservations hold the tenant and global advisory locks. Failed sends bill the
  full budget (`ai.py` TransportError, unreadable 200). No new route changes a cap.
- **Secrets in errors and logs.** `hide_input_in_errors=True` works: with azure, an unknown deployment named
  `secret-dep-name` and key `SUPERSECRETKEY123`, the `ValidationError` text contains neither (reproduced). The aicost
  messages contain tokens and price only, never the deployment. `cost-guard.sh` prints only aicost's stderr. The
  `json_invalid` branch in `errors.py` no longer echoes parser detail. The 422 bodies still carry only field and message,
  never input.
- **Workflows.** `_starter-ci.yml` runs on push and workflow_dispatch only (no `pull_request_target`), with
  `permissions: contents: read`. The new step runs a repo script with no `${{ }}` in `run:`. The deploy check step passes
  `inputs.ai_provider` (a choice input), a secret and a variable through `env:` only. Every `uses:` is pinned to a full
  SHA. The top-level permissions are `contents: read`, and `id-token: write` is only on the deploy job.
- **Tenancy.** `list_notes` adds only a tie-break order (`Note.id`). The count query is still tenant-filtered. The new
  `test_notes_with_the_same_timestamp_page_in_a_stable_order` covers paging. The frontend "Show more" uses only `offset`
  on the tenant-scoped endpoint.
- **XSS and redirects.** There is no `dangerouslySetInnerHTML`, `innerHTML`, `eval` or `new Function` in `frontend/src`.
  `safeNext` still refuses other origins, `//`, `\` and dot-segment tricks, and now also refuses sign-in pages (which
  stops the loop). `navigate(..., true)` uses `replaceState` with the same values.
- **T-83 follow-ups are all closed.** L1: `test_unverified_owner_cannot_open_the_billing_portal`. L2: `MockPortal` renders
  only when `/api/config` says `mock`. I1: `quote(customer_ref, safe='')`.
- **Input.** ASCII-only emails at sign-up and blank or invisible company names are refused. `NoteBody` turns
  invisible-only bodies into empty strings. `redirect_slashes=False` removes redirect responses. `CsrfGuard` still
  matches every `/api/` write.
- **Privacy text vs data flows.** `DATA.md`, `legal.tsx` and the Help FAQ now say France Central (EU), which matches
  `main.bicepparam` (`location = 'francecentral'`) and the infra README. They also say Azure OpenAI may process prompts
  outside the UK and EU depending on deployment type, which is accurate and suitably hedged. `store: False` is still sent
  on the Responses API. The `ai usage` log line has feature, token counts and model, and no tenant or personal data. The
  privacy and terms pages are drafts and not legal advice, as before.
- **Secrets scan.** The diff and HEAD tree were scanned for Stripe live/test keys with a body, `whsec_`, AWS, GitHub
  tokens, PEM private keys and Azure `AccountKey=`. The only matches are test fixtures (`SUPERSECRETKEY123` in
  `test_cost_guard.py`, a fake key by design).

## Tests and audits run

- Backend: `python -m pytest` with a throwaway local Postgres 16 and Python 3.11 venv: **672 passed, 1 skipped** in 64 s.
- `pip-audit -r backend/requirements.txt`: **No known vulnerabilities found**.
- `npm audit` (frontend lockfile, all and `--omit=dev`): **found 0 vulnerabilities**.
- Frontend vitest: not run (no `node_modules`). The changed UI was reviewed from source.
