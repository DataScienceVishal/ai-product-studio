# Definition of done: Sellable (G4)

A product is Sellable only when every line below is PASS, with evidence linked in `products/<slug>/DOD.md`.

## 1. Works for real
- Deployed on Azure at a stable URL. Private demo until approved: noindex, not linked anywhere.
- Sign-up and sign-in with strong password hashing (argon2 or bcrypt), expiring sessions, and a password reset path.
- Real data flowing end to end: a new user completes the core job with their own data in under 10 minutes.
- Tenant isolation: one customer can never see another's data, proven by a test.
- A demo account with realistic sample data.

## 2. Payments in test mode
- Subscription plans, a free trial and an early-customer offer, behind a payment adapter.
- Stripe test mode once test keys exist (from the business owner's Stripe account, added by Vishal as a network secret). Until then, a mock adapter with contract tests.
- Never live mode before `unlock selling`.

## 3. Reliability
- Every external call (AI, database, payments) has a timeout, retries and a friendly error.
- Structured logs with request ids. No secrets or personal data in logs.
- Tests: unit tests for business logic, API tests, and at least one end-to-end test of the core flow, all green in CI.
- Health check endpoint, basic rate limiting, and a per-customer AI usage cap.

## 4. Security and privacy
- Security PASS on every section of the security agent's checklist.
- Data inventory, retention rules and a delete-my-data path.
- Privacy policy and terms drafts, marked DRAFT and not legal advice.

## 5. Onboarding
- First-run onboarding: helpful empty states, an optional sample-data start, and a guided first task.
- A help page or FAQ.

## 6. Go-to-market kit
- Landing page with problem, demo visuals, pricing (trial and early-customer offer) and FAQ, private until approved.
- Five-minute demo script and a one-page sales sheet for the business owner.
- Competitor table with sources.

## 7. Comprehension brief
- `products/<slug>/BRIEF.md` by the teacher agent, following `comprehension-brief.md`, so Vishal can demo the product and answer buyers' questions.

## 8. Handover pack (needed for G5)
- README with an architecture diagram, a runbook (deploy, roll back, rotate keys), a cost sheet and known limitations.
- A plan to move hosting to the business's own Azure subscription. Azure for Students credit ending switches the subscription off, so no paying customer may depend on it.
