#!/usr/bin/env python3
"""Telegram helper for the studio. Standard library only.

Needs two environment variables (set them on the cloud environment, never in git):
  TELEGRAM_BOT_TOKEN   from @BotFather
  TELEGRAM_CHAT_ID     Vishal's own Telegram user id; messages from anyone else are dropped

Commands
  pull                                   save new messages to state/inbox/<update_id>.json
  send --text "..." | --file PATH [--buttons PATH] [--html]
                                         --html: Telegram HTML (<b>, <i>, <u>, <code>, <a href>);
                                         falls back to plain text if Telegram can't parse it
  whoami                                 check the token works (prints the bot's username)

Buttons file (JSON), one row of buttons per question:
  [{"qid": "Q-12", "options": ["A", "B", "C"], "recommended": "A",
    "labels": {"A": "Stripe", "B": "Razorpay", "C": "Both"}}]
"labels" is optional (short words, up to 24 characters); buttons then read "A · Stripe ⭐".
A tap arrives on the next pull as {"type": "button", "data": "q:Q-12:A"}.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "state" / "inbox"
OFFSET_FILE = ROOT / "state" / "tg_offset.txt"
API = "https://api.telegram.org/bot{token}/{method}"
MAX_CHARS = 4000  # Telegram's hard limit is 4096
QID = re.compile(r"^Q-\d+$")
LETTERS = ("A", "B", "C", "D")


def need(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"tg.py: {name} is not set. Add it to the cloud environment's variables (see SETUP.md).")
    return value


def iso(ts: float | int | None) -> str:
    moment = datetime.fromtimestamp(ts, timezone.utc) if ts else datetime.now(timezone.utc)
    return moment.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


class ParseError(Exception):
    """Telegram could not parse the message's HTML entities."""


def call(method: str, payload: dict | None = None, timeout: int = 30):
    """POST to the Bot API. Never prints the URL, because it contains the token."""
    url = API.format(token=need("TELEGRAM_BOT_TOKEN"), method=method)
    body = json.dumps(payload or {}).encode()
    for attempt in range(4):
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode())
            if not result.get("ok"):
                sys.exit(f"tg.py: Telegram refused {method}: {result.get('description', 'no reason given')}")
            return result["result"]
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            if error.code == 429 or error.code >= 500:
                wait = 2 ** attempt * 2
                try:
                    wait = int(json.loads(detail).get("parameters", {}).get("retry_after", wait))
                except (ValueError, AttributeError):
                    pass
                time.sleep(min(wait, 30))
                continue
            if error.code == 400 and "parse entities" in detail:
                raise ParseError(detail)
            sys.exit(f"tg.py: Telegram error {error.code} on {method}: {detail}")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if attempt == 3:
                reason = getattr(error, "reason", error)
                sys.exit(f"tg.py: network error on {method} ({reason}). "
                         "Is the cloud environment's network access set to Full?")
            time.sleep(2 ** attempt * 2)
    sys.exit(f"tg.py: gave up on {method} after retries")


def normalize(update: dict) -> dict | None:
    """Reduce a Telegram update to the fields the studio needs."""
    if "message" in update:
        message = update["message"]
        text = message.get("text") or message.get("caption") or ""
        if not text and any(k in message for k in ("photo", "document", "voice", "video", "audio", "sticker")):
            text = "[non-text message: tell Vishal the studio reads text only]"
        record = {
            "update_id": update["update_id"],
            "type": "message",
            "from_id": str((message.get("from") or {}).get("id", "")),
            "date": iso(message.get("date")),
            "text": text,
        }
        reply = message.get("reply_to_message")
        if reply:
            record["reply_to_text"] = (reply.get("text") or "")[:500]
        return record
    if "callback_query" in update:
        query = update["callback_query"]
        return {
            "update_id": update["update_id"],
            "type": "button",
            "from_id": str((query.get("from") or {}).get("id", "")),
            "date": iso(None),  # Telegram gives no press time; this is when we pulled it
            "data": query.get("data", ""),
            "question_text": ((query.get("message") or {}).get("text") or "")[:500],
            "callback_id": str(query.get("id", "")),
        }
    return None


def cmd_pull(args) -> None:
    chat_id = need("TELEGRAM_CHAT_ID")
    INBOX.mkdir(parents=True, exist_ok=True)
    offset = 0
    if OFFSET_FILE.exists() and OFFSET_FILE.read_text().strip():
        offset = int(OFFSET_FILE.read_text().strip())
    # Passing the pushed offset confirms only updates already saved in git.
    updates = call("getUpdates", {"offset": offset, "timeout": 0,
                                  "allowed_updates": ["message", "callback_query"]})
    saved = ignored = 0
    highest = offset - 1
    for update in updates:
        highest = max(highest, update["update_id"])
        record = normalize(update)
        if record is None or record["from_id"] != chat_id:
            ignored += 1
            continue
        if record["type"] == "button":
            acknowledge(record)
        path = INBOX / f"{record['update_id']}.json"
        if not path.exists():
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            saved += 1
    if updates:
        OFFSET_FILE.write_text(f"{highest + 1}\n")
    print(f"pulled {len(updates)} update(s): {saved} new from Vishal, {ignored} ignored.")
    if updates:
        print("Commit and push state/inbox/ and state/tg_offset.txt now, then handle the new files.")


def acknowledge(record: dict) -> None:
    """Stop the button's spinner and confirm the tap. Old taps can't be answered any more; that's fine."""
    if not record.get("callback_id"):
        return
    try:
        call("answerCallbackQuery", {"callback_query_id": record["callback_id"],
                                     "text": "✓ Got it. I'll apply it on the next run."}, timeout=10)
    except (SystemExit, ParseError):
        pass


def split(text: str) -> list[str]:
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > MAX_CHARS:  # a single very long line
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:MAX_CHARS])
            line = line[MAX_CHARS:]
        if len(current) + len(line) > MAX_CHARS:
            chunks.append(current)
            current = ""
        current += line
    if current.strip():
        chunks.append(current)
    return chunks


def load_buttons(path: str) -> dict:
    try:
        spec = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as error:
        sys.exit(f"tg.py: can't read buttons file: {error}")
    if not isinstance(spec, list) or not spec:
        sys.exit("tg.py: buttons file must be a non-empty JSON list")
    rows = []
    for item in spec:
        qid = str(item.get("qid", ""))
        options = [str(o).upper() for o in item.get("options", [])]
        recommended = str(item.get("recommended", "")).upper()
        if not QID.match(qid):
            sys.exit(f"tg.py: bad qid '{qid}' (expected Q-<number>)")
        if not 2 <= len(options) <= 4 or any(o not in LETTERS for o in options):
            sys.exit(f"tg.py: {qid} needs 2 to 4 options from A, B, C, D")
        if recommended not in options:
            sys.exit(f"tg.py: {qid} recommended option must be one of {options}")
        labels = item.get("labels") or {}
        if not isinstance(labels, dict):
            sys.exit(f"tg.py: {qid} labels must be an object like {{\"A\": \"Stripe\"}}")
        row = []
        for o in options:
            label = str(labels.get(o, "")).strip()[:24]
            text = f"{o} · {label}" if label else f"{qid} {o}"
            row.append({"text": text + (" ⭐" if o == recommended else ""), "callback_data": f"q:{qid}:{o}"})
        if labels and len(options) > 2:  # labelled buttons are wide: one per row
            rows.extend([button] for button in row)
        else:
            rows.append(row)
    return {"inline_keyboard": rows}


def looks_like_html(text: str) -> bool:
    """Digests written from the playbook template use <b>/<i>; send them as HTML even without --html."""
    return bool(re.search(r"</(b|i|u|code|a)>", text))


def strip_html(text: str) -> str:
    """Plain-text fallback: drop tags and unescape the three HTML entities Telegram uses."""
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def cmd_send(args) -> None:
    chat_id = need("TELEGRAM_CHAT_ID")
    if bool(args.text) == bool(args.file):
        sys.exit("tg.py: give exactly one of --text or --file")
    text = args.text if args.text else Path(args.file).read_text()
    if not text.strip():
        sys.exit("tg.py: nothing to send")
    markup = load_buttons(args.buttons) if args.buttons else None
    chunks = split(text)
    for index, chunk in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": chunk, "link_preview_options": {"is_disabled": True}}
        if args.html or looks_like_html(text):
            payload["parse_mode"] = "HTML"
        if markup and index == len(chunks) - 1:
            payload["reply_markup"] = markup
        try:
            call("sendMessage", payload)
        except ParseError:
            payload.pop("parse_mode")
            payload["text"] = strip_html(chunk)
            call("sendMessage", payload)
            print("tg.py: Telegram couldn't parse the HTML; sent this part as plain text.")
    print(f"sent {len(chunks)} message(s){' with buttons' if markup else ''}.")


def cmd_whoami(args) -> None:
    me = call("getMe")
    print(f"token works: bot @{me.get('username')} ({me.get('first_name')})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pull").set_defaults(func=cmd_pull)
    p = sub.add_parser("send")
    p.add_argument("--text")
    p.add_argument("--file")
    p.add_argument("--buttons", help="JSON file describing question buttons")
    p.add_argument("--html", action="store_true", help="send as Telegram HTML (falls back to plain text)")
    p.set_defaults(func=cmd_send)
    sub.add_parser("whoami").set_defaults(func=cmd_whoami)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
