import csv
import os
import re
import shutil
import sys
import tempfile
from datetime import timedelta
from decimal import Decimal

from engine import lookback, money
from engine.lookback import _leave_year_start

DEFAULT_THRESHOLD = Decimal("0.01")
DISCLAIMER = "Not legal advice; a payroll professional signs off."
COLUMNS = ("worker_id", "leave_week", "paid", "due", "difference", "direction", "flags",
           "ref_weeks_used", "ref_weeks_skipped", "ref_weeks_before_first_record", "average", "fixed_basic_rate")
FLAG_TEXT = {
    "no_reference_weeks": "no paid weeks before the leave, so nothing to average",
    "shortened": "fewer than 52 paid weeks were available, so the average uses what exists",
    "leave_week_missing_from_history": "the leave week has no payroll row, so nothing counts as paid",
    "leave_week_without_holiday_pay": "the leave week has pay but none of it is marked holiday_pay, so nothing counts as paid; "
                                      "if that pay was the holiday pay, re-export it as holiday_pay",
    "holiday_pay_week_not_in_leave_file": "an earlier week in this leave year carries holiday_pay but is not listed in leave.csv, "
                                          "so the count of the first 4 leave weeks (normal pay) may be wrong",
    "rate_inferred_no_contract_basic": "no contract basic supplied; the rate was inferred from recent pay",
    "latest_week_basic_differs_from_rate_used": "the latest week's basic differs from the rate used",
    "reference_week_basic_differs_from_contract": "basic in some reference weeks differs from the contract basic",
}


def unlisted_holiday_pay(workers):
    """{worker_id: [week endings with a holiday_pay row that is not in leave.csv]}, only for workers with leave."""
    out = {}
    for wid in sorted(workers):
        w = workers[wid]
        if not w.leave:
            continue
        listed = {e.week_end for e in w.leave}
        weeks = sorted(d for d, p in w.history.items() if "holiday_pay" in p and d not in listed)
        if weeks:
            out[wid] = weeks
    return out


def cannot_check(r):
    return "no_reference_weeks" in r["flags"]


def audit(workers, threshold=DEFAULT_THRESHOLD, include_flagged=False):
    """Return (all_rows, exceptions); each row is an engine row plus worker_id.

    A row that cannot be checked (no reference weeks) is always an exception, never dropped.
    """
    rows = []
    unlisted = unlisted_holiday_pay(workers)
    for wid in sorted(workers):
        w = workers[wid]
        for r in lookback(w.history, w.leave, worker_type=w.worker_type,
                          contract_weekly_basic=w.contract_weekly_basic):
            if any(_leave_year_start(d, 4, 1) == r["leave_year_start"] and d < r["week_end"]
                   for d in unlisted.get(wid, ())):
                r["flags"].append("holiday_pay_week_not_in_leave_file")
            rows.append({"worker_id": wid, "first_week": w.first_week, **r})
    exceptions = [r for r in rows if cannot_check(r) or abs(r["difference"]) > threshold
                  or (include_flagged and r["flags"])]
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


def _direction(diff, r=None):
    if r is not None and cannot_check(r):
        return "cannot_check"
    return "underpaid" if diff > 0 else "overpaid" if diff < 0 else "correct"


def _csv_row(r):
    n = r["working"]["normal"]
    return {"worker_id": _safe(r["worker_id"]), "leave_week": r["week_end"].isoformat(),
            "paid": f"{r['paid']:.2f}", "due": f"{r['due']:.2f}", "difference": f"{r['difference']:.2f}",
            "direction": _direction(r["difference"], r), "flags": _safe(";".join(r["flags"])),
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
    if cannot_check(r):
        lines.append(f"- CANNOT BE CHECKED: no paid weeks before this leave week, so there is nothing to average. "
                     f"Paid in the leave week: {_gbp(r['paid'])}. Any due figure shown is not reliable.")
    else:
        lines.append(f"- Due: {_gbp(r['due'])}. Paid in the leave week: {_gbp(r['paid'])}. "
                     f"Result: {_direction(r['difference'])} by {_gbp(abs(r['difference']))}.")
    if "leave_week_without_holiday_pay" in r["flags"]:
        lines.append(f"- Pay in this week that was not marked as holiday pay: {_gbp(r['other_pay_in_leave_week'])}.")
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


def _week_ranges(weeks):
    """Group sorted week endings into runs of consecutive weeks: 'a to b (n weeks)', or 'a' for a single week."""
    runs = []
    for d in weeks:
        if runs and d - runs[-1][-1] == timedelta(days=7):
            runs[-1].append(d)
        else:
            runs.append([d])
    return [r[0].isoformat() if len(r) == 1 else f"{r[0].isoformat()} to {r[-1].isoformat()} ({len(r)} weeks)"
            for r in runs]


def _gap_section(gaps):
    if not gaps:
        return []
    out = ["", "## Warning: weeks missing from the export", "",
           "These weeks fall between the worker's first and last record but have no rows at all. "
           "Confirm these were genuinely unpaid weeks and not missing from the export; "
           "the results above treat them as unpaid.", ""]
    out += [f"- {_md(wid)}: {len(ws)} week(s): {', '.join(_week_ranges(ws))}" for wid, ws in gaps.items()]
    return out


def _atomic_write_pair(out_dir, files):
    """files: [(name, writer(fh), open_kwargs)]. Write all to temp files, then move all into place.

    Guarantees, for any Python exception (including a failing os.replace):
    - the folder ends up holding either the complete new set of files or exactly what it held before.
      If a later rename fails after an earlier one succeeded, the earlier file is rolled back: the previous
      file is restored from a hard-linked backup (or a copy where hard links are unavailable), or the new
      file is removed when there was no previous file;
    - no temp or backup files are left behind.
    Not covered: a crash or power loss in the middle of the renames can still leave a mismatched pair,
    and if rolling back itself fails, the backup of the previous file is kept (never deleted) and the raised
    OSError names its path and says the files may not match.
    Files are created owner-only (mode 0600) because mkstemp is used; see ingest/FORMAT.md.
    """
    os.makedirs(out_dir, exist_ok=True)
    temps = []      # (tmp path, dest path) not yet moved into place
    backups = []    # (backup path or None, dest path) for each dest already replaced
    leftovers = []  # backup files to remove at the end
    try:
        for name, writer, kw in files:
            fd, tmp = tempfile.mkstemp(prefix="." + name + ".", suffix=".tmp", dir=out_dir)
            temps.append((tmp, os.path.join(out_dir, name)))
            with os.fdopen(fd, "w", **kw) as fh:
                writer(fh)
        try:
            while temps:
                tmp, dest = temps[0]
                backup = None
                if os.path.lexists(dest):
                    # mkstemp reserves a unique random name; the empty placeholder is removed so the
                    # hard link (or the copy fallback) can take its place.
                    fd, backup = tempfile.mkstemp(prefix="." + os.path.basename(dest) + ".", suffix=".bak", dir=out_dir)
                    os.close(fd)
                    leftovers.append(backup)
                    os.remove(backup)
                    try:
                        os.link(dest, backup, follow_symlinks=False)
                    except (OSError, NotImplementedError):
                        shutil.copy2(dest, backup)
                os.replace(tmp, dest)
                temps.pop(0)
                backups.append((backup, dest))
        except BaseException as exc:
            problems = []
            for backup, dest in reversed(backups):
                try:
                    if backup:
                        os.replace(backup, dest)
                    else:
                        os.remove(dest)
                except OSError as rb:
                    if backup:
                        leftovers.remove(backup)   # last copy of the previous file: never delete it
                        problems.append(f"previous {os.path.basename(dest)} kept at {backup} ({rb})")
                    else:
                        problems.append(f"new {dest} could not be removed ({rb})")
            if problems:
                note = ("rollback failed, the output files may not match: " + "; ".join(problems))
                if not isinstance(exc, Exception):
                    # An interrupt (KeyboardInterrupt etc.) must stay an interrupt: attach the note, tell the
                    # user on stderr, and re-raise the original.
                    if hasattr(exc, "add_note"):
                        exc.add_note(note)
                    print(note, file=sys.stderr)
                    raise
                raise OSError(f"{exc}; rollback failed, the output files may not match: "
                              + "; ".join(problems)) from exc
            raise
    finally:
        for tmp, _ in temps:
            try:
                os.remove(tmp)
            except OSError:
                pass
        for bak in leftovers:
            try:
                os.remove(bak)
            except OSError:
                pass


def _unlisted_section(unlisted):
    if not unlisted:
        return []
    out = ["", "## Warning: holiday pay recorded but no leave row", "",
           "These weeks carry a holiday_pay row but are not listed in leave.csv. The first 4 leave weeks of a leave year "
           "get normal pay and later weeks basic-only pay, so a missing leave row can change the result. "
           "Add the weeks to leave.csv if they were leave, then re-run. Affected leave weeks are flagged "
           "`holiday_pay_week_not_in_leave_file`.", ""]
    out += [f"- {_md(wid)}: {len(ws)} week(s): {', '.join(_week_ranges(ws))}" for wid, ws in unlisted.items()]
    return out


def write_outputs(out_dir, rows, exceptions, threshold=DEFAULT_THRESHOLD, gaps=None, workers_loaded=None, unlisted=None):
    under = [r for r in rows if not cannot_check(r) and r["difference"] > threshold]
    over = [r for r in rows if not cannot_check(r) and r["difference"] < -threshold]
    unchecked = [r for r in rows if cannot_check(r)]
    flagged = sorted({r["worker_id"] for r in rows if r["flags"]})
    with_leave = len({r["worker_id"] for r in rows})
    md = [f"# Holiday pay look-back audit", "", f"**{DISCLAIMER}**", "", "## Summary", ""]
    if workers_loaded is not None:
        md.append(f"- Workers loaded: {workers_loaded}")
    md += [f"- Workers with leave: {with_leave}",
           f"- Leave weeks checked: {len(rows)}",
           f"- Exceptions (difference over {_gbp(threshold)}, or cannot be checked): {len(exceptions)}",
           f"- Leave weeks that could not be checked: {len(unchecked)}",
           f"- Underpayments: {len(under)}, total underpaid {_gbp(sum((r['difference'] for r in under), Decimal(0)))}",
           f"- Overpayments: {len(over)}, total overpaid {_gbp(sum((-r['difference'] for r in over), Decimal(0)))}",
           f"- Workers with flags: {len(flagged)}" + (f" ({', '.join(_md(f) for f in flagged)})" if flagged else ""),
           ]
    if gaps is not None:
        md.append(f"- Workers with weeks missing from the export: {len(gaps)}")
    if unlisted:
        md.append(f"- Workers with holiday pay outside leave.csv: {len(unlisted)}")
    md += ["", "## Exceptions", ""]
    md += [explain(r) for r in exceptions] or ["None.\n"]
    md += _gap_section(gaps)
    md += _unlisted_section(unlisted)

    def write_csv(fh):
        w = csv.DictWriter(fh, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(_csv_row(r) for r in exceptions)

    _atomic_write_pair(out_dir, [
        ("exceptions.csv", write_csv, {"newline": "", "encoding": "utf-8"}),
        ("report.md", lambda fh: fh.write("\n".join(md)), {"encoding": "utf-8"})])
