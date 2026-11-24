# Review: p/_starter/T-34 at 90df50f (follow-ups S5, R3, R4, R6 from T-33)

Reviewer, 2026-11-24. Diff: `git diff origin/main...90df50f` (6 files, +48 -8).

## Verdict: CHANGES

One item blocks: the README still documents the old 500,000 default. The code, infra and tests are correct.

## Summary

| Item | Status | Evidence |
|---|---|---|
| S5 `AZURE_OPENAI_API` from Bicep | done | `main.bicep:43-49` param `azureOpenAiApi`, `@allowed` auto/chat/responses, default `auto`. This matches `config.py:54` `Literal["auto","chat","responses"] = "auto"`. It is passed in `webSettings` (`main.bicep:224-227`), so it reaches the web app only, which is correct because the purge job makes no AI calls. Checked by reading; Bicep was not compiled here, so CI must confirm. |
| R3 stricter cost guard | done | 20 hand-made templates, results below. Every bad input fails closed. |
| R4 app default 100,000 | code done, docs not | `config.py:62` is now `100_000`. **`README.md:89` still says "default 500,000"** (critical issue 1). |
| R6 `.env.example` | done | Both variables are listed, and the comment formula `6.10 / (30 x price) x 1,000,000` matches README "Sizing the daily AI cap". |
| Test hermeticity | done | `test_settings_accept_only_known_auth_modes` uses `monkeypatch.delenv("AZURE_OPENAI_AUTH")`. |

### Tests

Run in `products/_starter/backend`, with TEST_DATABASE_URL and DATABASE_URL set to the local `starter_test`:

- `python -m pytest -q -p no:warnings`: all dots, 1 `s`, no failures. With `-q` the summary line is suppressed, presumably because pyproject also passes `-q`.
- `python -m pytest -p no:warnings`: **238 passed, 1 skipped in 29.15s**
- the same run with `AZURE_OPENAI_AUTH=managed_identity` exported: **238 passed, 1 skipped in 32.35s**

### cost-guard.sh, run on hand-made compiled templates (jq 1.7)

| Template | rc | Result |
|---|---|---|
| real deployment defaults (int 100000, string "2.00", plus azureOpenAiApi) | 0 | pass ($6.00) |
| 500000 / "2.00" | 1 | "$30.00 a month, over the $6.10 AI budget" |
| 101666 / 2.00 (largest cap that fits the budget) | 0 | pass |
| 101667 / 2.00 | 1 | "$6.10 a month, over the $6.10" (rounding, see S-b) |
| price "0" / tokens -5 | 1 | "must both be above 0" |
| both params without defaults / defaultValue null / only one param | 1 | "must both exist with defaults" |
| price "abc", tokens `[parameters('x')]` expression, tokens `true` | 1 | "not a number" |
| price "nan" | 1 | "must both be above 0" (fails closed; the message is slightly off) |
| price "infinity" / tokens 1e30 | 1 | over; the infinity message prints a 300-digit dollar figure (cosmetic) |
| price "0.0001", tokens 1 | 0 | pass |
| price " 2.00" (leading space) | 0 | pass ($6.00); jq accepts it, which is harmless |
| no AI params at all / no `parameters` key | 0 | pass, as intended for shared.json |
| `"parameters": []` | 5 | jq aborts under `set -e`, so it fails closed without a message (the same as before) |
| `AI_MONTHLY_BUDGET_USD=abc` | 1 | fails closed, but the message blames "tokens or price" (carried over from T-33) |
| `AI_MONTHLY_BUDGET_USD=5` | 1 | "$6.00 ... over the $5.00" |
| three files (zero, real, over) | 1 | 2 problems counted, and the loop continues |

## Critical issues

1. **README.md:89 documents the old default.** It reads "studio-wide AI budget per UTC day (default 500,000)", but `config.py:62` now has 100,000. The README is what a product copying the starter reads, so the doc and the code disagree on the one number that protects the $80 credit. Fix: change it to "(default 100,000; the Bicep default too)".
   - The 500,000 figures in SECURITY.md (lines 667, 693, 921, 954, 993, 1081) are historical test evidence recorded against the old default. Leave them, or add a one-line note that the default is now 100,000.
   - `billing.py:47` `ai_monthly_tokens=500_000` is the Starter plan allowance. It is a different setting and is correct.

## Suggestions (not blocking)

- **S-a. `main.bicepparam` doesn't wire `azureOpenAiApi`.** Every deploy gets `auto`, and changing it means editing Bicep. For consistency with the other AI params, add `param azureOpenAiApi = readEnvironmentVariable('AZURE_OPENAI_API', 'auto')`, plus the workflow env, before any product switches to `responses`.
- **S-b. Rounding at the boundary.** With $6.1000x the guard prints "$6.10 a month, over the $6.10 AI budget". Use `%.4f` when the rounded values are equal, or say "above".
- **S-c.** Make the `infinity` and `nan` messages say "not a finite number". Separately, check that `AI_MONTHLY_BUDGET_USD` is numeric once, up front (the R3 note carried over from T-33).
- **S-d.** The guard still has no committed test harness. A small `infra/test-cost-guard.sh` that runs the table above would stop regressions. NEXT.md and this review are the only record of it now.
- **S-e.** S1, S2, S3 and S7 from the earlier reviews are still open, and none of them block.

## Security and performance

No new endpoints, queries or secrets. The new Bicep param is restricted by `@allowed`, so it can't inject an arbitrary value. Lowering the default cap reduces the worst-case AI spend for local runs that opt into `AI_PROVIDER=azure` from about $30 to about $6 a month at $2/M.
