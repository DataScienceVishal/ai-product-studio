#!/usr/bin/env python3
"""Azure spend report for rg-ai-studio. Standard library plus the Azure CLI for sign-in.

Runs daily in .github/workflows/azure-spend.yml, after azure/login has signed in with
the AZURE_CREDENTIALS secret. It asks Azure Cost Management for the resource group's
actual cost and rewrites the auto section of state/BUDGET.md.

Commands
  report [--from-dir DIR] [--save-dir DIR]
      fetch costs (or read saved responses from DIR) and update state/BUDGET.md.
      Prints ALERT <level> when cumulative spend first crosses 50%, 75% or 95% of the cap,
      and UNLISTED <name> for each resource that cost money but is missing from the table.

Environment (all optional)
  AZURE_SUBSCRIPTION_ID   defaults to `az account show`
  STUDIO_RESOURCE_GROUP   defaults to rg-ai-studio
  STUDIO_SPEND_SINCE      first day counted against the cap, YYYY-MM-DD (default 2026-11-01)
  STUDIO_SPEND_CAP        cap in USD (default 80)

Cost Management data can lag by up to a day, so the figures are a floor, not a live meter.
The access token is never printed or written to disk.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGET = ROOT / "state" / "BUDGET.md"
API_VERSION = "2026-06-01"  # Cost Management Query - Usage, checked 2026-11-23
START = "<!-- spend:auto:start -->"
END = "<!-- spend:auto:end -->"
LEVELS = (50, 75, 95)
QUERIES = ("month_to_date", "since_start", "by_resource")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def settings() -> dict:
    since = os.environ.get("STUDIO_SPEND_SINCE", "2026-11-01").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        sys.exit(f"azure_spend: STUDIO_SPEND_SINCE must be YYYY-MM-DD, got '{since}'")
    try:
        cap = float(os.environ.get("STUDIO_SPEND_CAP", "80"))
    except ValueError:
        sys.exit("azure_spend: STUDIO_SPEND_CAP must be a number")
    return {
        "group": os.environ.get("STUDIO_RESOURCE_GROUP", "rg-ai-studio").strip(),
        "since": since,
        "cap": cap,
    }


def bodies(since: str, today: str) -> dict:
    """Request bodies, in the shape the Cost Management docs use (type Usage = actual cost)."""
    total = {"totalCost": {"name": "PreTaxCost", "function": "Sum"}}
    return {
        "month_to_date": {"type": "Usage", "timeframe": "MonthToDate",
                          "dataset": {"granularity": "None", "aggregation": total}},
        "since_start": {"type": "Usage", "timeframe": "Custom",
                        "timePeriod": {"from": f"{since}T00:00:00Z", "to": f"{today}T23:59:59Z"},
                        "dataset": {"granularity": "None", "aggregation": total}},
        "by_resource": {"type": "Usage", "timeframe": "MonthToDate",
                        "dataset": {"granularity": "None", "aggregation": total,
                                    "grouping": [{"type": "Dimension", "name": "ResourceId"}]}},
    }


def az(*args: str) -> str:
    try:
        done = subprocess.run(["az", *args], capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        sys.exit("azure_spend: the Azure CLI (az) is not installed")
    except subprocess.TimeoutExpired:
        sys.exit(f"azure_spend: az {args[0]} timed out")
    if done.returncode != 0:
        sys.exit(f"azure_spend: az {args[0]} failed: {done.stderr.strip()[:300]}")
    return done.stdout.strip()


def post(url: str, token: str, body: dict) -> dict:
    """POST a query. Retries throttling (429) and server errors. 204 means no cost data."""
    data = json.dumps(body).encode()
    for attempt in range(5):
        request = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            if error.code == 429 or error.code >= 500:
                wait = 2 ** attempt * 5
                try:
                    wait = int(error.headers.get("Retry-After", wait))
                except (TypeError, ValueError):
                    pass
                time.sleep(min(wait, 60))
                continue
            sys.exit(f"azure_spend: Cost Management returned {error.code}: {detail}")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if attempt == 4:
                sys.exit(f"azure_spend: network error ({getattr(error, 'reason', error)})")
            time.sleep(2 ** attempt * 5)
    sys.exit("azure_spend: gave up after retries (Cost Management kept throttling)")


def fetch(cfg: dict) -> dict:
    sub = os.environ.get("AZURE_SUBSCRIPTION_ID", "").strip() or az("account", "show", "--query", "id", "-o", "tsv")
    token = az("account", "get-access-token", "--resource", "https://management.azure.com/",
               "--query", "accessToken", "-o", "tsv")
    url = (f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{cfg['group']}"
           f"/providers/Microsoft.CostManagement/query?api-version={API_VERSION}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results = {}
    for name, body in bodies(cfg["since"], today).items():
        results[name] = post(url, token, body)
        time.sleep(2)  # stay well under the per-scope query rate limit
    return results


def rows(result: dict) -> list[dict]:
    """Turn a QueryResult into dicts keyed by column name. Empty or 204 gives []."""
    props = (result or {}).get("properties") or {}
    names = [c.get("name", "") for c in props.get("columns") or []]
    return [dict(zip(names, row)) for row in props.get("rows") or []]


def cost_of(row: dict) -> float:
    for key in ("totalCost", "PreTaxCost", "Cost", "CostUSD"):
        if key in row:
            return float(row[key] or 0)
    return 0.0


def total(result: dict) -> tuple[float, str]:
    found = rows(result)
    currency = next((str(r.get("Currency")) for r in found if r.get("Currency")), "USD")
    return round(sum(cost_of(r) for r in found), 2), currency


def by_resource(result: dict) -> list[tuple[str, float]]:
    costs: dict[str, float] = {}
    for row in rows(result):
        rid = str(row.get("ResourceId") or "(unattributed)")
        name = rid.rstrip("/").rsplit("/", 1)[-1] or rid
        costs[name] = costs.get(name, 0.0) + cost_of(row)
    return sorted(((n, round(c, 2)) for n, c in costs.items() if round(c, 2) > 0),
                  key=lambda item: -item[1])


def listed_names(text: str) -> set[str]:
    """Resource names in the hand-kept table (first column), lower-cased."""
    manual = text.split(START)[0]
    names = set()
    for line in manual.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            cell = line.strip("|").split("|")[0].strip().strip("`").lower()
            if cell and cell != "resource":
                names.add(cell)
    return names


def last_alert(text: str) -> int:
    match = re.search(r"Last alert level: (\d+)%", text)
    return int(match.group(1)) if match else 0


def render(text: str, cfg: dict, results: dict, stamp: str) -> tuple[str, int | None, list[str]]:
    mtd, currency = total(results.get("month_to_date", {}))
    cumulative, _ = total(results.get("since_start", {}))
    resources = by_resource(results.get("by_resource", {}))
    listed = listed_names(text)
    unlisted = [n for n, _ in resources
                if n != "(unattributed)" and not any(n.lower() in cell for cell in listed)]

    share = cumulative / cfg["cap"] * 100 if cfg["cap"] else 0.0
    reached = max((lvl for lvl in LEVELS if share >= lvl), default=0)
    previous = last_alert(text)
    alert = reached if reached > previous else None
    kept = max(reached, previous)  # alert once per level; cumulative spend only grows

    lines = [
        START,
        "## Spend report (written daily by .github/workflows/azure-spend.yml)",
        "",
        f"- Updated: {stamp} (Cost Management data can lag up to a day)",
        f"- Month to date: ${mtd:.2f} {currency}",
        f"- Since {cfg['since']}: ${cumulative:.2f} of ${cfg['cap']:.0f} cap ({share:.0f}%)",
        f"- Last alert level: {kept}%",
        "",
        "| Resource this month | Cost $ | In the table above? |",
        "|---|---|---|",
    ]
    lines += [f"| {n} | {c:.2f} | {'no: add it' if n in unlisted else 'yes'} |" for n, c in resources]
    if not resources:
        lines.append("| (no costs recorded yet) | 0.00 | - |")
    lines.append(END)
    block = "\n".join(lines)

    mtd_line = f"Month-to-date spend: ${mtd:.2f} {currency} (as of {stamp}; see the spend report below)"
    if re.search(r"^Month-to-date spend:.*$", text, flags=re.M):
        text = re.sub(r"^Month-to-date spend:.*$", lambda _: mtd_line, text, count=1, flags=re.M)
    else:
        text = text.rstrip() + "\n\n" + mtd_line + "\n"
    if START in text and END in text:
        head, rest = text.split(START, 1)
        tail = rest.split(END, 1)[1]
        text = head + block + tail
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    return text, alert, unlisted


def cmd_report(args) -> None:
    cfg = settings()
    if args.from_dir:
        results = {}
        for name in QUERIES:
            path = Path(args.from_dir) / f"{name}.json"
            raw = path.read_text() if path.exists() else ""
            results[name] = json.loads(raw) if raw.strip() else {}
    else:
        results = fetch(cfg)
    if args.save_dir:
        Path(args.save_dir).mkdir(parents=True, exist_ok=True)
        for name, result in results.items():
            (Path(args.save_dir) / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    text, alert, unlisted = render(BUDGET.read_text(), cfg, results, now_iso())
    BUDGET.write_text(text)
    mtd, currency = total(results.get("month_to_date", {}))
    cumulative, _ = total(results.get("since_start", {}))
    print(f"month to date ${mtd:.2f} {currency}; since {cfg['since']} ${cumulative:.2f} of ${cfg['cap']:.0f}")
    for name in unlisted:
        print(f"UNLISTED {name}")
    if alert:
        print(f"ALERT {alert}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("report")
    p.add_argument("--from-dir", help="read saved query responses instead of calling Azure")
    p.add_argument("--save-dir", help="also save the raw responses here (no secrets in them)")
    p.set_defaults(func=cmd_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
