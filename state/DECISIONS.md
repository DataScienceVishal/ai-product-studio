# Decision log

Append only. One line per decision:
`<UTC> | <run id> | <decision> | why | reversible? | source (Q-id, Telegram update id, or gate)`
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Moved the kit from files/ai-product-studio/ to the repo root; removed duplicate files/CLAUDE.md, files/SETUP.md and .DS_Store | scheduled runs start at the root and expect CLAUDE.md and scripts/ there | yes | Vishal in chat
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Marked T-1 blocked and moved on to T-3 | Telegram and Azure OpenAI variables are not set yet; Vishal said to leave Telegram for now | yes | Vishal in chat
2026-11-23T11:18:42Z | 20261123T111240Z-run-b15e | T-2: spend report queries Cost Management directly (type Usage = actual cost, PreTaxCost) at rg-ai-studio scope; counts cumulative spend from 2026-11-01 against the $80 cap, not just month to date | the cap is total credit use, so month-to-date alone would hide it | yes | gate
2026-11-23T11:18:42Z | 20261123T111240Z-run-b15e | T-2: the workflow skips with a notice (not a red failure) while AZURE_CREDENTIALS is missing; Telegram alerts are optional Actions secrets | avoids a daily failing run before setup is finished | yes | gate
2026-11-23T11:36:09Z | 20261123T111240Z-run-b15e | Starter uses opaque hashed session cookies (not JWT), a custom-header CSRF check, argon2id, and shared tables with tenant_id plus a scoped query helper | server-side revocation, simplest safe defaults; full reasons in products/_starter/ADR/0001 | yes | T-6
2026-11-23T11:36:09Z | 20261123T111240Z-run-b15e | Starter deploy (Bicep + Container Apps) deferred to the architect, with cost estimates in BUDGET.md before anything is created | no Azure credentials yet, and the registry and Postgres choice costs money | yes | T-6
2026-11-23T11:36:09Z | 20261123T111240Z-run-b15e | Product code is on vishal/blissful-cray-v1s3ys instead of p/_starter/T-6 | this session may push only to that branch | yes | session limits
2026-11-23T11:37:58Z | 20261123T111240Z-run-b15e | Added T-7 (starter deploy design) and T-8 (starter gaps), and queued Q-1 about merging this branch to main | found while building T-6; scheduled runs start from main | yes | T-6
