import csv
import os
import re
import shutil
import sys
import tempfile
from datetime import timedelta
from collections import Counter
from decimal import Decimal

from engine import lookback, money
from engine.lookback import leave_year_start_date, ROLLED_UP_TYPE
from .rolled_up import HOLIDAY_PAID, audit_rolled_up, rolled_up_leave_weeks, stray_rolled_up, explain_rolled_up, holiday_pay_to_rolled_up, md_escape, rolled_up_idle, rolled_up_leave_missing

DEFAULT_THRESHOLD = Decimal("0.01")
DISCLAIMER = "Not legal advice; a payroll professional signs off."
COLUMNS = ("worker_id", "leave_week", "paid", "due", "difference", "direction", "flags",
           "ref_weeks_used", "ref_weeks_skipped", "ref_weeks_before_first_record", "average", "fixed_basic_rate", "check")
CHECK_LOOKBACK, CHECK_ROLLED_UP = "leave_lookback", "rolled_up_pay"
FLAG_TEXT = {
    "no_reference_weeks": "no paid weeks before the leave, so nothing to average",
    "shortened": "fewer than 52 paid weeks were available, so the average uses what exists",
    "leave_week_missing_from_history": "the leave week has no payroll row, so nothing counts as paid",
    "leave_week_without_holiday_pay": "the leave week has pay but none of it is marked holiday_pay, so nothing counts as paid; "
                                      "if that pay was the holiday pay, re-export it as holiday_pay",
    "holiday_pay_week_not_in_leave_file": "an earlier week in this leave year carries holiday_pay but is not listed in leave.csv, "
                                          "so the count of the first 4 leave weeks (normal pay) may be wrong",
    "rate_inferred_no_contract_basic": "no contract basic supplied; the rate was inferred from recent pay",
    "rate_inferred_ambiguous": "no contract basic was supplied and the rate is a guess that could change the answer: either the basic "
                               "changed in the 8 weeks before the leave (a pay rise?), so the most recent rate was used, or there "
                               "was no basic in those 8 weeks, so the latest basic seen was used (which may be a short or part week). "
                               "Check the rate with the employer and supply contract_weekly_basic",
    "no_basic_pay_found": "no contract basic was supplied and no basic pay appears anywhere before the leave, so the weekly basic "
                          "rate used is 0.00 and the recalculated figure is not reliable. Supply contract_weekly_basic",
    "latest_week_basic_differs_from_rate_used": "the latest week's basic differs from the rate used",
    "reference_week_basic_differs_from_contract": "basic in some reference weeks (weeks with basic pay) differs from the contract basic",
}


def unlisted_holiday_pay(workers):
    """{worker_id: [week endings with a holiday_pay row that is not in leave.csv]}, only for workers with leave."""
    out = {}
    for wid in sorted(workers):
        w = workers[wid]
        if not w.leave or w.worker_type == ROLLED_UP_TYPE:
            continue
        listed = {e.week_end for e in w.leave}
        weeks = sorted(d for d, p in w.history.items() if "holiday_pay" in p and d not in listed)
        if weeks:
            out[wid] = weeks
    return out


def ignored_contract_basic(workers):
    """[(worker_id, worker_type)] for workers not fixed_pay that were given a contract_weekly_basic, which is ignored."""
    return sorted((w, d.worker_type) for w, d in workers.items()
                  if d.worker_type != "fixed_pay" and d.contract_weekly_basic is not None)


def cannot_check(r):
    return "no_reference_weeks" in r["flags"]


ALWAYS_EXCEPTION_FLAGS = ("rate_inferred_ambiguous", "no_basic_pay_found")


def always_exception(r):
    """The weekly rate was a guess that could change the answer: never hidden, even when paid equals due."""
    return any(f in r["flags"] for f in ALWAYS_EXCEPTION_FLAGS)


def audit(workers, threshold=DEFAULT_THRESHOLD, include_flagged=False):
    """Return (all_rows, exceptions); each row is an engine row plus worker_id.

    Rows from the rolled-up pay check (irregular_rolled_up workers, report/rolled_up.py) have kind 'rolled_up'
    and follow the look-back rows. The look-back skips those workers' leave weeks: their holiday pay is paid
    as rolled-up pay in each wage packet, so the 52-week average does not apply to them.

    A row that cannot be checked (no reference weeks) is always an exception, never dropped. So is a row with
    rate_inferred_ambiguous or no_basic_pay_found (the rate was a guess), whatever the difference.
    """
    rows = []
    unlisted = unlisted_holiday_pay(workers)
    for wid in sorted(workers):
        w = workers[wid]
        if w.worker_type == ROLLED_UP_TYPE:
            continue
        for r in lookback(w.history, w.leave, worker_type=w.worker_type,
                          contract_weekly_basic=w.contract_weekly_basic,
                          leave_year_month=w.leave_year_start[0], leave_year_day=w.leave_year_start[1]):
            if any(leave_year_start_date(d, *w.leave_year_start) == r["leave_year_start"] and d < r["week_end"]
                   for d in unlisted.get(wid, ())):
                r["flags"].append("holiday_pay_week_not_in_leave_file")
            rows.append({"worker_id": wid, "first_week": w.first_week, **r})
    exceptions = [r for r in rows if cannot_check(r) or always_exception(r) or abs(r["difference"]) > threshold
                  or (include_flagged and r["flags"])]
    ru_rows, ru_exc = audit_rolled_up(workers, threshold)
    return rows + ru_rows, exceptions + ru_exc


def is_rolled_up(r):
    return r.get("kind") == "rolled_up"


def rolled_up_weeks_checked(ru_rows):
    """Distinct (worker, pay week) pairs among rolled-up rows: a week with both a rolled-up check row and a
    holiday_pay row counts once."""
    return len({(r["worker_id"], r["week_end"]) for r in ru_rows})


def split_rows(rows):
    """(look-back rows, rolled-up rows)."""
    return [r for r in rows if not is_rolled_up(r)], [r for r in rows if is_rolled_up(r)]


_md = md_escape
MAX_ROLLED_UP_TOTAL = 500    # detailed rolled-up sections in the whole report.md, all workers together
MAX_ROLLED_UP_SUMMARIES = 50  # per-worker 'and K more' lines; further workers share one line
MAX_ROLLED_UP_DETAILS = 20   # detailed report.md sections per rolled-up worker; exceptions.csv is always complete


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
    if is_rolled_up(r):
        due, diff = r["due"], r["difference"]
        direction = "rule_flag" if due is None else ("underpaid" if diff > 0 else "overpaid" if diff < 0 else "correct")
        return {"worker_id": _safe(r["worker_id"]), "leave_week": r["week_end"].isoformat(), "paid": f"{r['paid']:.2f}",
                "due": "" if due is None else f"{due:.2f}", "difference": "" if diff is None else f"{diff:.2f}",
                "direction": direction, "flags": _safe(";".join(r["flags"])), "ref_weeks_used": "",
                "ref_weeks_skipped": "", "ref_weeks_before_first_record": "", "average": "", "fixed_basic_rate": "",
                "check": CHECK_ROLLED_UP}
    n = r["working"]["normal"]
    blank = cannot_check(r)  # no reference weeks: any recalculated figure would be a fake under/overpayment
    return {"worker_id": _safe(r["worker_id"]), "leave_week": r["week_end"].isoformat(),
            "paid": f"{r['paid']:.2f}", "due": "" if blank else f"{r['due']:.2f}",
            "difference": "" if blank else f"{r['difference']:.2f}",
            "direction": _direction(r["difference"], r), "flags": _safe(";".join(r["flags"])),
            "ref_weeks_used": n["weeks_used"], "ref_weeks_skipped": _split_skipped(r)[1],
            "ref_weeks_before_first_record": _split_skipped(r)[0],
            "average": f"{n['average']:.2f}",
            "fixed_basic_rate": f"{n['current_basic']:.2f}" if "current_basic" in n else "", "check": CHECK_LOOKBACK}


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
                     f"Paid in the leave week: {_gbp(r['paid'])}. No recalculated figure is given (due and difference are blank in exceptions.csv).")
    else:
        lines.append(f"- Recalculated under these settings: {_gbp(r['due'])}. Paid in the leave week: {_gbp(r['paid'])}. "
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


def _ignored_basic_section(ignored):
    if not ignored:
        return []
    out = ["", "## Warning: contract_weekly_basic ignored", ""]
    if any(t == "variable_hours" for _, t in ignored):
        out += ["For variable_hours workers the contract_weekly_basic you gave is ignored: their rate is the "
                "52-week average. Set worker_type to fixed_pay if the contract rate should be used, or remove the value.", ""]
    if any(t == ROLLED_UP_TYPE for _, t in ignored):
        out += ["For irregular_rolled_up workers the contract_weekly_basic you gave is ignored: their rolled-up pay is "
                "checked as 12.07% of pay that counts, so a weekly basic is not used.", ""]
    return out + [f"- {_md(wid)}: contract_weekly_basic ignored ({t})" for wid, t in ignored]


def _holiday_paid_section(held):
    if not held:
        return []
    out = ["", "## Warning: holiday_pay recorded for an irregular_rolled_up worker", "",
           "These workers are paid holiday pay rolled up into each wage packet, but these weeks also carry a holiday_pay "
           "row. That may be a second payment of the same holiday pay, or the worker may not be on rolled-up pay. "
           "Each week is listed in exceptions.csv with the flag `holiday_pay_paid_to_rolled_up_worker`; "
           "it is not recalculated.", ""]
    return out + [f"- {_md(wid)}: {len(ws)} week(s): {', '.join(_week_ranges(ws))}" for wid, ws in held.items()]


def _stray_section(stray):
    if not stray:
        return []
    out = ["", "## Warning: rolled-up holiday pay for a worker not set as irregular_rolled_up", "",
           "These workers have rolled_up_holiday_pay rows but their worker_type is not irregular_rolled_up, so the "
           "rolled-up pay was not checked and is not counted as normal pay, basic pay or holiday pay. "
           "Set worker_type to irregular_rolled_up in workers.csv if they are paid rolled-up holiday pay, then re-run.", ""]
    return out + [f"- {_md(wid)}: {len(ws)} week(s): {', '.join(_week_ranges(ws))}" for wid, ws in stray.items()]


def _rolled_up_notes(skipped_leave, idle=None, leave_missing=None):
    out = []
    if skipped_leave:
        n = sum(skipped_leave.values())
        out += ["", "## Note: leave weeks of irregular_rolled_up workers", "",
                f"{n} leave week(s) listed in leave.csv for {len(skipped_leave)} irregular_rolled_up worker(s) "
                "were not re-audited by the 52-week look-back, because their holiday pay is paid as rolled-up pay in "
                "each wage packet. Their pay weeks are checked under the rolled-up rules above: "
                + ", ".join(f"{_md(w)} ({c})" for w, c in skipped_leave.items()) + "."]
    if idle:
        out += ["", "## Note: irregular_rolled_up workers with nothing to check", "",
                f"{len(idle)} irregular_rolled_up worker(s) were loaded but had no week that the rolled-up check applies to "
                "(no pay that counts, or pay only in leave years starting before 1 April 2024 with no rolled_up_holiday_pay, and no holiday_pay row): "
                + ", ".join(_md(w) for w in idle) + ". They were not skipped by mistake; confirm their history is complete."]
    if leave_missing:
        out += ["", "## Warning: leave week of an irregular_rolled_up worker missing from history", "",
                "These leave.csv weeks have no payroll row in history.csv. Rolled-up workers' leave weeks are not "
                "re-audited, so check the export is complete.", ""]
        out += [f"- {_md(wid)}: {len(ws)} week(s): {', '.join(_week_ranges(ws))}" for wid, ws in leave_missing.items()]
    return out


def _exception_sections(exceptions):
    """Detailed sections: all look-back exceptions; rolled-up ones at most MAX_ROLLED_UP_DETAILS per worker and
    MAX_ROLLED_UP_TOTAL overall. Left-out ones get an 'and K more' line for the first MAX_ROLLED_UP_SUMMARIES workers,
    then one combined line. exceptions.csv is never capped."""
    out, shown, more, total = [], {}, {}, 0
    for r in exceptions:
        if not is_rolled_up(r):
            out.append(explain(r))
            continue
        wid = r["worker_id"]
        if shown.get(wid, 0) < MAX_ROLLED_UP_DETAILS and total < MAX_ROLLED_UP_TOTAL:
            shown[wid] = shown.get(wid, 0) + 1
            total += 1
            out.append(explain_rolled_up(r, _gbp, _md))
        else:
            more.setdefault(wid, []).append(r)
    items = list(more.items())
    for wid, rs in items[:MAX_ROLLED_UP_SUMMARIES]:
        flags = Counter(f for r in rs for f in r["flags"])
        detail = f" ({', '.join(f'{_md(f)}: {c}' for f, c in sorted(flags.items()))})" if flags else ""
        out.append(f"### {_md(wid)}: and {len(rs)} more rolled-up pay exception(s){detail}\n\n"
                   f"The rest are not written out above (at most {MAX_ROLLED_UP_DETAILS} per worker and {MAX_ROLLED_UP_TOTAL} in the whole report). All of them, "
                   f"{', '.join(_week_ranges(sorted({r['week_end'] for r in rs})))}, are in exceptions.csv.\n")
    rest = items[MAX_ROLLED_UP_SUMMARIES:]
    if rest:
        out.append(f"### and {sum(len(rs) for _, rs in rest)} more rolled-up pay exception(s) for {len(rest)} further worker(s)\n\n"
                   "Left out of this report to keep it readable. Every exception is in exceptions.csv.\n")
    return out


MAX_LEAVE_YEAR_WORKERS = 20   # workers named in the 'Leave years' summary line

_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")


def _leave_years_line(starts):
    """Summary line naming workers whose leave year does not start on 1 April, or None when there are none.

    starts maps worker_id -> (month, day). When every worker uses the default the line is left out, so reports
    without a custom leave_year_start are unchanged."""
    odd = sorted((w, s) for w, s in (starts or {}).items() if s != (4, 1))
    if not odd:
        return None
    shown = [f"{_md(w)}: {s[1]} {_MONTHS[s[0] - 1]}" for w, s in odd[:MAX_LEAVE_YEAR_WORKERS]]
    more = len(odd) - MAX_LEAVE_YEAR_WORKERS
    if more > 0:
        shown.append(f"and {more} more")
    return "- Leave years: 1 April unless set; " + ", ".join(shown)


def write_outputs(out_dir, rows, exceptions, threshold=DEFAULT_THRESHOLD, gaps=None, workers_loaded=None, unlisted=None,
                  ignored_basic=None, stray_rolled=None, skipped_leave=None, holiday_paid=None,
                  rolled_up_idle_workers=None, rolled_up_leave_missing_weeks=None, leave_year_starts=None):
    rows, ru_rows = split_rows(rows)
    lb_exc, ru_exc = split_rows(exceptions)
    under = [r for r in rows if not cannot_check(r) and r["difference"] > threshold]
    over = [r for r in rows if not cannot_check(r) and r["difference"] < -threshold]
    unchecked = [r for r in rows if cannot_check(r)]
    flagged = sorted({r["worker_id"] for r in rows if r["flags"]})
    with_leave = len({r["worker_id"] for r in rows})
    md = [f"# Holiday pay look-back audit", "", f"**{DISCLAIMER}**", "",
          "Every figure here is recalculated under these settings. It is a calculation to check, not a finding.", "",
          "## Summary", ""]
    if workers_loaded is not None:
        md.append(f"- Workers loaded: {workers_loaded}")
    md += [f"- Workers with leave: {with_leave}",
           f"- Leave weeks checked: {len(rows)}",
           f"- Exceptions (difference over {_gbp(threshold)}, or cannot be checked): {len(lb_exc)}",
           f"- Leave weeks that could not be checked: {len(unchecked)}",
           f"- Underpayments: {len(under)}, total underpaid {_gbp(sum((r['difference'] for r in under), Decimal(0)))}",
           f"- Overpayments: {len(over)}, total overpaid {_gbp(sum((-r['difference'] for r in over), Decimal(0)))}",
           f"- Workers with flags: {len(flagged)}" + (f" ({', '.join(_md(f) for f in flagged)})" if flagged else ""),
           ]
    leave_years = _leave_years_line(leave_year_starts)
    if leave_years:
        md.append(leave_years)
    if gaps is not None:
        md.append(f"- Workers with weeks missing from the export: {len(gaps)}")
    if unlisted:
        md.append(f"- Workers with holiday pay outside leave.csv: {len(unlisted)}")
    if ignored_basic:
        md.append(f"- Workers whose contract_weekly_basic was ignored: {len(ignored_basic)}")
    if ru_rows or ru_exc:
        paid_ru = [r for r in ru_exc if r["flags"] == [HOLIDAY_PAID]]
        flagged_ru = [r for r in ru_exc if r["flags"] and r["flags"] != [HOLIDAY_PAID]]
        md += [f"- Rolled-up pay weeks checked (worker-weeks, each counted once): {rolled_up_weeks_checked(ru_rows)}",
               f"- Rolled-up pay exceptions: {len(ru_exc)} ({len(flagged_ru)} rule flags, "
               f"{len(ru_exc) - len(flagged_ru) - len(paid_ru)} differences from 12.07% of pay that counts, "
               f"{len(paid_ru)} holiday_pay week(s) paid to a rolled-up worker)"]
    if holiday_paid:
        md.append(f"- Workers with holiday_pay recorded while on rolled-up pay: {len(holiday_paid)}")
    if stray_rolled:
        md.append(f"- Workers with rolled-up pay but not set as irregular_rolled_up: {len(stray_rolled)}")
    md += ["", "## Exceptions", ""]
    md += _exception_sections(exceptions) or ["None.\n"]
    md += _gap_section(gaps)
    md += _unlisted_section(unlisted)
    md += _ignored_basic_section(ignored_basic)
    md += _rolled_up_notes(skipped_leave, rolled_up_idle_workers, rolled_up_leave_missing_weeks)
    md += _holiday_paid_section(holiday_paid)
    md += _stray_section(stray_rolled)

    def write_csv(fh):
        w = csv.DictWriter(fh, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(_csv_row(r) for r in exceptions)

    _atomic_write_pair(out_dir, [
        ("exceptions.csv", write_csv, {"newline": "", "encoding": "utf-8"}),
        ("report.md", lambda fh: fh.write("\n".join(md)), {"encoding": "utf-8"})])
