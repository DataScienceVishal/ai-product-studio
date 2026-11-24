# Azure budget

Cap: $80 of Azure for Students credit, resource group `rg-ai-studio` only.
Ask Vishal first if one resource would cost more than $10 a month or the projected total would pass $80.

Month-to-date spend: not reported yet (board task T-2)

| Resource | Product | Created (UTC) | Estimated $ per month | Status |
|---|---|---|---|---|
| `psql-studio-znp96r` (Postgres Flexible Server, Burstable B1ms, 32 GB, 7-day backups) | shared | - | 18.13 without the student free allowance ($13.87 compute + $4.26 storage); 0 while the 12-month allowance (750 h B1MS, 32 GB) applies | planned (approved by Vishal, Q-5 A; create at first G3) |
| `acrstudioznp96r` (Container Registry Basic, 10 GiB included) | shared | - | 5.07 ($0.1666 a day) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `cae-studio` (Container Apps environment, Consumption profile only, no own network) | shared | - | 0 (no environment fee without Dedicated profiles, private endpoints or maintenance windows) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `log-studio` (Log Analytics, 30-day retention, 0.1 GB a day cap) | shared | - | 0 (first 5 GB a month free) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `id-studio-acrpull` (managed identity for image pulls) | shared | - | 0 | planned (approved by Vishal, Q-5 A; create at first G3) |
| `ca-starter` (container app, 0.5 vCPU, 1 GiB, scales 0 to 1) | _starter | - | 0 inside the free grant (about 100 active hours a month); 0.076 per active hour after that | planned (approved by Vishal, Q-5 A; create at first G3) |
| `caj-starter-migrate` (job, one run per release) | _starter | - | 0 (inside the free grant) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `caj-starter-purge` (scheduled job, daily) | _starter | - | 0 (inside the free grant) | planned (approved by Vishal, Q-5 A; create at first G3) |
| (Azure OpenAI tokens for ca-starter, existing deployment) | _starter | - | 0 with ai_provider=fake (the default); at most 6.10 with azure and the 100,000-token daily cap | planned (approved by Vishal, Q-5 A; create at first G3) |

Planned for T-7: `products/_starter/ADR/0002-azure-deploy.md` has the sources and options. Projected: $23.20 a
month if the student free allowance doesn't cover Postgres (the $80 then lasts about 3.4 months), $5.07 if it does.
Nothing exists yet: the deploy workflow refuses to create anything until Vishal sets `STUDIO_AZURE_APPROVED=yes`.

## Azure OpenAI token log (existing deployment gpt-5.4-pro, outside our resources; draws on the same credit)

Price per token for gpt-5.4-pro is not confirmed. As an assumption, the gpt-5-pro list price is about $15 per million input tokens and $120 per million output tokens (reasoning tokens count as output). Check this before any bigger run.

| UTC | Run | Use | Input | Output (incl. reasoning) | Reasoning | Est. $ (assumed price) |
|---|---|---|---|---|---|---|
| 2026-11-23 | 7a98 | T-1 test call | ~20 | 41 | 21 | <0.01 |
| 2026-11-24 | f468 | T-12 pilot, 5 calls | 5,709 | 27,619 | 22,509 | ~3.40 |

A full T-12 benchmark at ~650k output tokens would be about $78 at that price, i.e. the whole credit. It must not run on the pro deployment (see HURDLES: a mini deployment is needed first).
