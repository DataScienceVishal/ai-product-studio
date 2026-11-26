"""Read the canonical CSVs (see FORMAT.md). All problems are collected, never just the first."""
import csv
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from engine import CATEGORIES, LeaveEntry
from engine.lookback import WORKER_TYPES

HISTORY_COLS = (("worker_id", "week_ending", "element_category", "amount"), ())
LEAVE_COLS = (("worker_id", "week_ending"), ("weeks",))
WORKER_COLS = (("worker_id", "worker_type"), ("contract_weekly_basic",))

_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_MONEY = re.compile(r"^[0-9]{1,9}(\.[0-9]{1,2})?$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_NI = re.compile(r"^[A-Za-z]{2}[\s-]?[0-9]{2}[\s-]?[0-9]{2}[\s-]?[0-9]{2}[\s-]?[A-Za-z]$")
_PERSONAL_PARTS = ("name", "nino", "ninumber", "insurance", "birth", "dob", "address", "postcode",
                   "email", "phone", "mobile", "surname")


@dataclass(frozen=True)
class Issue:
    file: str
    line: int          # 0 = whole file / header-level
    reason: str

    def __str__(self):
        return f"{self.file}:{self.line}: {self.reason}" if self.line else f"{self.file}: {self.reason}"


class ValidationError(Exception):
    def __init__(self, issues: List[Issue]):
        self.issues = issues
        super().__init__(f"{len(issues)} validation error(s)")


@dataclass
class WorkerData:
    worker_id: str
    history: Dict[date, dict] = field(default_factory=dict)
    leave: List[LeaveEntry] = field(default_factory=list)
    worker_type: str = "variable_hours"
    contract_weekly_basic: Optional[Decimal] = None
    first_week: Optional[date] = None   # earliest week_ending in the history file


def _is_personal_header(h: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", h.lower())
    return n in ("ni", "dob") or any(p in n for p in _PERSONAL_PARTS)


def _read(path, spec, issues):
    """Return [(line_no, {col: value})]; header problems are reported and give []."""
    name = os.path.basename(path)
    required, optional = spec
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if header is None or not any(c.strip() for c in header):
                issues.append(Issue(name, 0, "file is empty"))
                return []
            header = [c.strip() for c in header]
            bad = False
            for c in header:
                if _is_personal_header(c):
                    issues.append(Issue(name, 1, f"column '{c}' looks like personal data; use pseudonymous IDs only. Refused"))
                    bad = True
                elif c not in required + optional:
                    issues.append(Issue(name, 1, f"unexpected column '{c}'"))
                    bad = True
            for c in required:
                if c not in header:
                    issues.append(Issue(name, 1, f"missing column '{c}'"))
                    bad = True
            for c, n in Counter(header).items():
                if n > 1:
                    issues.append(Issue(name, 1, f"duplicate column '{c}'"))
                    bad = True
            if bad:
                return []
            rows = []
            for rec in reader:
                if not rec or not any(c.strip() for c in rec):
                    continue
                if len(rec) != len(header):
                    issues.append(Issue(name, reader.line_num, f"expected {len(header)} fields, found {len(rec)}"))
                    continue
                rows.append((reader.line_num, dict(zip(header, (c.strip() for c in rec)))))
            return rows
    except (OSError, UnicodeDecodeError) as e:
        issues.append(Issue(name, 0, f"cannot read file: {e}"))
        return []
    except csv.Error as e:
        issues.append(Issue(name, reader.line_num, f"malformed CSV: {e}"))
        return []


def _worker_id(name, line, row, issues):
    wid = row["worker_id"]
    if not wid:
        issues.append(Issue(name, line, "worker_id is empty"))
    elif _NI.match(wid):
        issues.append(Issue(name, line, "worker_id looks like a National Insurance number. Refused; use a pseudonymous payroll ID"))
    elif not _ID.match(wid):
        issues.append(Issue(name, line, "worker_id must be 1-64 letters, digits, '_', '.' or '-', starting with a letter or digit"))
    else:
        return wid
    return None


def _date(name, line, row, issues):
    v = row["week_ending"]
    if _DATE.match(v):
        try:
            return date.fromisoformat(v)
        except ValueError:
            pass
    issues.append(Issue(name, line, f"week_ending '{v}' is not a valid YYYY-MM-DD date"))
    return None


def _amount(name, line, col, v, issues):
    if _MONEY.match(v):
        return Decimal(v)
    issues.append(Issue(name, line, f"{col} '{v[:30]}' must be a plain non-negative number: up to 9 digits and 2 decimal places (no NaN, Infinity, signs, exponents or separators)"))
    return None


def load_workers(history_path, leave_path, workers_path=None) -> Dict[str, WorkerData]:
    """Return {worker_id: WorkerData} or raise ValidationError carrying every issue found."""
    issues: List[Issue] = []
    hname, lname = os.path.basename(history_path), os.path.basename(leave_path)
    workers: Dict[str, WorkerData] = {}
    hist_lines, leave_lines = defaultdict(dict), defaultdict(dict)   # id -> {date: line}
    seen = {}

    hrows = _read(history_path, HISTORY_COLS, issues)
    if not hrows and not any(i.file == hname for i in issues):
        issues.append(Issue(hname, 0, "no data rows"))
    for line, row in hrows:
        wid, d = _worker_id(hname, line, row, issues), _date(hname, line, row, issues)
        cat = row["element_category"]
        if cat not in CATEGORIES:
            issues.append(Issue(hname, line, f"unknown element_category '{cat}' (allowed: {', '.join(CATEGORIES)})"))
        amt = _amount(hname, line, "amount", row["amount"], issues)
        if wid is None or d is None or cat not in CATEGORIES or amt is None:
            continue
        key = (wid, d, cat)
        if key in seen:
            issues.append(Issue(hname, line, f"duplicate row for {wid} {d} {cat} (first at line {seen[key]})"))
            continue
        seen[key] = line
        w = workers.setdefault(wid, WorkerData(wid))
        w.history.setdefault(d, {})[cat] = amt
        hist_lines[wid].setdefault(d, line)

    # the worker's week pattern is the commonest weekday in their history
    pattern = {wid: Counter(d.weekday() for d in w.history).most_common(1)[0][0] for wid, w in workers.items()}
    for wid, w in workers.items():
        w.first_week = min(w.history)
        for d in w.history:
            if d.weekday() != pattern[wid]:
                issues.append(Issue(hname, hist_lines[wid][d], f"week_ending {d} is a {d:%A} but {wid}'s weeks end on {_DAYS[pattern[wid]]}"))

    history_failed = any(i.file == hname for i in issues)
    lrows = _read(leave_path, LEAVE_COLS, issues)
    if not lrows and not any(i.file == lname for i in issues):
        issues.append(Issue(lname, 0, "no data rows"))
    for line, row in lrows:
        wid, d = _worker_id(lname, line, row, issues), _date(lname, line, row, issues)
        weeks = _amount(lname, line, "weeks", row.get("weeks") or "1", issues)
        if weeks is not None and not 0 < weeks <= 1:
            issues.append(Issue(lname, line, "weeks must be greater than 0 and at most 1 (one row per leave week)"))
            weeks = None
        if wid is None or d is None or weeks is None:
            continue
        if wid not in workers:
            if not history_failed:   # otherwise this is just noise on top of the real history error
                issues.append(Issue(lname, line, f"leave for worker '{wid}' who has no payroll history"))
        elif d in leave_lines[wid]:
            issues.append(Issue(lname, line, f"duplicate leave week for {wid} {d} (first at line {leave_lines[wid][d]})"))
        elif d.weekday() != pattern[wid]:
            issues.append(Issue(lname, line, f"week_ending {d} is a {d:%A} but {wid}'s weeks end on {_DAYS[pattern[wid]]}"))
        else:
            leave_lines[wid][d] = line
            workers[wid].leave.append(LeaveEntry(d, weeks))

    if workers_path:
        wname, wseen = os.path.basename(workers_path), {}
        for line, row in _read(workers_path, WORKER_COLS, issues):
            wid = _worker_id(wname, line, row, issues)
            if wid is None:
                continue
            if wid in wseen:
                issues.append(Issue(wname, line, f"duplicate settings for {wid} (first at line {wseen[wid]})"))
                continue
            wseen[wid] = line
            if wid not in workers:
                issues.append(Issue(wname, line, f"settings for worker '{wid}' who has no payroll history"))
                continue
            if row["worker_type"] not in WORKER_TYPES:
                issues.append(Issue(wname, line, f"worker_type '{row['worker_type']}' must be one of {', '.join(WORKER_TYPES)}"))
            else:
                workers[wid].worker_type = row["worker_type"]
            basic = row.get("contract_weekly_basic", "")
            if basic:
                workers[wid].contract_weekly_basic = _amount(wname, line, "contract_weekly_basic", basic, issues)

    if issues:
        raise ValidationError(issues)
    return workers


_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
