# Azure budget

Cap: $80 of Azure for Students credit, resource group `rg-ai-studio` only.
Ask Vishal first if one resource would cost more than $10 a month or the projected total would pass $80.

Month-to-date spend: see the spend report below (spend unknown (no_data), updated 2026-11-24T17:39:39Z)

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
| `id-starter-app`, `id-starter-migrate` (user-assigned managed identities for Entra database sign-in, ADR 0003) | _starter | - | 0 | planned (T-18; created with the starter release) |
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
| 2026-11-24 | cf1a | T-12 full run, 15 calls (1 rejected probe, 12 done, 2 HTTP 502) | 11,263 | 36,041 | most | ~4.49 recorded (≤7.95 if the two 502s were billed at their full output cap) |
| 2026-11-24 | e08c | T-56 tuning, 5 sheets (1 rejected probe at effort low, HTTP 400, unbilled); effort medium | 10,356 | 15,449 | most | 2.01 (ledger) of the $12 Q-11 cap |

A full T-12 benchmark at ~650k output tokens would be about $78 at that price. Vishal chose Q-7 B (2026-11-24): pro only, at most 20 documents in total, hard cap $15 of model spend for T-12.

T-56 so far: $2.01 of $12 (Q-11 A). The test set preflight needs 30 x $0.316 + one worst-case call ($1.02) = $10.50 and only $9.99 is left, so the test cannot start inside the cap (Q-12).

T-12 total so far: ~$7.89 recorded (≤$11.35 worst case) of the $15 Q-7 B cap; the 20-document call limit is used up, so T-12 makes no more model calls.

<!-- spend:auto:start -->
## Spend report (written daily by .github/workflows/azure-spend.yml)

- Updated: 2026-11-24T17:39:39Z. Covers resource group rg-ai-studio only; Cost Management data can lag by up to a day.
- Status: no_data: Azure returned no cost rows (new subscription, data lag, or an unsupported offer). Spend is unknown.
- Cost rows returned: month to date 0, since start 0, by resource 0
- Projected monthly cost from the table above: $17015.20
- Last alert level: 0% (since 2026-11-01)
- Inventory: 0 resources in rg-ai-studio, 0 not in the table above

| Resource | Type | Cost this month | In the table above? |
|---|---|---|---|
| (no resources or costs seen) | - | - | - |
<!-- spend:auto:end -->
