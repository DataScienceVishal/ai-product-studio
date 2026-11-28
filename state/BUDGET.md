# Azure budget

Cap: $80 of Azure for Students credit, resource group `rg-ai-studio` only.
Ask Vishal first if one resource would cost more than $10 a month or the projected total would pass $80.

Month-to-date spend: see the spend report below (spend unknown (no_data), updated 2026-11-27T22:13:29Z)

| Resource | Product | Created (UTC) | Estimated $ per month | Status |
|---|---|---|---|---|
| `id-github-deploy` (user-assigned managed identity, francecentral; GitHub OIDC for main only, Contributor on rg-ai-studio) | shared | 2026-11-24T23:24Z (by Vishal) | 0 | live |
| `psql-studio-znp96r` (Postgres Flexible Server, Burstable B1ms, 32 GB, 7-day backups) | shared | - | 18.13 without the student free allowance ($13.87 compute + $4.26 storage); 0 while the 12-month allowance (750 h B1MS, 32 GB) applies | planned (approved by Vishal, Q-5 A; create at first G3) |
| `acrstudioznp96r` (Container Registry Basic, 10 GiB included) | shared | - | 5.07 ($0.1666 a day) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `cae-studio` (Container Apps environment, Consumption profile only, no own network) | shared | - | 0 (no environment fee without Dedicated profiles, private endpoints or maintenance windows) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `log-studio` (Log Analytics, 30-day retention, 0.1 GB a day cap) | shared | - | 0 (first 5 GB a month free) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `id-studio-acrpull` (managed identity for image pulls) | shared | - | 0 | planned (approved by Vishal, Q-5 A; create at first G3) |
| `ca-starter` (container app, 0.5 vCPU, 1 GiB, scales 0 to 1) | _starter | - | 0 inside the free grant (about 100 active hours a month); 0.076 per active hour after that | planned (approved by Vishal, Q-5 A; create at first G3) |
| `caj-starter-migrate` (job, one run per release) | _starter | - | 0 (inside the free grant) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `caj-starter-purge` (scheduled job, daily) | _starter | - | 0 (inside the free grant) | planned (approved by Vishal, Q-5 A; create at first G3) |
| `caj-starter-cancels` (scheduled job, every 30 minutes, T-176) | _starter | - | 0 inside the free grant: 1,440 runs a month x about 10 s = 14,400 s; at 0.25 vCPU / 0.5 GiB that is 3,600 vCPU-s and 7,200 GiB-s, about 2% of the free 180,000 vCPU-s and 360,000 GiB-s. Even with no grant: 3,600 x $0.000024 + 7,200 x $0.000003 = about $0.11. Replica timeout 15 minutes caps a stuck run | planned (same approval as the purge job; created by the starter release) |
| `id-starter-app`, `id-starter-migrate` (user-assigned managed identities for Entra database sign-in, ADR 0003) | _starter | - | 0 | planned (T-18; created with the starter release) |
| (Azure OpenAI tokens for ca-starter, existing deployment) | _starter | - | 0 with ai_provider=fake (the default); at most 6.10 with azure and the 98,000-token daily cap ($6.08 at gpt-5-mini prices; with the gpt-5.4-pro deployment the cost guard allows only ~1,093 tokens a day, so AI is effectively off until a mini deployment or a bigger budget) | planned (approved by Vishal, Q-5 A; create at first G3) |
| (no new resources) build and eval of the tender demo, local in cloud runs; if deployed later: `ca-tender`, `caj-tender-migrate/-purge/-cancels`, `id-tender-app`, `id-tender-migrate`, database `tender` on the shared server | sme-council-tender-drafting | - | 0 (inside the Container Apps free grant, shared with ca-starter; about $0.076 per active hour above it). Deploying triggers the Q-5 shared resources: a later question (DESIGN.md section 12) | planned (T-184; nothing created) |
| (Azure OpenAI tokens, gpt-5-mini via AZURE_OPENAI_DEPLOYMENT_MINI) tender eval harness, one-off, own ledger | sme-council-tender-drafting | - | 0 a month (one-off, not monthly: about $3.66 expected (4.3M tokens), hard cap $6.00 approved (Q-19 A); app path stays inside the existing $6.10 line (keep ca-starter on fake so the per-app guard is not doubled)) | approved by Vishal (Q-19 A, 2026-11-27T19:37Z): $6.00 hard cap, own ledger; no live call yet (status corrected by desk df0b 2026-11-28) |

Planned for T-7: `products/_starter/ADR/0002-azure-deploy.md` has the sources and options. Projected: $23.20 a
month if the student free allowance doesn't cover Postgres (the $80 then lasts about 3.4 months), $5.07 if it does.
Nothing exists yet: the deploy workflow refuses to create anything until Vishal sets `STUDIO_AZURE_APPROVED=yes`.

## Azure OpenAI token log (existing deployment gpt-5.4-pro, outside our resources; draws on the same credit)

Price (corrected 2026-11-24 by run 591a, T-58): gpt-5.4-pro is **$30 per million input tokens and $180 per million output tokens** (reasoning counts as output), on OpenAI's model page (https://developers.openai.com/api/docs/models/gpt-5.4-pro) and in Microsoft's Foundry launch post (https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-gpt-5-4-in-microsoft-foundry/4499785). Until then the studio assumed the older gpt-5-pro price of $15 / $120, which understated spend by about 1.5x. The Azure pricing page itself shows no figure, and an agreement could differ; the daily spend report is the final word once it returns data. The "Est. $ (assumed price)" column is kept as history; use "Real $".

| UTC | Run | Use | Input | Output (incl. reasoning) | Reasoning | Est. $ (assumed price, superseded) | Real $ ($30/$180) |
|---|---|---|---|---|---|---|---|
| 2026-11-23 | 7a98 | T-1 test call | ~20 | 41 | 21 | <0.01 | 0.01 |
| 2026-11-24 | f468 | T-12 pilot, 5 calls | 5,709 | 27,619 | 22,509 | ~3.40 | 5.14 |
| 2026-11-24 | cf1a | T-12 full run, 15 calls (1 rejected probe, 12 done, 2 HTTP 502) | 11,263 | 36,041 | most | ~4.49 recorded (≤7.95 if the two 502s were billed at their full output cap) | 6.82 recorded (≤12.02 if the 502s were billed) |
| 2026-11-24 | e08c | T-56 tuning, 5 sheets (1 rejected probe at effort low, HTTP 400, unbilled); effort medium | 10,356 | 15,449 | most | 2.01 (ledger) of the $12 Q-11 cap | 3.09 of the $12 Q-11 cap |
| 2026-11-24 | bb8d | T-56 on gpt-5-mini ($0.25/$2.00 per 1M): 2 tiny probe calls (~$0.0001, not in ledger), tuning2 5 sheets $0.034, test 30 sheets $0.223 (incl. one worst-case charge for a connection reset) | ~76,000 | ~166,000 | mini | 0.26 | 3.35 of the $12 Q-11 cap (ledger) |
| 2026-11-26 | 0abb | T-113 holiday-pay part B on gpt-5-mini ($0.25/$2.00 per 1M), 1 request, Q-16 $2 cap | 5,738 | 2,222 | low effort | 0.0059 | 0.0059 of the $2 Q-16 cap |

**Total model spend so far at the real price: about $15.07 recorded (up to $20.26 if both T-12 HTTP 502s were billed in full), not the ~$9.90 logged before.** It draws on the same $80 credit. A full T-12 benchmark at ~650k output tokens would be about $117 at the real price. Vishal chose Q-7 B (2026-11-24): pro only, at most 20 documents in total, hard cap $15 of model spend for T-12.

T-56 final: $3.35 of $12 (run bb8d moved the test to gpt-5-mini; test done, FAIL). Earlier note: $3.09 of $12 at the real price (Q-11 A; the cap is read as real dollars). Tuning cost $0.14-1.08 a sheet, mean $0.62, about twice the pre-registered cost mark of $0.316, so a 30-sheet test on gpt-5.4-pro would cost about $18.50 (range ~$14-22) and cannot fit the cap (Q-12, rewritten).

T-12 total so far: ~$11.97 recorded at the real price (≤$17.16 if the two 502s were billed in full, which would pass the $15 Q-7 B cap; logged as a hurdle) (old assumed figure ~$7.89); the 20-document call limit is used up, so T-12 makes no more model calls.

<!-- spend:auto:start -->
## Spend report (written daily by .github/workflows/azure-spend.yml)

- Updated: 2026-11-27T22:13:29Z. Covers resource group rg-ai-studio only; Cost Management data can lag by up to a day.
- Status: no_data: Azure returned no cost rows (new subscription, data lag, or an unsupported offer). Spend is unknown.
- Cost rows returned: month to date 0, since start 0, by resource 0
- Projected monthly cost from the table above: $23.20
- Last alert level: 0% (since 2026-11-01)
- Inventory: 1 resources in rg-ai-studio, 0 not in the table above

| Resource | Type | Cost this month | In the table above? |
|---|---|---|---|
| id-github-deploy | Microsoft.ManagedIdentity/userAssignedIdentities | - | yes |
<!-- spend:auto:end -->
