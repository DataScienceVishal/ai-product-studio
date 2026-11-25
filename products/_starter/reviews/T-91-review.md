# Review: T-91 AI cost guard tied to the deployed model

- Branch: `p/_starter/T-91-cost-guard` at b08031b, diffed against `main` (`git diff main...p/_starter/T-91-cost-guard`)
- Reviewer: reviewer agent, 2026-11-25
- **Verdict: CHANGES** (2 required fixes, both small)

## Summary

The design is right and most of it is well done. One rule lives in `backend/app/aicost.py` (stdlib only). The app applies it at startup and `infra/cost-guard.sh` applies it in the check job. Both see the deployment from the `AZURE_OPENAI_DEPLOYMENT` secret, which is passed through `env:` and never interpolated into `run:`. Unknown or versioned deployment names fail closed. Bad numbers (blank, nan, inf, 0, negative, text) are rejected on both paths. The tests are strong: 8 of 8 hand mutations were caught.

Two things stop it merging:

1. An explicit price can be lower than the table price and silently defeat the guard. This re-creates the exact bug T-91 exists to fix, through a repository variable that no code review sees.
2. The claim that the deployment name is "never printed" is false on the app side. Pydantic's `input_value` repr prints parts of the settings dict. I reproduced it printing the tail of the deployment name and, in another run, the whole `AZURE_OPENAI_API_KEY`. The new test hides this by cutting the message at `input_value`.

## Correctness checks asked for

- **Is the global cap the real bound?** Yes. The only AI call site is `routes/notes.py:114-123`. It always calls `reserve(..., global_daily_cap=settings.ai_global_daily_tokens)` under `GLOBAL_LOCK` (`ai.py:489,510`), and `tokens_today_all_tenants` includes rows from deleted tenants. The per-call reservation is an upper bound: input bytes are at least input tokens, plus `max_output_tokens` plus reasoning headroom (`ai.py:92-100`). `settle()` writes billed usage, and that can't exceed the reservation because failed or unreadable calls are billed at the full budget. So per UTC day, recorded tokens are at most the cap. The known gaps are older than this branch and bounded: a stale reservation is zeroed after 15 minutes (`ai.py:462-475`), which costs at most one estimate per killed process, and 5xx retries are not billed.
- **Price per million: input, output, reasoning.** Every capped token is charged at the OUTPUT price (`aicost.py:25-37`). That is conservative: input is 6 to 8 times cheaper, and reasoning is billed as output, which the Responses parser already counts inside `output_tokens` (`ai.py:374`). Correct.
- **Table figures.** gpt-5-nano 0.40, gpt-5-mini 2.00, gpt-5 10.00, gpt-5-pro 120 and gpt-5.4-pro 180 are the vendors' output list prices. They match `state/BUDGET.md:28,36` (gpt-5.4-pro $30/$180 with OpenAI and Microsoft sources; gpt-5-mini $0.25/$2.00). They are clearly labelled ESTIMATES with a date. Good.
- **Where 6.10 comes from.** `state/BUDGET.md:20`, the ca-starter Azure OpenAI line: "at most 6.10 with azure and the 100,000-token daily cap". Cited correctly in `aicost.py:19-21` and in config.
- **Edge cases tried by hand.** `" 2.00 "` parses to 2.0. `NaN`, `Infinity` and `0` are rejected. `GPT-5.4-PRO` resolves to 180. `gpt-5-mini-2025-08-07` and `""` are unknown and refused. With the fake provider nothing is checked. With azure, a cap of 0 refuses to start, which is fine (use fake to turn AI off). A deployment name starting with `-` makes argparse fail closed (see suggestion 3).
- **Bicep** (read only, no `az` here). `main.bicep:58-59` uses `param aiPricePerMillionTokens string = ''`. `main.bicep:352-359` has `var aiPriceEnv = empty(...) ? [] : [ {...} ]` concatenated into `webEnv`. That is valid syntax, and the conditional logic matches the app: unset means use the table. `main.bicepparam:18-19` uses `readEnvironmentVariable('AI_PRICE_PER_MILLION_TOKENS', '')`, which the deploy job's env provides (`_starter-deploy.yml:161`). The jobs force `AI_PROVIDER=fake` (`main.bicep:384-392`), so the migrate and purge jobs can't trip the new startup check. Correct.
- **Workflow.** The check step (`_starter-deploy.yml:109-118`) gets `AI_PROVIDER`, the deployment secret (with the same `|| 'gpt-5-mini'` fallback as the deploy job at line 272) and the variable, all through `env:`. There is no `set -x`. `cost-guard.sh:64` captures the aicost output, and that output never contains the deployment name (tested by `test_unknown_deployment_without_price_fails_with_azure` and the pro test). The workflow is dispatch-only and the check job has no `environment:`, so repo secrets resolve there just as they do in the deploy job.

## Critical issues (must fix)

### C1. An explicit price below the table silently defeats the guard
`backend/app/aicost.py:52-55`, `infra/cost-guard.sh:59`, `_starter-deploy.yml:115,161`

`resolve_price` returns the explicit price whenever one is set, even for a deployment the table knows. Reproduced:

```
AI_PROVIDER=azure AZURE_OPENAI_DEPLOYMENT=gpt-5.4-pro AI_PRICE_PER_MILLION_TOKENS=0.0001 bash infra/cost-guard.sh t.json   # tokens 100000
-> exit 0, "1 template(s) use only the Consumption profile..."
```

The app accepts the same values. T-91 exists because a fixed $2 price sat next to a $180 model. Today one repository variable, set with `gh variable set` and never code-reviewed, re-creates that bug: up to $540 a month against $80 of credit. The tests `test_explicit_price_overrides_the_table_both_ways` (`tests/test_aicost.py:57`) and `test_explicit_env_price_overrides_table_in_both_directions` (`tests/test_cost_guard.py:112`) assert the bypass as intended behaviour. The docs say "an explicit price beats the table" but never mention the risk.

**Fix:** for a deployment in the table, use `max(explicit, table)`, so an explicit price can only raise the price, never lower it. Keep the explicit price as the only source for unknown deployments. Flip the "under" halves of the two tests to expect failure, and add one line to the README and `.env.example` saying a lower price needs a code change to the table, which goes through review.

### C2. Settings errors print secret values through `input_value`
`backend/app/config.py:22` (and the new check at `config.py:139-144`), `tests/test_aicost.py:50`

Pydantic appends `input_value={...}` with a shortened repr of the whole settings input to every `ValueError` raised in `_safe_settings`. Reproduced on this branch:

- `AZURE_OPENAI_API_KEY=SUPERSECRETKEY123`, deployment `gpt-5.4-pro`, then the startup message ends `input_value={'env': 'prod', 'database...y': 'SUPERSECRETKEY123'}`. The full key appears.
- deployment `my-secret-deployment-name` gives `input_value={'azure_openai_endpoint':...secret-deployment-name'}`.

Which fields fall in the printed window depends on which settings are set. The same leak exists for the other validators, so it is older than this branch. But T-91 adds the startup failure most likely to fire, since the real secret is gpt-5.4-pro, and it claims the name is never printed. The test works around the leak with `.split("input_value")[0]` instead of catching it. Container stderr goes to Log Analytics.

**Fix:** add `hide_input_in_errors=True` to `SettingsConfigDict` at `config.py:22`. Make the test assert on the full `str(err.value)`, and add a test that a set `azure_openai_api_key` doesn't appear in the error.

## Suggestions (not blocking)

1. `aicost.py:23` `DAYS_PER_MONTH = 30` understates a 31-day month by 3.3%. The default gpt-5-mini cap costs 100,000 x 31 x 2 / 1e6 = $6.20, which is over the $6.10 that the rule claims as its worst case. Use 31, or reword "worst case". The margin is already thin: Azure Data Zone and Regional deployments list about 10% above Global, and the table doesn't model that. Say so next to the table.
2. `README.md:187` says "about 1,130 tokens a day: one summary", and `NEXT.md:10` says "lower to about 1,100". The smallest reservation is 287 + 17 + 1,200 = 1,504 tokens (chat) or 3,004 (Responses), so a cap of 1,129 allows **zero** calls. Write plainly that gpt-5.4-pro at $6.10 means AI is effectively off, so the real choices are a cheaper deployment or a budget raise from Vishal.
3. `cost-guard.sh:64`: pass `--deployment="$deployment"` (and the same `=` form for `--price` and `--tokens`). Then a value starting with `-` is parsed as a value, not as an argparse usage error. It already fails closed and doesn't print the name, so this is tidiness.
4. `cost-guard.sh:63` checks an explicit price even with `AI_PROVIDER=fake`, but the app doesn't. That is harmless (it fails closed), but the two paths differ. Say so in the comment, or skip the check with fake.
5. Each product copied from the starter gets its own default of $6.10 while every product draws on one credit and one shared OpenAI deployment. Worth a line in ADR 0002 so the product-level budget lines in `state/BUDGET.md` add up.
6. The local venv is Python 3.11 (`.venv/lib/python3.11`) but the README asks for 3.12. CI should be on 3.12. Nothing here depends on it.

## Test evidence (exact head b08031b)

| Suite | Result |
|---|---|
| Backend `pytest` (Postgres 16, ephemeral DB) | **643 passed, 1 skipped** (`test_spa.py:103`, frontend not built), 87.7 s |
| Frontend `npx vitest run` | **203 passed** (7 files) |
| `infra/test-deploy-workflow.sh` | **102 passed, 0 failed** (actionlint not installed, skipped) |
| `infra/test-deploy-role.sh` | **67 passed, 0 failed** |
| `infra/test-db-setup.sh` | **33 passed, 0 failed** |
| `infra/test-bicep-identities.sh` | not run: needs compiled Bicep (no `az` here) |

Mutation check (on a scratch copy, scoped to `tests/test_aicost.py` and `tests/test_cost_guard.py`; base run 0 failures):

| Mutation | Failed tests |
|---|---|
| drop `.strip().lower()` from the table lookup | 1 |
| `cost > budget` changed to `cost > budget * 100` | 12 |
| app startup check disabled (`if False:`) | 4 |
| cost-guard ignores `AI_PROVIDER=azure` | 4 |
| cost-guard ignores the env deployment (template default only) | 2 |
| `DAYS_PER_MONTH = 1` | 9 |
| price finite/positive check weakened to a NaN check only | 4 |
| cost-guard ignores the env price | 7 |

All 8 were caught. The tests bite. The gaps are the two behaviours the tests assert on purpose (C1) or step around (C2).
