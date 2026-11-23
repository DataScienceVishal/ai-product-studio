# T-17 status

Done: `ManagedIdentityToken` and auth mode in `backend/app/ai.py`, settings `AZURE_OPENAI_AUTH` and
`AZURE_CLIENT_ID`, tests in `backend/tests/test_ai.py`, ADR 0002 decision 7, README.

Left (needs Vishal, ask-first): attach an identity to the app, grant "Cognitive Services OpenAI User" on the
OpenAI resource, set the two settings. No Bicep changed: the infra has only the shared pull identity
(`lifecycle: None`), so there is nothing to scope a role to yet.

Verify: `cd backend && TEST_DATABASE_URL=... .venv/bin/python -m pytest`.
