#!/usr/bin/env python3
"""Studio housekeeping: run log, usage modes, selling lock and a status summary.

Standard library only. All times are UTC, written as 2026-11-23T10:07:00Z.

Commands
  run-start --kind run|desk      log the start of a run, print its run id
  mode [--now ISO]               apply mode transitions, print the current mode
  set-mode normal|paused|reserve [--at ISO]
  selling lock|unlock
  status                         one-screen summary for digests

How "leave some usage for me" works (mode = reserve)
  The studio keeps working at full speed until the current five-hour usage
  window ends. It knows the window ended when hourly Studio Runs stop arriving
  (a gap of more than GAP minutes means runs were refused at the limit), or
  when five hours have passed since the request, whichever comes first.
  From then it is LIGHT (inbox and digests only) for WINDOW hours, then NORMAL.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
RUNS = STATE / "runs"
MODE_FILE = STATE / "MODE.json"

WINDOW = timedelta(hours=5)       # length of a plan usage window
GAP = timedelta(minutes=100)      # hourly runs: a longer gap means runs were refused
KEEP_RUN_LOGS = timedelta(days=7)

DEFAULT_MODE = {
    "mode": "normal",
    "reserve_requested_at": None,
    "light_until": None,
    "selling": "locked",
    "updated_at": None,
}

RUN_FILE = re.compile(r"^(\d{8}T\d{6}Z)-(run|desk)-[0-9a-f]{4}\.txt$")


# ---------- time helpers ----------

def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def fmt(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for pattern in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise SystemExit(f"studio.py: can't read time '{value}'. Use UTC like 2026-11-23T10:07:00Z")


# ---------- state helpers ----------

def load_mode() -> dict:
    if MODE_FILE.exists():
        try:
            data = json.loads(MODE_FILE.read_text())
            return {**DEFAULT_MODE, **data}
        except json.JSONDecodeError:
            print("studio.py: MODE.json was unreadable; reset to normal.", file=sys.stderr)
    return dict(DEFAULT_MODE)


def save_mode(state: dict, now: datetime) -> None:
    state["updated_at"] = fmt(now)
    MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def run_times(kind: str = "run") -> list[datetime]:
    if not RUNS.exists():
        return []
    times = []
    for path in RUNS.iterdir():
        match = RUN_FILE.match(path.name)
        if match and match.group(2) == kind:
            times.append(parse(match.group(1)))
    return sorted(times)


# ---------- mode logic ----------

def evaluate(state: dict, now: datetime, runs: list[datetime]) -> tuple[dict, list[str]]:
    """Apply time-based transitions. Returns the new state and notes on what changed."""
    notes: list[str] = []
    state = dict(state)

    if state["mode"] == "reserve":
        requested = parse(state.get("reserve_requested_at")) or now
        before = [t for t in runs if t <= requested]
        after = [t for t in runs if t > requested]
        sequence = ([before[-1]] if before else []) + after
        light_start = None
        for earlier, later in zip(sequence, sequence[1:]):
            if later - earlier > GAP:
                light_start = later
                notes.append(f"usage window ended (no runs from {fmt(earlier)} to {fmt(later)})")
                break
        if light_start is None and now >= requested + WINDOW:
            light_start = now
            notes.append("five hours passed since the request; treating the window as ended")
        if light_start is not None:
            state["mode"] = "light"
            state["light_until"] = fmt(light_start + WINDOW)
            notes.append(f"LIGHT until {state['light_until']}")

    if state["mode"] == "light":
        until = parse(state.get("light_until"))
        if until is None or now >= until:
            state.update(mode="normal", light_until=None, reserve_requested_at=None)
            notes.append("reserve finished; back to NORMAL (say so in the next digest)")

    return state, notes


def describe(state: dict) -> str:
    mode = state["mode"]
    if mode == "normal":
        line = "NORMAL: full work"
    elif mode == "reserve":
        line = (f"RESERVE: full speed until the current usage window ends "
                f"(requested {state.get('reserve_requested_at')}), then LIGHT for five hours")
    elif mode == "light":
        line = f"LIGHT until {state.get('light_until')}: inbox and digests only, no build or research"
    elif mode == "paused":
        line = "PAUSED: inbox and digests only, until Vishal sends 'resume'"
    else:
        line = f"UNKNOWN mode '{mode}': treat as PAUSED and raise a hurdle"
    return f"{line} | selling: {state.get('selling', 'locked')}"


# ---------- commands ----------

def cmd_run_start(args) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    now = now_utc()
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{args.kind}-{secrets.token_hex(2)}"
    session = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID", "local")
    (RUNS / f"{run_id}.txt").write_text(f"kind={args.kind}\nstarted={fmt(now)}\nsession={session}\n")
    pruned = 0
    for path in RUNS.iterdir():
        match = RUN_FILE.match(path.name)
        if match and now - parse(match.group(1)) > KEEP_RUN_LOGS:
            path.unlink()
            pruned += 1
    print(run_id)
    print(f"logged state/runs/{run_id}.txt (pruned {pruned} old). Commit and push.", file=sys.stderr)


def cmd_mode(args) -> None:
    now = parse(args.now) if args.now else now_utc()
    state, notes = evaluate(load_mode(), now, run_times("run"))
    if notes:
        save_mode(state, now)
        for note in notes:
            print(f"note: {note}")
        print("MODE.json changed: commit and push it.")
    print(describe(state))


def cmd_set_mode(args) -> None:
    now = now_utc()
    state = load_mode()
    if args.mode == "reserve":
        at = parse(args.at) if args.at else now
        state.update(mode="reserve", reserve_requested_at=fmt(at), light_until=None)
    else:
        state.update(mode=args.mode, reserve_requested_at=None, light_until=None)
    save_mode(state, now)
    print(describe(state))
    print("MODE.json changed: commit and push it.")


def cmd_selling(args) -> None:
    now = now_utc()
    state = load_mode()
    state["selling"] = "unlocked" if args.action == "unlock" else "locked"
    save_mode(state, now)
    print(describe(state))
    print("Record this in state/DECISIONS.md, then commit and push.")


def count_board() -> dict[str, int]:
    counts = {k: 0 for k in ("todo", "doing", "review", "blocked", "done")}
    board = STATE / "BOARD.md"
    if board.exists():
        for line in board.read_text().splitlines():
            match = re.match(r"^- \[(todo|doing|review|blocked|done)\]", line.strip())
            if match:
                counts[match.group(1)] += 1
    return counts


def count_questions() -> dict[str, int]:
    counts: dict[str, int] = {}
    questions = STATE / "QUESTIONS.md"
    if questions.exists():
        for line in questions.read_text().splitlines():
            match = re.match(r"^## Q-\d+ \(status: (\w+)", line.strip())
            if match:
                counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return counts


def count_ideas() -> dict[str, int]:
    counts: dict[str, int] = {}
    ideas = STATE / "ideas"
    if ideas.exists():
        for path in ideas.glob("*.md"):
            if path.name.startswith("_") or path.name in ("RANKING.md", "README.md"):
                continue
            match = re.search(r"^- stage:\s*(G\d)", path.read_text(), flags=re.MULTILINE)
            stage = match.group(1) if match else "G?"
            counts[stage] = counts.get(stage, 0) + 1
        killed = ideas / "killed"
        if killed.exists():
            counts["killed"] = len([p for p in killed.glob("*.md")])
    return counts


def budget_line(now: datetime) -> str:
    """One line about the Azure spend report in state/BUDGET.md, flagging it when stale or unavailable."""
    path = STATE / "BUDGET.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block = re.search(r"^<!-- spend:auto:start -->[ \t]*$(.*?)^<!-- spend:auto:end -->[ \t]*$", text, re.M | re.S)
    text = block.group(1) if block else ""  # only the report's own block: hand-written lines can't fool it
    updated = re.search(r"^- Updated: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", text, re.M)
    if not updated:
        return "budget: no spend report yet (the azure-spend workflow needs Azure credentials)"
    status = re.search(r"^- Status: (.+)$", text, re.M)
    since = re.search(r"^- Since \S+: (.+)$", text, re.M)
    when = datetime.strptime(updated.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    hours = (now - when).total_seconds() / 3600
    state = status.group(1) if status else "unknown"
    parts = [f"budget: {since.group(1)}" if state == "ok" and since else f"budget: {state[:100]}"]
    parts.append(f"updated {hours:.0f}h ago" + (" (STALE: check the azure-spend workflow)" if hours > 30 else ""))
    return " · ".join(parts)


def cmd_status(args) -> None:
    now = now_utc()
    state, _ = evaluate(load_mode(), now, run_times("run"))
    runs = run_times("run")
    last24 = [t for t in runs if now - t <= timedelta(hours=24)]
    board = count_board()
    questions = count_questions()
    ideas = count_ideas()
    print(f"mode: {describe(state)}")
    print("board: " + " · ".join(f"{k} {v}" for k, v in board.items()))
    print("questions: " + (" · ".join(f"{k} {v}" for k, v in sorted(questions.items())) or "none"))
    print("ideas: " + (" · ".join(f"{k} {v}" for k, v in sorted(ideas.items())) or "none yet"))
    print(f"studio runs in last 24h: {len(last24)} · last: {fmt(runs[-1]) if runs else 'never'}")
    print(budget_line(now))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run-start")
    p.add_argument("--kind", choices=["run", "desk"], required=True)
    p.set_defaults(func=cmd_run_start)

    p = sub.add_parser("mode")
    p.add_argument("--now", help="override the current time (UTC), for testing")
    p.set_defaults(func=cmd_mode)

    p = sub.add_parser("set-mode")
    p.add_argument("mode", choices=["normal", "paused", "reserve"])
    p.add_argument("--at", help="when Vishal asked (UTC); use the Telegram message date")
    p.set_defaults(func=cmd_set_mode)

    p = sub.add_parser("selling")
    p.add_argument("action", choices=["lock", "unlock"])
    p.set_defaults(func=cmd_selling)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
