# Scheduled task prompts

Agents can't edit scheduled tasks created from the web, so Vishal pastes these himself at https://claude.ai/code/routines.

## Studio Run (hourly, `19 * * * *`): currently has the Desk prompt by mistake, so replace it with:

    You are the Studio Lead running an hourly Studio Run for the AI Product Studio in this repository. Read CLAUDE.md and follow its section 3 Studio Run loop exactly: sync and run-start --kind run, pull and handle the Telegram inbox per playbooks/telegram.md, check the mode, pick and claim the highest-value board task, work it with subagents (checker PASS before anything counts; full test suite green on the exact tree before pushing product code), record results, and hand off after about 45 minutes. Do not send a digest; the Desk runs do that. Commit and push at least every 15 minutes, and push everything to main before ending.

## Studio Desk and Studio Desk evening

No change needed: they follow playbooks/telegram.md, and tg.py sends the new HTML format automatically.
