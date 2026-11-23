# Hurdles

One line per blocker:
`<UTC> | <run id> | what's blocked | what was tried | recommended fix | needs Vishal? (Q-id or no) | status`

2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Telegram: tg.py cannot send or pull | TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not set in the cloud environment; api.telegram.org is reachable | add both as environment variables on the `studio` environment (SETUP.md step 5), then start a new session | yes (setup) | open
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | Azure OpenAI test call | AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT and AZURE_OPENAI_API_KEY are not set; no network secret seen | finish SETUP.md steps 3 and 5 (env vars plus the api-key network secret) | yes (setup) | open
2026-11-23T11:13:00Z | 20261123T111240Z-run-b15e | State files cannot go straight to main from this session | this session may push only to branch vishal/blissful-cray-v1s3ys | merge that branch to main, and switch on unrestricted branch pushes for the scheduled tasks (SETUP.md step 6) | yes (setup) | open
2026-11-23T11:24:06Z | 20261123T111240Z-run-b15e | Scouts could not fetch a few hosts (cwv.yourstory.com, quickrams.pages.dev), and Capterra, G2 and some gov/vendor pages returned 403 | used search snippets and labelled them unverified in the idea files | make sure scheduled runs use the `studio` environment with Full network (SETUP.md step 5); 403s from review sites are normal, so validators should re-check key figures | no | open
