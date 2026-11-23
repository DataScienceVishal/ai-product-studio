# Decision log

Append only. One line per decision:
`<UTC> | <run id> | <decision> | why | reversible? | source (Q-id, Telegram update id, or gate)`
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Moved the kit from files/ai-product-studio/ to the repo root; removed duplicate files/CLAUDE.md, files/SETUP.md and .DS_Store | scheduled runs start at the root and expect CLAUDE.md and scripts/ there | yes | Vishal in chat
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Marked T-1 blocked and moved on to T-3 | Telegram and Azure OpenAI variables are not set yet; Vishal said to leave Telegram for now | yes | Vishal in chat
