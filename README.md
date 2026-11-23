# AI Product Studio

A team of Claude Code agents that finds, validates and builds sellable AI products. It runs on a schedule in the cloud, keeps its memory in this repo, and reports to you on Telegram.

## How it works

```
  Studio Run (every hour, Opus)            Studio Desk (08:00 · 15:00 · 19:30)
  Studio Lead + 10 specialist agents       digest + tap-to-answer questions
                 \                                  /
                  ▼                                ▼
        ┌──────────────────────────────────────────────────┐
        │  this repo = the studio's memory                  │
        │  CLAUDE.md · state/ (board, decisions, inbox)     │
        │  products/ (the code)                             │
        └──────────────────────────────────────────────────┘
                  │                                │
         GitHub Actions deploys              scripts/tg.py
                  ▼                                ▼
      Azure rg-ai-studio (≤ $80)            Telegram ⇄ you
```

- **Studio Run** reads the board, picks the most valuable task, hands it to the right specialists, has a different agent check the result, and pushes everything.
- **Studio Desk** sends your three daily digests: what happened, what it decided, and questions with buttons (recommended option marked ⭐).
- **Usage limits:** when a limit is hit, runs are refused until the reset, and the next run picks up from the repo. Nothing to do on your side.
- **Nothing is sold or sent to anyone** until you message `unlock selling`.

## What's where

| Path | What |
|---|---|
| `CLAUDE.md` | the studio's constitution: the improved prompt every run follows |
| `.claude/agents/` | the 10 specialists, 4 of them checkers (validator, reviewer, qa, security) |
| `playbooks/` | detailed rules: pipeline, sellable bar, Telegram, safety, engineering, briefs |
| `prompts/` | the two prompts you paste into the scheduled tasks |
| `scripts/` | `tg.py` (Telegram) and `studio.py` (modes, run log, status) |
| `state/` | board, decisions, questions, hurdles, budget, ideas, inbox |
| `products/` | the products themselves |

## Telegram commands

| Send | What happens |
|---|---|
| `leave some usage for me` | full speed until the current five-hour window ends, then light mode (messages and digests only) for five hours |
| `pause` / `resume` | stop and restart work; messages and digests continue |
| `status` | a short update within the hour |
| `unlock selling` / `lock selling` | allow or block outreach, live payments and public launch |
| anything else | an instruction, acted on and confirmed in the next digest |

Answer a question by tapping a button, or by replying to the question message.

## Stopping everything

`pause` keeps usage small but not zero, because runs still check messages. To stop all usage, switch both tasks off at claude.ai/code/routines, which works from your phone.

## Changing how it behaves

Edit `CLAUDE.md` or a playbook and push, or tell it on Telegram. The next run follows the change.

## Getting started

Follow `SETUP.md`.
