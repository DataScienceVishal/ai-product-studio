# Products

One folder per product, created at G2 by the strategist and architect, copied from `_starter` once it exists.

    products/<slug>/
      SPEC.md            strategist
      ARCHITECTURE.md    architect
      ADR/               architecture decisions
      infra/             Azure resources (Bicep) and notes
      backend/  frontend/  tests/
      TESTPLAN.md  DOD.md  SECURITY.md  reviews/
      gtm/               competitors, landing copy, demo script, sales sheet, leads
      BRIEF.md           teacher (comprehension brief)
      README.md          run, deploy, roll back
      .env.example       variable names only, never values

CI/CD lives in `.github/workflows/<slug>-ci.yml` and `<slug>-deploy.yml`, path-filtered to `products/<slug>/**`. At handover a product is split into its own repository with its history.
