# Handoff from session "Telegram bot setup" (2026-11-23, run 20261123T111240Z-run-b15e)

The previous session ran in the wrong environment ("Default"). This file brings a new session in the "Cloud" environment up to date. Everything else is in the repo: CLAUDE.md, state/ and git log.

## Standing instructions from Vishal (in chat)
- "You are meant to never stop": keep working the board and the Always-On list; never idle while agents run.
- "Always commit everything and push to main whenever you push." Keep main the single source of truth.
- Guard added after a red-CI slip: before any push that touches product code, run the full test suite on that exact tree and push only on exit 0.
- Never paste or print secrets. The selling lock is on. Ask first for anything on the CLAUDE.md section 6 list.

## Where things stand (main at handoff)
- Product starter (T-6, T-8, T-21, T-16): done. Code review and security gates passed. One image serves the SPA and API. 180 backend tests; CI green, including the image build and e2e.
- Azure deploy design (T-7, T-20, T-26): done. Bicep compiles in CI with a cost guard. Nothing is created until Q-5 and STUDIO_AZURE_APPROVED=yes.
- Spend report (T-2): built and reviewed; waits for an Azure Actions secret and one manual run.
- Ideas: 32 scored, 0 PASS, 3 killed. The top ideas (pEPR 68, restaurant 66, MTD 65, holiday-pay 63) are parked, with reasons in state/ideas/RANKING.md. Scouting lessons are at the end of RANKING.md.
- Scheduled tasks exist: a Desk run fired at 22:19 UTC. Telegram credentials are set, but api.telegram.org was blocked by network policy (HURDLES). The unsent digest is in state/runs/20261123T221941Z-desk-bf43-digest.txt.

## First things for the new session
1. Run the CLAUDE.md section 3 loop from step 1 (sync, then `python3 scripts/studio.py run-start --kind run`).
2. T-1: check that the Telegram and Azure OpenAI variables exist (names only), then `python3 scripts/tg.py send` a short hello. If Telegram works, tell Vishal, and close or update the HURDLES Telegram lines.
3. Then the board: open todo items include T-29 (T-16 minors), T-19 (digest and SHA pins), T-15 (starter follow-ups) and T-17/T-18 (managed identity, passwordless Postgres). Idea work mostly waits on Q-4 (the friend's sector).

## Pending on Vishal
Telegram network access (if still blocked); "Allow unrestricted branch pushes" for the scheduled tasks; Q-4; Azure OpenAI variables and the api-key network secret (SETUP.md steps 3 and 5); the Azure spend secret; Q-5; optionally, whether his GitHub account has Pro (main-only deploy environment).
