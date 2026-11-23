# Decision log

Append only. One line per decision:
`<UTC> | <run id> | <decision> | why | reversible? | source (Q-id, Telegram update id, or gate)`
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Moved the kit from files/ai-product-studio/ to the repo root; removed duplicate files/CLAUDE.md, files/SETUP.md and .DS_Store | scheduled runs start at the root and expect CLAUDE.md and scripts/ there | yes | Vishal in chat
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Marked T-1 blocked and moved on to T-3 | Telegram and Azure OpenAI variables are not set yet; Vishal said to leave Telegram for now | yes | Vishal in chat
2026-11-23T11:18:42Z | 20261123T111240Z-run-b15e | T-2: spend report queries Cost Management directly (type Usage = actual cost, PreTaxCost) at rg-ai-studio scope; counts cumulative spend from 2026-11-01 against the $80 cap, not just month to date | the cap is total credit use, so month-to-date alone would hide it | yes | gate
2026-11-23T11:18:42Z | 20261123T111240Z-run-b15e | T-2: the workflow skips with a notice (not a red failure) while AZURE_CREDENTIALS is missing; Telegram alerts are optional Actions secrets | avoids a daily failing run before setup is finished | yes | gate
