# Board

One line per task:
`- [status] T-<n> | <product, idea or studio> | <task> | claimed-by: <run id or -> @ <UTC> | updated: <UTC>`

Status is one of todo, doing, review, blocked, done. Move done items older than 7 days to `state/archive/`. New task ids continue from the highest one used.

## Tasks

- [blocked] T-1 | studio | First-run check: send Vishal a short hello with tg.py, pull, confirm the expected environment variables exist (names only), make one tiny Azure OpenAI call through the network secret, check whether the AZURE_CREDENTIALS Actions secret exists if the API allows it, and report results in DIGEST_NOTES.md and HURDLES.md | claimed-by: - | updated: 2026-11-23T11:13:00Z (blocked: Telegram and Azure OpenAI env vars not set; see HURDLES)
- [review] T-2 | studio | Build a GitHub Actions workflow that reports month-to-date Azure spend for rg-ai-studio daily, and use it to keep state/BUDGET.md current | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:15:44Z | updated: 2026-11-23T11:18:42Z (built: workflow + scripts/azure_spend.py + 11 tests; waiting for reviewer)
- [done] T-3 | ideas | Scout 15 candidate problems across markets: Vishal's four seed directions plus at least 11 others; one idea file each | claimed-by: - 26-11-23T11:24:06Z (15 G0 idea files; validator scoring in T-4)
- [doing] T-4 | ideas | Validate and score every G0 idea; write state/ideas/RANKING.md | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:23:02Z | updated: 2026-11-23T11:23:02Z
- [todo] T-5 | ideas | Take the top 2 ideas through G2 (spec, architecture, cost) | claimed-by: - | updated: -
- [review] T-6 | studio | Build products/_starter (see playbooks/engineering.md) and get reviewer and security PASS | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:19:07Z | updated: 2026-11-23T11:36:09Z (backend + frontend + CI built; 55 tests and e2e pass; needs reviewer + security PASS; deploy left, see products/_starter/NEXT.md)
