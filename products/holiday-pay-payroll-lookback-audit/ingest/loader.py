"""Read the canonical CSVs (see FORMAT.md). All problems are collected, never just the first."""
import csv
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from engine import CATEGORIES, LeaveEntry
from engine.elements import normal_pay
from engine.lookback import INPUT_WORKER_TYPES as WORKER_TYPES

HISTORY_COLS = (("worker_id", "week_ending", "element_category", "amount"), ())
LEAVE_COLS = (("worker_id", "week_ending"), ("weeks",))
WORKER_COLS = (("worker_id", "worker_type"), ("contract_weekly_basic", "leave_year_start"))
DEFAULT_LEAVE_YEAR_START = (4, 1)
_MMDD = re.compile(r"[0-9]{2}-[0-9]{2}")

_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MONEY = re.compile(r"^[0-9]{1,9}(\.[0-9]{1,2})?$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
# NI shape on a value with every separator removed: two prefix letters, six digits, optional suffix A-D.
# HMRC prefix rules: first letter not D F I Q U V; second not D F I O Q U V; BG GB NK KN TN NT ZZ never issued.
# QQ (the HMRC example prefix) is deliberately still treated as NI-shaped, so documentation examples are refused.
_NI_SHAPE = re.compile(r"^(?:QQ|(?![DFIQUV])[A-Z](?![DFIOQUV])[A-Z])[0-9]{6}[A-D]?$")
_NI_NEVER = ("BG", "GB", "NK", "KN", "TN", "NT", "ZZ")
_DATE_ID = re.compile(r"^(?:[0-9]{4}[-_.][0-9]{2}[-_.][0-9]{2}|[0-9]{2}[-_.][0-9]{2}[-_.][0-9]{4})$")
MIN_DATE, MAX_DATE = date(2000, 1, 1), date(2100, 12, 31)
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
    leave_year_start: tuple = DEFAULT_LEAVE_YEAR_START   # (month, day) the worker's leave year starts
    first_week: Optional[date] = None   # earliest week_ending in the history file
    first_line: int = 0                 # history.csv line of the worker's first row


def _looks_like_ni(wid):
    """True if the id, or any run of its separator-delimited parts, has the shape of an NI number.

    Separators are anything that is not a letter or digit. Whole-value matching on each run of parts catches
    'QQ.12.34.56.C', 'QQ_12_34_56_C', 'QQ123456' (no suffix) and 'EMP-QQ123456C' (NI after a prefix part), while
    'EMP100234' or 'EMP100234A' (an alphabetic prefix glued to the digits) are not NI-shaped and stay allowed.
    """
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", wid.upper()) if p]
    for i in range(len(parts)):
        for j in range(i + 1, len(parts) + 1):
            c = "".join(parts[i:j])
            if len(c) > 9:      # an NI number has at most 9 characters; keeps the scan linear in the input
                break
            if _NI_SHAPE.match(c) and c[:2] not in _NI_NEVER:
                return True
    return False


def mask_id(wid):
    """Worker IDs in messages: first 2 characters then ***, never the full ID."""
    return f"{str(wid)[:2]}***"


_mask_id = mask_id   # older internal name


_NAME_LIKE = re.compile(r"^[A-Za-z]{2,}(?:[._-][A-Za-z]{2,})+$")


def name_like_id_warnings(workers):
    """Non-fatal G8 warnings: worker_ids made only of letters joined by '.', '_' or '-' (john.smith) look like names.
    IDs are masked; the check is a hint, not a guarantee (JSmith1990 is not caught). Identical masked warnings are
    made distinguishable by the line of the worker's first history row."""
    out = []
    for wid in sorted(workers):
        if _NAME_LIKE.match(wid):
            line = getattr(workers[wid], "first_line", 0)
            where = f", first row at history line {line}" if line else ""
            out.append(f"warning: worker_id {_mask_id(wid)} ({len(wid)} chars{where}) looks like a person's name. Use a pseudonymous payroll ID")
    return out


def excluded_week_with_pay(workers):
    """{worker_id: [week_ending]} for weeks carrying an excluded_week marker AND pay that counts (the engine's own
    normal_pay test: basic, regular_overtime, commission, allowance). The engine uses such a week; this only reports it."""
    out = {}
    for wid in sorted(workers):
        weeks = [d for d, cats in sorted(workers[wid].history.items())
                 if "excluded_week" in cats and normal_pay(cats) > 0]
        if weeks:
            out[wid] = weeks
    return out


def _mask(v):
    """Never echo a raw cell: first 2 characters and the length only."""
    v = str(v)
    clean = "".join(c for c in v if unicodedata.category(c) != "Cf")
    note = ", invisible characters removed" if clean != v else ""
    return f"'{clean[:2]}...' ({len(clean)} chars{note})"


def _header_hint(pos):
    """A header cell that is not a known column name is never echoed: a file with its header row deleted would
    otherwise print the first data row (worker id, date, amount)."""
    return f"column {pos} is not a recognised header; the file may be missing its header row"


def _is_personal_header(h: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", h.lower())
    return n in ("ni", "dob") or any(p in n for p in _PERSONAL_PARTS)


def _bad_utf8_line(path):
    """1-based line of the first byte sequence that is not valid UTF-8, or 0 if it cannot be found."""
    try:
        with open(path, "rb") as fh:
            for n, raw in enumerate(fh, 1):
                try:
                    raw.decode("utf-8")
                except UnicodeDecodeError:
                    return n
    except OSError:
        pass
    return 0


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
            for pos, c in enumerate(header, 1):
                if _is_personal_header(c):
                    issues.append(Issue(name, 1, f"column {pos} looks like personal data; use pseudonymous IDs only. Refused"))
                    bad = True
                elif c not in required + optional:
                    issues.append(Issue(name, 1, _header_hint(pos)))
                    bad = True
            for c in required:
                if c not in header:
                    issues.append(Issue(name, 1, f"missing column '{c}'"))
                    bad = True
            for c, n in Counter(header).items():
                if n > 1 and c in required + optional:
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
    except UnicodeDecodeError:
        issues.append(Issue(name, _bad_utf8_line(path), "the file is not valid UTF-8; save the file as UTF-8 (CSV UTF-8 in Excel)"))
        return []
    except OSError as e:
        issues.append(Issue(name, 0, f"cannot read file: {e}"))
        return []
    except csv.Error as e:
        issues.append(Issue(name, reader.line_num, f"malformed CSV: {e}"))
        return []


def _worker_id(name, line, row, issues):
    wid = row["worker_id"]
    if not wid:
        issues.append(Issue(name, line, "worker_id is empty"))
    elif _looks_like_ni(wid) or _DATE_ID.match(wid):
        issues.append(Issue(name, line, "worker_id looks like a National Insurance number or a date. Refused; use a pseudonymous payroll ID"))
    elif not _ID.match(wid):
        issues.append(Issue(name, line, "worker_id must be 1-64 ASCII letters, digits, '_', '.' or '-', starting with a letter or digit"))
    else:
        return wid
    return None


def _date(name, line, row, issues):
    v = row["week_ending"]
    if _DATE.fullmatch(v):
        try:
            d = date.fromisoformat(v)
        except ValueError:
            d = None
        if d is not None:
            if MIN_DATE <= d <= MAX_DATE:
                return d
            issues.append(Issue(name, line, f"week_ending is outside the accepted range {MIN_DATE} to {MAX_DATE}; check for a typo in the year"))
            return None
    issues.append(Issue(name, line, f"week_ending {_mask(v)} is not a valid YYYY-MM-DD date"))
    return None


def _amount(name, line, col, v, issues):
    if _MONEY.match(v):
        return Decimal(v)
    issues.append(Issue(name, line, f"{col} {_mask(v)} must be a plain non-negative number: up to 9 digits and 2 decimal places (no NaN, Infinity, signs, exponents or separators)"))
    return None


def _leave_year_start_value(v):
    """(month, day) for a real MM-DD calendar date, else None. 02-29 is refused: the start must exist every year."""
    if not _MMDD.fullmatch(v):
        return None
    m, d = int(v[:2]), int(v[3:])
    try:
        date(2023, m, d)     # 2023 is not a leap year, so 02-29 fails
    except ValueError:
        return None
    return (m, d)


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
        if cat == "statutory":
            issues.append(Issue(hname, line, "element_category 'statutory' is no longer accepted: it reveals why a week is excluded. "
                                "Replace it with 'excluded_week' and amount 0 (no reason, no amount)"))
        elif cat not in CATEGORIES:
            issues.append(Issue(hname, line, f"unknown element_category {_mask(cat)} (allowed: {', '.join(CATEGORIES)})"))
        amt = _amount(hname, line, "amount", row["amount"], issues)
        if cat == "excluded_week" and amt is not None and amt != 0:
            issues.append(Issue(hname, line, "excluded_week must have amount 0: the amount of a leave payment can reveal its reason"))
            amt = None
        if wid is None or d is None or cat not in CATEGORIES or amt is None:
            continue
        key = (wid, d, cat)
        if key in seen:
            issues.append(Issue(hname, line, f"duplicate row for {_mask_id(wid)} {d} {cat} (first at line {seen[key]})"))
            continue
        seen[key] = line
        w = workers.setdefault(wid, WorkerData(wid, first_line=line))
        w.history.setdefault(d, {})[cat] = amt
        hist_lines[wid].setdefault(d, line)

    # the worker's week pattern is the commonest weekday in their history
    pattern = {wid: Counter(d.weekday() for d in w.history).most_common(1)[0][0] for wid, w in workers.items()}
    for wid, w in workers.items():
        w.first_week = min(w.history)
        for d in w.history:
            if d.weekday() != pattern[wid]:
                issues.append(Issue(hname, hist_lines[wid][d], f"week_ending {d} is a {d:%A} but {_mask_id(wid)}'s weeks end on {_DAYS[pattern[wid]]}"))

    history_failed = any(i.file == hname for i in issues)
    lrows = _read(leave_path, LEAVE_COLS, issues)
    leave_empty = not lrows and not any(i.file == lname for i in issues)
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
                issues.append(Issue(lname, line, f"leave for worker '{_mask_id(wid)}' who has no payroll history"))
        elif d in leave_lines[wid]:
            issues.append(Issue(lname, line, f"duplicate leave week for {_mask_id(wid)} {d} (first at line {leave_lines[wid][d]})"))
        elif d.weekday() != pattern[wid]:
            issues.append(Issue(lname, line, f"week_ending {d} is a {d:%A} but {_mask_id(wid)}'s weeks end on {_DAYS[pattern[wid]]}"))
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
                issues.append(Issue(wname, line, f"duplicate settings for {_mask_id(wid)} (first at line {wseen[wid]})"))
                continue
            wseen[wid] = line
            if wid not in workers:
                issues.append(Issue(wname, line, f"settings for worker '{_mask_id(wid)}' who has no payroll history"))
                continue
            if row["worker_type"] not in WORKER_TYPES:
                issues.append(Issue(wname, line, f"worker_type {_mask(row['worker_type'])} must be one of {', '.join(WORKER_TYPES)}"))
            else:
                workers[wid].worker_type = row["worker_type"]
            lys = row.get("leave_year_start", "")
            if lys:
                parsed = _leave_year_start_value(lys)
                if parsed is None:
                    issues.append(Issue(wname, line, f"leave_year_start {_mask(lys)} must be a real calendar date as MM-DD (for example 01-01 or 04-01)"
                                        + ("; 02-29 is not accepted" if lys == "02-29" else "")))
                else:
                    workers[wid].leave_year_start = parsed
            basic = row.get("contract_weekly_basic", "")
            if basic:
                amt = _amount(wname, line, "contract_weekly_basic", basic, issues)
                if amt is not None and amt == 0 and workers[wid].worker_type == "fixed_pay":
                    issues.append(Issue(wname, line, f"contract_weekly_basic must be greater than 0 for a fixed_pay worker ({_mask_id(wid)}); leave it blank to infer the rate"))
                    amt = None
                workers[wid].contract_weekly_basic = amt

    # An empty leave.csv is allowed only for a firm whose every worker is irregular_rolled_up (T-130): otherwise
    # an empty export would silently hide look-back leave and unlisted holiday pay.
    if leave_empty and not (workers and all(w.worker_type == "irregular_rolled_up" for w in workers.values())):
        issues.append(Issue(lname, 0, "no data rows (a header-only leave.csv is accepted only when every worker in history is set as irregular_rolled_up in workers.csv)"))
    if issues:
        raise ValidationError(issues)
    return workers


_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
