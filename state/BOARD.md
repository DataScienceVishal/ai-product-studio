# Board

One line per task:
`- [status] T-<n> | <product, idea or studio> | <task> | claimed-by: <run id or -> @ <UTC> | updated: <UTC>`

Status is one of todo, doing, review, blocked, done. Move done items older than 7 days to `state/archive/`. New task ids continue from the highest one used.

## Tasks

- [blocked] T-1 | studio | First-run check: send Vishal a short hello with tg.py, pull, confirm the expected environment variables exist (names only), make one tiny Azure OpenAI call through the network secret, check whether the AZURE_CREDENTIALS Actions secret exists if the API allows it, and report results in DIGEST_NOTES.md and HURDLES.md | claimed-by: - | updated: 2026-11-23T11:13:00Z (blocked: Telegram and Azure OpenAI env vars not set; see HURDLES)
- [review] T-2 | studio | Build a GitHub Actions workflow that reports month-to-date Azure spend for rg-ai-studio daily, and use it to keep state/BUDGET.md current | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:15:44Z | updated: 2026-11-23T11:46:56Z (review CHANGES fixed: 25 tests; waiting for re-review; done only after a real run writes real figures)
- [done] T-3 | ideas | Scout 15 candidate problems across markets: Vishal's four seed directions plus at least 11 others; one idea file each | claimed-by: - 26-11-23T11:24:06Z (15 G0 idea files; validator scoring in T-4)
- [doing] T-4 | ideas | Validate and score every G0 idea; write state/ideas/RANKING.md | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:23:02Z | updated: 2026-11-23T11:23:02Z
- [blocked] T-5 | ideas | Take the top 2 ideas through G2 (spec, architecture, cost) | claimed-by: - | updated: 2026-11-23T11:52:45Z (blocked: no idea has passed G1 yet; T-9 and T-10 gather the evidence that could change that)
- [review] T-6 | studio | Build products/_starter (see playbooks/engineering.md) and get reviewer and security PASS | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:19:07Z | updated: 2026-11-23T11:36:09Z (backend + frontend + CI built; 55 tests and e2e pass; needs reviewer + security PASS; deploy left, see products/_starter/NEXT.md)
- [todo] T-7 | studio | Starter deploy path: architect designs Azure Container Apps + Bicep for products/_starter (registry: GHCR vs ACR Basic; Postgres: Flexible Server B1ms vs container), writes monthly estimates to BUDGET.md, then builder writes .github/workflows/_starter-deploy.yml (manual dispatch until AZURE_CREDENTIALS exists) | claimed-by: - | updated: 2026-11-23T11:37:58Z
- [doing] T-8 | studio | Starter gaps before any product reaches G4: invitations and member roles, email verification, Redis-backed rate limits, frontend unit tests (see products/_starter/NEXT.md) | claimed-by: 20261123T111240Z-run-b15e @ 2026-11-23T11:38:18Z | updated: 2026-11-23T11:38:18Z (starting with invitations and member roles)
- [todo] T-9 | restaurant-margin-copilot | Evidence pass for the G1 re-score, per the validator's notes in the idea file: check Jelly, Profito and KitchenIQ on their own product and pricing pages, evidence on UK independents' price sensitivity and multi-supplier buying, then re-score with the validator | claimed-by: - | updated: 2026-11-23T11:52:45Z
- [todo] T-10 | mtd-quarterly-prep | Evidence pass for the G1 re-score, per the validator's notes: confirm or kill the remaining gap against Dext, AutoEntry and Xero public help docs, test the add-on-to-Dext/Xero framing, verify the Wolters Kluwer 59% figure, find published prices for outsourced MTD bookkeeping; then re-score | claimed-by: - | updated: 2026-11-23T11:52:45Z
- [todo] T-11 | ideas | Scout round 2: 10 UK ideas, each with a forcing function (a regulation or deadline that makes buyers act), a competitor gap checked on the competitor's own pages, and a demo possible on public or synthetic data. Lean on Vishal's finance, tax and data-engineering edges | claimed-by: - | updated: 2026-11-23T11:52:45Z

