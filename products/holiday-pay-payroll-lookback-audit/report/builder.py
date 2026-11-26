import csv
import os
import re
import tempfile
from datetime import timedelta
from decimal import Decimal

from engine import lookback, money

DEFAULT_THRESHOLD = Decimal("0.01")
DISCLAIMER = "Not legal advice; a payroll professional signs off."
COLUMNS = ("worker_id", "leave_week", "paid", "due", "difference", "direction", "flags",
           "ref_weeks_used", "ref_weeks_skipped", "ref_weeks_before_first_record", "average", "fixed_basic_rate")
FLAG_TEXT = {
    "no_reference_weeks": "no paid weeks before the leave, so nothing to average",
    "shortened": "fewer than 52 paid weeks were available, so the average uses what exists",
    "leave_week_missing_from_history": "the leave week has no payroll row, so nothing counts as paid",
    "rate_inferred_no_contract_basic": "no contract basic supplied; the rate was inferred from recent pay",
    "latest_week_basic_differs_from_rate_used": "the latest week's basic differs from the rate used",
    "reference_week_basic_differs_from_contract": "basic in some reference weeks differs from the contract basic",
}


def audit(workers, threshold=DEFAULT_THRESHOLD, include_flagged=False):
    """Return (all_rows, exceptions); each row is an engine row plus worker_id."""
    rows = []
    for wid in sorted(workers):
        w = workers[wid]
        for r in lookback(w.history, w.leave, worker_type=w.worker_type,
                          contract_weekly_basic=w.contract_weekly_basic):
            rows.append({"worker_id": wid, "first_week": w.first_week, **r})
    exceptions = [r for r in rows if abs(r["difference"]) > threshold or (include_flagged and r["flags"])]
    return rows, exceptions


def _md(text):
    """Escape Markdown-special characters in untrusted text."""
    return re.sub(r"([\\`*_{}\[\]()#+!|<>~-])", r"\\\1", str(text))


def _safe(cell):
    cell = str(cell)
    return "'" + cell if cell[:1] in ("=", "+", "-", "@", "\t", "\r") else cell


def _split_skipped(r):
    """(weeks before the first payroll row, no-pay weeks inside the history) among the weeks skipped."""
    n = r["working"]["normal"]
    before = sum(1 for i in range(1, n["weeks_scanned"] + 1)
                 if r["week_end"] - timedelta(days=7 * i) < r["first_week"])
    return before, n["weeks_skipped"] - before


def _gbp(x):
    return f"£{money(x):,.2f}"


def _direction(diff):
    return "underpaid" if diff > 0 else "overpaid" if diff < 0 else "correct"


def _csv_row(r):
    n = r["working"]["normal"]
    return {"worker_id": _safe(r["worker_id"]), "leave_week": r["week_end"].isoformat(),
            "paid": f"{r['paid']:.2f}", "due": f"{r['due']:.2f}", "difference": f"{r['difference']:.2f}",
            "direction": _direction(r["difference"]), "flags": _safe(";".join(r["flags"])),
            "ref_weeks_used": n["weeks_used"], "ref_weeks_skipped": _split_skipped(r)[1],
            "ref_weeks_before_first_record": _split_skipped(r)[0],
            "average": f"{n['average']:.2f}",
            "fixed_basic_rate": f"{n['current_basic']:.2f}" if "current_basic" in n else ""}


def explain(r):
    n, b = r["working"]["normal"], r["working"]["basic"]
    fixed = r["worker_type"] == "fixed_pay"
    lines = [f"### {_md(r['worker_id'])}, week ending {r['week_end']}", ""]
    lines.append(f"- Leave: {r['leave_weeks']} week(s) in the leave year starting {r['leave_year_start']}: "
                 f"{r['normal_weeks']} at normal pay, {r['basic_weeks']} at basic pay only.")
    before, nopay = _split_skipped(r)
    scope = (f"{n['weeks_used']} paid week(s) found looking back {n['weeks_scanned']} week(s): "
             f"{nopay} week(s) with no pay that counts skipped (no pay, or only excluded items such as SSP), "
             f"{before} week(s) before the first payroll record in the file not counted (no data)")
    if fixed:
        lines.append(f"- Fixed-pay worker: current weekly basic {_gbp(n['current_basic'])} ({n['basic_source']}) "
                     f"plus the average of variable pay over {scope}: {_gbp(n['average'])} a week.")
    else:
        lines.append(f"- Normal weekly pay: average ({scope}) = {_gbp(n['total'])} / {n['weeks_used']} = {_gbp(n['average'])}.")
        if r["basic_weeks"]:
            lines.append(f"- Basic-only weekly pay (for the remaining leave): {_gbp(b['average'])}.")
    lines.append(f"- Due: {_gbp(r['due'])}. Paid in the leave week: {_gbp(r['paid'])}. "
                 f"Result: {_direction(r['difference'])} by {_gbp(abs(r['difference']))}.")
    for f in r["flags"]:
        lines.append(f"- Flag `{f}`: {FLAG_TEXT.get(f, f)}.")
    return "\n".join(lines) + "\n"


def history_gaps(workers):
    """{worker_id: [week endings between the first and last payroll row with no rows at all]}."""
    gaps = {}
    for wid in sorted(workers):
        weeks = sorted(workers[wid].history)
        have, missing, d = set(weeks), [], weeks[0] + timedelta(days=7)
        while d < weeks[-1]:
            if d not in have:
                missing.append(d)
            d += timedelta(days=7)
        if missing:
            gaps[wid] = missing
    return gaps


def _gap_section(gaps):
    if not gaps:
        return []
    out = ["", "## Warning: weeks missing from the export", "",
           "These weeks fall between the worker's first and last record but have no rows at all. "
           "Confirm these were genuinely unpaid weeks and not missing from the export; "
           "the results above treat them as unpaid.", ""]
    out += [f"- {_md(wid)}: {len(ws)} week(s): {', '.join(d.isoformat() for d in ws)}" for wid, ws in gaps.items()]
    return out


def _atomic_write_pair(out_dir, files):
    """files: [(name, writer(fh))]. Write all to temp files, then rename all into place."""
    os.makedirs(out_dir, exist_ok=True)
    temps = []
    try:
        for name, writer, kw in files:
            fd, tmp = tempfile.mkstemp(prefix="." + name + ".", suffix=".tmp", dir=out_dir)
            temps.append((tmp, os.path.join(out_dir, name)))
            with os.fdopen(fd, "w", **kw) as fh:
                writer(fh)
        for tmp, dest in temps:
            os.replace(tmp, dest)
            temps = [t for t in temps if t[0] != tmp]
    finally:
        for tmp, _ in temps:
            try:
                os.remove(tmp)
            except OSError:
                pass


def write_outputs(out_dir, rows, exceptions, threshold=DEFAULT_THRESHOLD, gaps=None, workers_loaded=None):
    under = [r for r in rows if r["difference"] > threshold]
    over = [r for r in rows if r["difference"] < -threshold]
    flagged = sorted({r["worker_id"] for r in rows if r["flags"]})
    with_leave = len({r["worker_id"] for r in rows})
    md = [f"# Holiday pay look-back audit", "", f"**{DISCLAIMER}**", "", "## Summary", ""]
    if workers_loaded is not None:
        md.append(f"- Workers loaded: {workers_loaded}")
    md += [f"- Workers with leave: {with_leave}",
           f"- Leave weeks checked: {len(rows)}",
           f"- Exceptions (difference over {_gbp(threshold)}): {len(exceptions)}",
           f"- Underpayments: {len(under)}, total underpaid {_gbp(sum((r['difference'] for r in under), Decimal(0)))}",
           f"- Overpayments: {len(over)}, total overpaid {_gbp(sum((-r['difference'] for r in over), Decimal(0)))}",
           f"- Workers with flags: {len(flagged)}" + (f" ({', '.join(flagged)})" if flagged else ""),
           f"- Workers with weeks missing from the export: {len(gaps or {})}", "",
           "## Exceptions", ""]
    md += [explain(r) for r in exceptions] or ["None.\n"]
    md += _gap_section(gaps)

    def write_csv(fh):
        w = csv.DictWriter(fh, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(_csv_row(r) for r in exceptions)

    _atomic_write_pair(out_dir, [
        ("exceptions.csv", write_csv, {"newline": "", "encoding": "utf-8"}),
        ("report.md", lambda fh: fh.write("\n".join(md)), {"encoding": "utf-8"})])
