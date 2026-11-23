# Telegram protocol

`scripts/tg.py` talks to the Telegram Bot API using only the Python standard library. It needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the environment and accepts messages only from that chat id; everything else is dropped.

## Pull and handle (every Studio Run and Desk run)

1. `python3 scripts/tg.py pull` saves each new update as `state/inbox/<update_id>.json` and moves `state/tg_offset.txt` forward. Commit and push both straight away. Telegram only forgets an update after a later pull sends the pushed offset, so a run that dies before pushing loses nothing.
2. For each inbox file whose update id isn't in `state/inbox/HANDLED.md`:
   - **Button press** (`"type": "button"`, data `q:<QID>:<letter>`): apply that option to the question in `state/QUESTIONS.md`, mark it answered, and log the decision in `state/DECISIONS.md`.
   - **Command** (the whole message, any capitalisation): see the table below.
   - **Reply to a question**: `reply_to_text` contains a `Q-` id, the message names one, or it is a short answer like `1A` / `2 c` (match the number to the latest digest's numbering in QUESTIONS.md). Treat it as the answer.
   - **Anything else**: an instruction or information from Vishal. Turn it into board tasks or decisions. If it's ambiguous, act on the most sensible reading and say what you assumed in the next digest.
3. Add `<update_id> | <what you did> | <run id>` to `state/inbox/HANDLED.md` in the same commit as the action. If the push is rejected, pull, re-check HANDLED.md, and never repeat an action another run already took.

## Commands

| Message | Do |
|---|---|
| `leave some usage for me` | `python3 scripts/studio.py set-mode reserve --at <the message's date>` |
| `pause` | `python3 scripts/studio.py set-mode paused` |
| `resume` | `python3 scripts/studio.py set-mode normal` |
| `status` | send the status reply (below) now with `tg.py send --html --text` |
| `unlock selling` | send a Yes/No button question; on Yes run `python3 scripts/studio.py selling unlock` |
| `lock selling` | `python3 scripts/studio.py selling lock` |

## Questions

Write each question in `state/QUESTIONS.md` using the format there: one decision, 2 to 4 options lettered A to D, the recommended option, and the default. Reversible questions take the recommendation 12 hours after being sent; ask-first questions wait. The Desk applies due defaults, marks them `defaulted`, and logs them in DECISIONS.md.

## Digest (Desk run at 08:00, 15:00 and 19:30 UK)

**One digest per slot.** Before writing one, look at the newest `state/runs/*-digest.txt`. If it is less than 3 hours old, this run is not a digest slot (for example an hourly run started with the Desk prompt): pull and handle the inbox, send nothing, and push.

Vishal reads these on his phone. Make them short, calm and easy to scan: **12 to 18 lines**, sent with `--html`.

Writing rules:
- Plain words. No gate codes (G0-G5), task ids (T-12), run ids, scores out of 100 or file paths. Say "the starter app", not "_starter"; "idea ranked 2nd", not "66/100".
- One idea per line, 12 words or fewer. Lead with the result, not the activity.
- Bold section titles with one emoji each. Leave out any section with nothing in it (no "none" lines).
- At most 4 wins, 2 questions, 1 problem, 2 next steps. Everything else waits for the next digest or `status`.
- Escape `&`, `<` and `>` in any text that is not a tag (`&amp;`, `&lt;`, `&gt;`).

Template:

    🧪 <b>Studio update</b> · Mon 23 Nov, 15:00
    🟢 Running normally · 🔒 Selling locked · 💷 Azure $0 of $80

    <b>✨ What's new</b>
    • Starter app finished: passed code and security review
    • 32 ideas checked; none strong enough yet

    <b>🙋 Need your call</b>
    <b>1. Which customers should we aim at next?</b>
    A Friend's sector ⭐ · B Finance network · C Keep broad
    <i>No reply → C at 10:40.</i>

    Tap a button, or just reply <b>1A</b>.

    <b>⚠️ One problem</b>
    • AI keys not set up yet, so tests on real documents wait

    <b>🧭 Next</b>
    • Polishing the starter app (tests, safer builds)

Questions: number them 1, 2 in the text and list the options in one short line, so a text reply works even if buttons don't. When you send, write in QUESTIONS.md which number each question had in that digest (`sent: <time> as 1`); a reply like `1A`, `1 a` or `2: C` then answers it (use the latest digest's numbering). Give every question `labels` so buttons read "A · Friend's sector ⭐" (up to 24 characters each). The question id stays in the button data only.

    [{"qid": "Q-4", "options": ["A", "B", "C"], "recommended": "A",
      "labels": {"A": "Friend's sector", "B": "Finance network", "C": "Keep broad"}}]

Send with: `python3 scripts/tg.py send --html --file /tmp/digest.txt --buttons /tmp/buttons.json`

Answers applied, decisions taken and the pipeline go in a "📌 Also" section of at most 2 lines, only when Vishal needs to know.

In LIGHT or PAUSED mode, still send the digest, shorter, with the first line saying the mode and how to change it ("⏸ Paused · send resume to restart").

## Status reply

At most 6 lines, same style, sent with `--html`: a bold title line, then what is running now, the last win, and anything waiting on him.

## Urgent pings (between digests)

Only when all useful work is blocked, a secret may be exposed, or money is at risk. One short message: what happened, what you did, what you recommend.
