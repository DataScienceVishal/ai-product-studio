# Engineering standards

## Default stack (change only with an ADR)

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 with Alembic migrations, Pydantic v2.
- **Frontend:** React with TypeScript (Vite) and Tailwind. Mobile-friendly and accessible: labels, contrast, keyboard navigation.
- **Database:** Postgres. Use one shared small Azure Postgres server for all products, one database each, unless an ADR says otherwise.
- **AI:** Azure OpenAI through Vishal's deployment (`AZURE_OPENAI_DEPLOYMENT`, gpt-5-mini by default), behind a provider interface so models can be swapped. Log token use per customer. Check the current Azure docs for client setup and API version.
- **Hosting:** Azure, with Container Apps preferred because it scales to zero. Demos use the default Azure URL; at G4 a `vishalkhan.me` subdomain needs Vishal to add a DNS record, so ask once the product is ready.
- **CI/CD:** GitHub Actions per product, `.github/workflows/<slug>-ci.yml` and `<slug>-deploy.yml`, path-filtered to `products/<slug>/**`. Private repos get limited free Actions minutes, so cache dependencies and run end-to-end tests on merges to main rather than every push.

## Repository layout

Everything lives in this one repo, because a cloud run can only reach the repositories attached to it. See `products/README.md` for the folder layout. At handover a product is split into its own repo with its history (`git subtree split`).

## Credentials and deploys

- Cloud runs never hold Azure management credentials. Infrastructure changes and deploys run in GitHub Actions signing in to Azure by OIDC as the managed identity `id-github-deploy` (secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`; Contributor on `rg-ai-studio` only; the federated credential trusts `main` only, so never add `environment:` to a job that signs in). The daily spend report signs in as the separate read-only identity `id-github-spend` (Reader + Cost Management Reader on the group; secret `AZURE_SPEND_CLIENT_ID`) when configured, so it never needs deploy rights. Merging to main deploys; you can also trigger a workflow with `gh workflow run`, then read the result with `gh run list` and `gh run view --log`.
- `gh pr` and `gh issue` don't work in cloud runs (they use GraphQL). Use `gh api repos/<owner>/<repo>/...` for anything else.
- Azure OpenAI is reachable from runs through the cloud environment's network secret, which adds the key to requests for your endpoint's host. Set the SDK's key to the placeholder in `AZURE_OPENAI_API_KEY`; never try to read the real key. If calls return 401, log a hurdle.
- If deploy credentials are missing, keep building and testing inside the run (Postgres and Redis are preinstalled) and raise a hurdle.

## Working rules

- One branch per task, `p/<slug>/<task-id>`, with small commits. Merge to main only after reviewer PASS and green tests. State files under `state/` go straight to main.
- Tests come with the code. Every bug fix adds a regression test.
- Every external call has a timeout, retries with backoff and a clear error.
- Update README and ADRs in the same change as the code they describe.
- Watch AI cost: cache results where safe and enforce per-customer usage caps.

## Shared starter (board task T-6)

`products/_starter` is a template every product copies: FastAPI and React with sign-in, tenant isolation, billing adapter (mock plus Stripe test mode), structured logging, health check, tests, CI and an Azure deploy workflow. It needs reviewer and security PASS before any product starts from it. Improvements found while building a product flow back into the starter.
