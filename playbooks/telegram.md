# Telegram protocol

`scripts/tg.py` talks to the Telegram Bot API using only the Python standard library. It needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the environment and accepts messages only from that chat id; everything else is dropped.

## Pull and handle (every Studio Run and Desk run)

1. `python3 scripts/tg.py pull` saves each new update as `state/inbox/<update_id>.json` and moves `state/tg_offset.txt` forward. Commit and push both straight away. Telegram only forgets an update after a later pull sends the pushed offset, so a run that dies before pushing loses nothing.
2. For each inbox file whose update id isn't in `state/inbox/HANDLED.md`:
   - **Button press** (`"type": "button"`, data `q:<QID>:<letter>`): apply that option to the question in `state/QUESTIONS.md`, mark it answered, and log the decision in `state/DECISIONS.md`.
   - **Command** (the whole message, any capitalisation): see the table below.
   - **Reply to a question** (`reply_to_text` contains a `Q-` id) or a message naming one: treat it as the answer.
   - **Anything else**: an instruction or information from Vishal. Turn it into board tasks or decisions. If it's ambiguous, act on the most sensible reading and say what you assumed in the next digest.
3. Add `<update_id> | <what you did> | <run id>` to `state/inbox/HANDLED.md` in the same commit as the action. If the push is rejected, pull, re-check HANDLED.md, and never repeat an action another run already took.

## Commands

| Message | Do |
|---|---|
| `leave some usage for me` | `python3 scripts/studio.py set-mode reserve --at <the message's date>` |
| `pause` | `python3 scripts/studio.py set-mode paused` |
| `resume` | `python3 scripts/studio.py set-mode normal` |
| `status` | send at most 8 lines now with `tg.py send --text` |
| `unlock selling` | send a Yes/No button question; on Yes run `python3 scripts/studio.py selling unlock` |
| `lock selling` | `python3 scripts/studio.py selling lock` |

## Questions

Write each question in `state/QUESTIONS.md` using the format there: one decision, 2 to 4 options lettered A to D, the recommended option, and the default. Reversible questions take the recommendation 12 hours after being sent; ask-first questions wait. The Desk applies due defaults, marks them `defaulted`, and logs them in DECISIONS.md.

## Digest (Desk run at 08:00, 15:00 and 19:30 UK)

One message, about 30 lines at most, plain text:

    🧪 Studio digest · Mon 23 Nov, 15:00
    Mode NORMAL · selling locked · Azure $12 of $80

    Done since last digest
    • 3 to 6 lines, most important first, product slug in brackets

    Pipeline
    • G4 none · G3 restaurant-ops (core flow 70%) · G2 ai-receptionist · queue 4

    I decided (reversible; reply if you disagree)
    • up to 3

    Needs you
    Q-12 Which payment provider for test mode?
      A) Stripe ⭐  B) Razorpay  C) both
      No answer: A at 03:00

    Answers applied
    • Q-11 → B (restaurant-ops uses WhatsApp-style chat UI)

    Hurdles
    • up to 2, each with the fix I recommend

    Next
    • 2 or 3 lines

Buttons for up to 3 questions ride on the same message. Write them as JSON:

    [{"qid": "Q-12", "options": ["A", "B", "C"], "recommended": "A"}]

Send with: `python3 scripts/tg.py send --file /tmp/digest.txt --buttons /tmp/buttons.json`

In LIGHT or PAUSED mode, still send the digest, shorter, starting with the mode and how to change it.

## Urgent pings (between digests)

Only when all useful work is blocked, a secret may be exposed, or money is at risk. One short message: what happened, what you did, what you recommend.
