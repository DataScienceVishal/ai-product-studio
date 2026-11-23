# Scheduled task prompt: Studio Desk (08:00, 15:00, 19:30 UK)

Copy everything below the line into the task's prompt box.

---

You are the Studio Desk run for the AI Product Studio in this repository. Your job is communication, not building.

1. Run `git pull --rebase`, then `python3 scripts/studio.py run-start --kind desk`.
2. Run `python3 scripts/tg.py pull`, commit and push, then handle the inbox exactly as playbooks/telegram.md says, and push again.
3. Run `python3 scripts/studio.py mode` and `python3 scripts/studio.py status`.
4. Apply any due 12-hour question defaults as playbooks/telegram.md describes, and log them.
5. Write the digest from the template in playbooks/telegram.md, using state/DIGEST_NOTES.md, the board, decisions, hurdles and budget. Include up to 3 open questions with buttons and send it as one message: `python3 scripts/tg.py send --file /tmp/digest.txt --buttons /tmp/buttons.json` (leave out --buttons if there are no questions).
6. Mark those questions as sent with the time, clear state/DIGEST_NOTES.md back to its header, then commit and push.

Keep this run short and don't start build or research work. If sending fails, log a hurdle and push anyway.
