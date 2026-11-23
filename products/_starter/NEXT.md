# NEXT: product starter (T-6)

Last updated 2026-11-23 by run 20261123T111240Z-run-b15e.

## Done and verified

- Backend: FastAPI, SQLAlchemy 2 with Alembic migration 0001, argon2id passwords, hashed opaque sessions,
  CSRF header check, password reset (single use, 30 minutes, revokes sessions), tenant-scoped example resource,
  AI adapter (fake and Azure OpenAI v1) with retries and a monthly cap per plan, billing adapter (mock and
  Stripe test mode only) with signed, idempotent webhooks, data export and account deletion, JSON logs with
  request and tenant ids, security headers including noindex, health check, rate limits.
- 56 backend tests pass against Postgres 16. A mutation check showed the tenancy test fails when the tenant
  filter is removed.
- Frontend: React 19, TypeScript, Vite 8, Tailwind 4. Type check clean, build about 74 kB gzipped.
- The browser end-to-end test (`scripts/e2e.sh`) passes: sign-up, sample data, AI summary, checkout with
  EARLY50, sign out and in, delete account.
- CI: `.github/workflows/_starter-ci.yml`. Not yet seen running on GitHub.

## Left to do

1. **Gates:** reviewer and security PASS (required before any product copies the starter).
2. **Deploy:** an Azure Container Apps deploy workflow and Bicep. Architect first: decide the registry
   (GHCR vs ACR Basic, about $5 a month) and the Postgres choice (Flexible Server B1ms vs a container), write
   the monthly estimates in `state/BUDGET.md`, and ask Vishal if one resource passes $10 a month. Needs
   `AZURE_CREDENTIALS`, which isn't set yet (see HURDLES).
3. **Gaps to close before G4 products:** invitations and member roles; email verification; Redis-backed rate
   limits for more than one replica; a frontend unit test setup. (uvicorn's startup lines now go
   through the JSON logger too.)
4. **Watch:** Starlette warns that its test client prefers `httpx2`. Installing it was blocked (unverified
   package), so we stay on httpx. Revisit only if Starlette's docs confirm it.

## How to verify

```bash
cd products/_starter/backend && .venv/bin/python -m pytest -q
cd products/_starter && ./scripts/e2e.sh
```
