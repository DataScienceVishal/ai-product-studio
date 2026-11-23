#!/usr/bin/env python3
"""Azure spend report for rg-ai-studio. Standard library plus the Azure CLI for sign-in.

Runs daily in .github/workflows/azure-spend.yml after azure/login. It asks Azure Cost Management
for the resource group's actual cost, lists the group's resources, and rewrites the auto section of
state/BUDGET.md. Every outcome is written down, so a run that can't get figures says so in the file
instead of only failing in the Actions tab:

  Status: ok            figures are real (they can lag by up to a day)
  Status: unavailable   Cost Management refused or failed (for example the offer isn't supported);
                        spend is unknown, and the resource inventory still checks the table
  marker error          BUDGET.md's auto-section markers are malformed: nothing is written, exit 3

Commands
  report [--from-dir DIR] [--save-dir DIR]
      Fetch (or read saved responses from DIR), update state/BUDGET.md, and print:
        the summary line, STATUS <ok|unavailable|currency>, UNLISTED <name> per resource missing
        from the table, and ALERT <level> when spend first passes 50%, 75% or 95% of the cap.
      Alerts and new outages are also added to state/DIGEST_NOTES.md for the next digest.

Environment (all optional)
  AZURE_SUBSCRIPTION_ID   defaults to `az account show`
  STUDIO_RESOURCE_GROUP   defaults to rg-ai-studio
  STUDIO_SPEND_SINCE      first day counted against the cap, YYYY-MM-DD (default 2026-11-01)
  STUDIO_SPEND_CAP        cap in USD (default 80)

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
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGET = ROOT / "state" / "BUDGET.md"
DIGEST = ROOT / "state" / "DIGEST_NOTES.md"
API_VERSION = "2026-06-01"  # Cost Management Query - Usage, checked 2026-11-23
START = "<!-- spend:auto:start -->"
END = "<!-- spend:auto:end -->"
START_LINE = re.compile(r"^<!-- spend:auto:start -->[ \t]*$", re.M)
END_LINE = re.compile(r"^<!-- spend:auto:end -->[ \t]*$", re.M)
LEVELS = (50, 75, 95)
QUERIES = ("month_to_date", "since_start", "by_resource")
MAX_RANGE_DAYS = 364  # the Query API rejects custom ranges longer than a year
RETRY_HEADERS = (  # Cost Management's documented throttling hints, then the generic one
    "x-ms-ratelimit-microsoft.costmanagement-qpu-retry-after",
    "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after",
    "x-ms-ratelimit-microsoft.costmanagement-tenant-retry-after",
    "retry-after",
)


class Unavailable(Exception):
    """Cost Management (or the CLI) can't give figures right now."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


class MarkerError(Exception):
    pass


@dataclass
class Outcome:
    results: dict | None = None
    error: Unavailable | None = None
    inventory: list[dict] | None = None
    inventory_error: str | None = None


def one_line(text: str) -> str:
    return " ".join((text or "").split())


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def settings() -> dict:
    since = os.environ.get("STUDIO_SPEND_SINCE", "2026-11-01").strip()
    try:
        date.fromisoformat(since)
    except ValueError:
        sys.exit(f"azure_spend: STUDIO_SPEND_SINCE must be YYYY-MM-DD, got '{since}'")
    try:
        cap = float(os.environ.get("STUDIO_SPEND_CAP", "80"))
    except ValueError:
        sys.exit("azure_spend: STUDIO_SPEND_CAP must be a number")
    return {"group": os.environ.get("STUDIO_RESOURCE_GROUP", "rg-ai-studio").strip(), "since": since, "cap": cap}


# --- Azure calls -----------------------------------------------------------------------------

def query_window(since: str, today: date) -> tuple[str, str, bool]:
    start, clamped = date.fromisoformat(since), False
    earliest = today - timedelta(days=MAX_RANGE_DAYS)
    if start < earliest:
        start, clamped = earliest, True
    return start.isoformat(), today.isoformat(), clamped


def bodies(since: str, today: date) -> dict:
    """Request bodies in the shape the Cost Management docs use (type Usage = actual cost)."""
    total = {"totalCost": {"name": "PreTaxCost", "function": "Sum"}}
    start, end, _ = query_window(since, today)
    return {
        "month_to_date": {"type": "Usage", "timeframe": "MonthToDate",
                          "dataset": {"granularity": "None", "aggregation": total}},
        "since_start": {"type": "Usage", "timeframe": "Custom",
                        "timePeriod": {"from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"},
                        "dataset": {"granularity": "None", "aggregation": total}},
        "by_resource": {"type": "Usage", "timeframe": "MonthToDate",
                        "dataset": {"granularity": "None", "aggregation": total,
                                    "grouping": [{"type": "Dimension", "name": "ResourceId"}]}},
    }


def az(*args: str, attempts: int = 3, sleep=time.sleep) -> str:
    last = ""
    for attempt in range(1, attempts + 1):
        try:
            done = subprocess.run(["az", *args], capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            raise Unavailable("no_az_cli", "the Azure CLI (az) is not installed") from None
        except subprocess.TimeoutExpired:
            last = f"az {args[0]} timed out"
        else:
            if done.returncode == 0:
                return done.stdout.strip()
            last = f"az {args[0]} failed: {one_line(done.stderr)[:200]}"
        if attempt < attempts:
            sleep(5 * attempt)
    raise Unavailable("az_failed", last)


def retry_wait(headers, default: float) -> float:
    for name in RETRY_HEADERS:
        value = headers.get(name) if headers is not None else None
        if value:
            try:
                return float(value)
            except ValueError:
                continue
    return default


def azure_error(text: str) -> str:
    try:
        error = json.loads(text).get("error") or {}
        return one_line(f"{error.get('code', 'error')}: {error.get('message', '')}")[:240]
    except (ValueError, AttributeError):
        return one_line(text)[:240] or "no details"


def post(url: str, token: str, body: dict, attempts: int = 5, sleep=time.sleep,
         opener=urllib.request.urlopen) -> dict:
    """POST one query. Retries throttling and server errors; other HTTP errors mean 'unavailable'."""
    data = json.dumps(body).encode()
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with opener(request, timeout=60) as response:
                raw = response.read().decode()
                return json.loads(raw) if raw.strip() else {}  # 204 No Content: no data
        except urllib.error.HTTPError as error:
            text = error.read().decode(errors="replace")
            if error.code == 429 or error.code >= 500:
                reason = "kept throttling (429)" if error.code == 429 else f"kept failing ({error.code})"
                if attempt == attempts:
                    raise Unavailable(f"http_{error.code}", f"Cost Management {reason} over {attempts} tries") from None
                sleep(min(retry_wait(error.headers, 5 * 2 ** (attempt - 1)), 60))
                continue
            raise Unavailable(f"http_{error.code}", azure_error(text)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if attempt == attempts:
                raise Unavailable("network", f"network error ({getattr(error, 'reason', error)})") from None
            sleep(5 * 2 ** (attempt - 1))
    raise Unavailable("unknown", "gave up")


def fetch(cfg: dict, today: date) -> dict:
    sub = os.environ.get("AZURE_SUBSCRIPTION_ID", "").strip() or az("account", "show", "--query", "id", "-o", "tsv")
    token = az("account", "get-access-token", "--resource", "https://management.azure.com/",
               "--query", "accessToken", "-o", "tsv")
    url = (f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{cfg['group']}"
           f"/providers/Microsoft.CostManagement/query?api-version={API_VERSION}")
    results = {}
    for name, body in bodies(cfg["since"], today).items():
        results[name] = post(url, token, body)
        time.sleep(2)  # the docs ask callers to stay well under the per-scope rate limit
    return results


def inventory(cfg: dict) -> tuple[list[dict] | None, str | None]:
    """The group's resources from ARM. Works even where Cost Management doesn't."""
    try:
        listed = json.loads(az("resource", "list", "--resource-group", cfg["group"], "-o", "json") or "[]")
    except Unavailable as error:
        return None, f"{error.code}: {error.detail}"
    except ValueError:
        return None, "az resource list returned something that isn't JSON"
    return [{"id": r.get("id", ""), "name": r.get("name", ""), "type": r.get("type", "")} for r in listed], None


# --- parsing ---------------------------------------------------------------------------------

def rows(result: dict | None) -> list[dict]:
    props = (result or {}).get("properties") or {}
    names = [c.get("name", "") for c in props.get("columns") or []]
    return [dict(zip(names, row)) for row in props.get("rows") or []]


def cost_of(row: dict) -> float:
    for key in ("totalCost", "PreTaxCost", "Cost", "CostUSD"):
        if key in row:
            return float(row[key] or 0)
    return 0.0


def total(result: dict | None) -> tuple[float, str | None, int]:
    """(amount, currency or None when no rows came back, number of rows)."""
    found = rows(result)
    currency = next((str(r["Currency"]) for r in found if r.get("Currency")), None)
    return round(sum(cost_of(r) for r in found), 2), currency, len(found)


def top_level(resource_id: str) -> tuple[str, str]:
    """(top-level resource name, display name) from an ARM id. Child resources keep their path,
    so two storage accounts' blobServices/default don't collapse into one 'default' row."""
    # /subscriptions/{s}/resourceGroups/{g}/providers/{namespace}/{type}/{name}[/{childType}/{childName}...]
    parts = [p for p in resource_id.strip("/").split("/") if p]
    lowered = [p.lower() for p in parts]
    if "providers" in lowered:
        after = parts[lowered.index("providers") + 1:]
        if len(after) >= 3:
            child = "/".join(after[3:])
            return after[2], after[2] + (f"/{child}" if child else "")
    name = parts[-1] if parts else resource_id
    return name, name


def split_block(text: str) -> tuple[str, str | None, str]:
    starts, ends = list(START_LINE.finditer(text)), list(END_LINE.finditer(text))
    if not starts and not ends:
        return text, None, ""
    if len(starts) == 1 and len(ends) == 1 and starts[0].start() < ends[0].start():
        return text[:starts[0].start()], text[starts[0].start():ends[0].end()], text[ends[0].end():]
    raise MarkerError(
        f"state/BUDGET.md has {len(starts)} start and {len(ends)} end marker lines; expected exactly one of each, "
        "start first. Fix the file by hand. Nothing was written.")


def table_rows(text: str) -> list[list[str]]:
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and not re.match(r"^\|\s*:?-{3,}", stripped):
            out.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return out


def listed_names(outside: str) -> set[str]:
    """First word of each hand-kept table row's first cell, lower-cased (header rows skipped)."""
    names = set()
    for cells in table_rows(outside):
        token = re.split(r"[\s(]", cells[0].strip("`").strip(), maxsplit=1)[0].strip("`").lower()
        if token and token != "resource":
            names.add(token)
    return names


def projected_monthly(outside: str) -> float:
    """Sum of the 'Estimated $ per month' column of the hand-kept table."""
    column, totalled = None, 0.0
    for cells in table_rows(outside):
        lowered = [c.lower() for c in cells]
        if any("estimated" in c for c in lowered):
            column = next(i for i, c in enumerate(lowered) if "estimated" in c)
            continue
        if column is not None and column < len(cells):
            match = re.search(r"-?\d+(?:\.\d+)?", cells[column].replace(",", ""))
            if match:
                totalled += float(match.group())
    return round(totalled, 2)


def previous(block: str | None) -> dict:
    block = block or ""
    level = re.search(r"Last alert level: (\d+)% \(since (\d{4}-\d{2}-\d{2})\)", block)
    status = re.search(r"Status: unavailable since (\d{4}-\d{2}-\d{2}): (\S+)", block)
    code = re.search(r"^- Status: (\w+)", block, re.M)
    return {"level": int(level.group(1)) if level else 0, "level_since": level.group(2) if level else None,
            "down_since": status.group(1) if status else None, "down_code": status.group(2) if status else None,
            "status": code.group(1) if code else None}


def money(amount: float, currency: str | None) -> str:
    return f"${amount:.2f}" if currency in (None, "USD") else f"{amount:.2f} {currency}"


# --- the report ------------------------------------------------------------------------------

def render(text: str, cfg: dict, outcome: Outcome, stamp: str, today: date):
    """Returns (new text, alert level or None, unlisted names, status, digest lines)."""
    head, block, tail = split_block(text)
    outside = head + tail
    before = previous(block)
    listed = listed_names(outside)
    digest: list[str] = []

    results = outcome.results if outcome.error is None else None
    if outcome.error is not None:
        status = "unavailable"
        since_down = before["down_since"] if before["down_code"] == outcome.error.code else today.isoformat()
        status_line = f"- Status: unavailable since {since_down}: {outcome.error.code} ({outcome.error.detail}). Spend is unknown."
        if before["down_code"] != outcome.error.code:
            digest.append(f"- [budget] The Azure spend report is unavailable ({outcome.error.code}), so spend is unknown. "
                          "See state/BUDGET.md and HURDLES.md.")
    else:
        status, status_line = "ok", "- Status: ok"

    lines = [START, "## Spend report (written daily by .github/workflows/azure-spend.yml)", "",
             f"- Updated: {stamp}. Covers resource group {cfg['group']} only; Cost Management data can lag by up to a day."]
    alert, cumulative = None, None
    costs_known = results is not None  # false when unavailable or when Azure returned no rows
    kept = before["level"] if before["level_since"] == cfg["since"] else 0  # a new since date starts afresh
    if results is not None:
        mtd, mtd_cur, mtd_rows = total(results.get("month_to_date"))
        cumulative, cum_cur, cum_rows = total(results.get("since_start"))
        _, _, res_rows = total(results.get("by_resource"))
        currencies = {c for c in (mtd_cur, cum_cur) if c}
        start, _, clamped = query_window(cfg["since"], today)
        if currencies - {"USD"}:
            status = "currency"
            status_line = (f"- Status: currency: figures are in {', '.join(sorted(currencies))}, not USD, so they can't be "
                           f"compared with the ${cfg['cap']:.0f} cap. Convert by hand or change the cap's currency.")
            lines += [status_line, f"- Since {start}: {money(cumulative, cum_cur)}", f"- Month to date: {money(mtd, mtd_cur)}"]
        elif mtd_rows == 0 and cum_rows == 0:
            # No rows is "no data", not "$0.00": a new subscription, data lag, or an offer that returns nothing.
            status = "no_data"
            costs_known = False  # so the inventory check flags every unlisted resource
            lines.append("- Status: no_data: Azure returned no cost rows (new subscription, data lag, or an "
                         "unsupported offer). Spend is unknown.")
        else:
            share = cumulative / cfg["cap"] * 100 if cfg["cap"] else 0.0
            reached = max((lvl for lvl in LEVELS if share >= lvl), default=0)
            alert = reached if reached > kept else None
            kept = max(reached, kept)
            lines += [status_line, f"- Since {start}: {money(cumulative, 'USD')} of ${cfg['cap']:.0f} cap ({share:.0f}%)",
                      f"- Month to date: {money(mtd, 'USD')}"]
            if alert:
                digest.append(f"- [budget] Azure spend passed {alert}% of the ${cfg['cap']:.0f} cap: "
                              f"{money(cumulative, 'USD')} since {start}. See state/BUDGET.md.")
        lines.append(f"- Cost rows returned: month to date {mtd_rows}, since start {cum_rows}, by resource {res_rows}")
        if clamped:
            lines.append(f"- The since-start range was shortened to the last {MAX_RANGE_DAYS} days (API limit).")
        if any(((results.get(q) or {}).get("properties") or {}).get("nextLink") for q in QUERIES):
            lines.append("- Azure returned more pages (nextLink) that this report doesn't read; totals may be low.")
    else:
        lines.append(status_line)
    lines.append(f"- Projected monthly cost from the table above: ${projected_monthly(outside):.2f}")
    lines.append(f"- Last alert level: {kept}% (since {cfg['since']})")

    # resources: inventory plus anything that cost money, keyed by full id
    resources: dict[str, dict] = {}
    for item in outcome.inventory or []:
        name, display = top_level(item["id"])
        resources[item["id"].lower()] = {"name": name, "display": display, "type": item["type"], "cost": None}
    for row in rows((results or {}).get("by_resource")):
        rid = str(row.get("ResourceId") or "")
        key = rid.lower() or "(unattributed)"
        name, display = top_level(rid) if rid else ("(unattributed)", "(unattributed)")
        entry = resources.setdefault(key, {"name": name, "display": display, "type": "", "cost": None})
        entry["cost"] = round((entry["cost"] or 0.0) + cost_of(row), 2)
    def needs_listing(entry: dict) -> bool:
        """Missing from the table and either costing money, or of unknown cost because figures are unavailable."""
        if entry["name"] == "(unattributed)" or entry["name"].lower() in listed:
            return False
        if entry["cost"] is not None:
            return entry["cost"] > 0
        return not costs_known

    unlisted = sorted({r["name"] for r in resources.values() if needs_listing(r)})
    if outcome.inventory is not None:
        lines.append(f"- Inventory: {len(outcome.inventory)} resources in {cfg['group']}, "
                     f"{len(unlisted)} not in the table above")
    else:
        lines.append(f"- Inventory unavailable: {outcome.inventory_error or 'not fetched'}")
    lines += ["", "| Resource | Type | Cost this month | In the table above? |", "|---|---|---|---|"]
    for entry in sorted(resources.values(), key=lambda r: (-(r["cost"] or 0), r["display"])):
        cost = "-" if entry["cost"] is None else f"{entry['cost']:.2f}"
        if entry["name"] == "(unattributed)":
            where = "-"
        elif entry["name"].lower() in listed:
            where = "yes"
        else:
            where = "no: add it" if needs_listing(entry) else "no (no cost so far)"
        lines.append(f"| {entry['display']} | {entry['type'] or '-'} | {cost} | {where} |")
    if not resources:
        lines.append("| (no resources or costs seen) | - | - | - |")
    lines.append(END)
    new_block = "\n".join(lines)

    if block is None:
        new_text = head.rstrip() + "\n\n" + new_block + "\n"
    else:
        new_text = head + new_block + tail
    summary = (f"Since {cfg['since']}: {money(cumulative, 'USD')} of ${cfg['cap']:.0f}" if status == "ok"
               else f"spend unknown ({status})")
    new_text = re.sub(r"^Month-to-date spend:.*$", lambda _: f"Month-to-date spend: see the spend report below ({summary}, "
                      f"updated {stamp})", new_text, count=1, flags=re.M)
    return new_text, alert, unlisted, status, digest


def cmd_report(args) -> None:
    cfg = settings()
    today = datetime.now(timezone.utc).date()
    text = BUDGET.read_text(encoding="utf-8")
    try:
        split_block(text)  # refuse early, before any API call, if the markers are malformed
    except MarkerError as error:
        print(f"azure_spend: {error}", file=sys.stderr)
        sys.exit(3)
    outcome = Outcome()
    if args.from_dir:
        folder = Path(args.from_dir)
        saved = json.loads((folder / "outcome.json").read_text(encoding="utf-8"))
        outcome.results = saved.get("results")
        outcome.error = Unavailable(**saved["error"]) if saved.get("error") else None
        outcome.inventory, outcome.inventory_error = saved.get("inventory"), saved.get("inventory_error")
    else:
        try:
            outcome.results = fetch(cfg, today)
        except Unavailable as error:
            outcome.error = error
        outcome.inventory, outcome.inventory_error = inventory(cfg)
    if args.save_dir:
        folder = Path(args.save_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "outcome.json").write_text(json.dumps({
            "results": outcome.results, "inventory": outcome.inventory, "inventory_error": outcome.inventory_error,
            "error": {"code": outcome.error.code, "detail": outcome.error.detail} if outcome.error else None,
        }, indent=2), encoding="utf-8")
    previous_status = previous(split_block(text)[1])["status"]
    new_text, alert, unlisted, status, digest = render(text, cfg, outcome, now_iso(), today)
    BUDGET.write_text(new_text, encoding="utf-8")
    if digest and DIGEST.exists():
        DIGEST.write_text(DIGEST.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(digest) + "\n", encoding="utf-8")
    if outcome.results is not None and status == "ok":
        cumulative, _, _ = total(outcome.results.get("since_start"))
        mtd, _, _ = total(outcome.results.get("month_to_date"))
        print(f"since {cfg['since']} ${cumulative:.2f} of ${cfg['cap']:.0f}; month to date ${mtd:.2f}")
    else:
        detail = f"{outcome.error.code}: {outcome.error.detail}" if outcome.error else status
        print(f"spend unknown ({detail})")
    print(f"STATUS {status}")
    print(f"CHANGED {'yes' if status != previous_status else 'no'}")
    for name in unlisted:
        print(f"UNLISTED {name}")
    if alert:
        print(f"ALERT {alert}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("report")
    p.add_argument("--from-dir", help="read a saved outcome.json instead of calling Azure")
    p.add_argument("--save-dir", help="also save the outcome (no secrets in it) as outcome.json here")
    p.set_defaults(func=cmd_report)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
