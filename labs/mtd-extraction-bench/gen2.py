"""Full-benchmark generator: 4 fictional bank layouts (+ parsers), 3 personas with ambiguous lines.
All names fictional, no real branding. Deterministic extraction (no model) for PDF/CSV/xlsx."""
import csv, json, random, re, subprocess
from datetime import date, timedelta
from pathlib import Path
import gen

# (template, category, (lo, hi), sign, ambiguous?)
COMMON = [
    ("MONTHLY ACCOUNT FEE", "interest_bank_charges", (7, 7), -1, False),
    ("OVERDRAFT INTEREST", "interest_bank_charges", (3, 14), -1, False),
    ("DD PENNYWORTH ACCOUNTANTS", "professional_fees", (45, 45), -1, False),
    ("DD TELLOWAY MOBILE", "phone_office", (22, 22), -1, True),   # personal+business phone
    ("CARD PAYMENT TO GREENLEAF SUPERMARKET", "drawings_personal", (12, 95), -1, False),
    ("CARD PAYMENT TO STARLIGHT CINEMAS", "drawings_personal", (9, 30), -1, False),
    ("DD STREAMBOX SUBSCRIPTION", "drawings_personal", (10, 10), -1, False),
    ("STANDING ORDER TO OWNER PERSONAL A/C", "drawings_personal", (300, 600), -1, False),
    ("TRANSFER TO SAVINGS 8841", "transfer", (100, 400), -1, False),
    ("TRANSFER FROM SAVINGS 8841", "transfer", (100, 300), 1, False),
]
PERSONAS = {
    "tradesperson": {"label": "self-employed joiner (van, workshop unit, buys timber and trade parts)", "merchants": [
        ("BACS FROM {c} LTD INV{n}", "turnover", (180, 1400), 1, False),
        ("CARD PAYMENT TO BRICKWELL TIMBER SUPPLY", "cost_of_goods", (40, 380), -1, False),
        ("CARD PAYMENT TO TOPMART HARDWARE", "cost_of_goods", (8, 140), -1, True),  # DIY store: job materials or home
        ("DD HARLOW FUEL STATION {n}", "car_van_travel", (30, 85), -1, True),       # van fuel, some private
        ("CARD PAYMENT TO MERIDIAN PARKING", "car_van_travel", (3, 18), -1, False),
        ("DD ELMSTEAD UNITS RENT", "premises", (350, 350), -1, False),
        ("DD WESTFIELD POWER", "premises", (60, 140), -1, True),                    # home or unit electricity
        ("CARD PAYMENT TO QUICKFIX TYRES", "repairs", (25, 190), -1, True),
        ("CASH WITHDRAWAL ATM {n}", "drawings_personal", (20, 200), -1, True),
        ("CARD PAYMENT TO TRADEBODY SUBSCRIPTION", "other_expenses", (12, 60), -1, True),
    ] + COMMON},
    "consultant": {"label": "self-employed IT consultant working from a spare room at home", "merchants": [
        ("BACS FROM {c} LTD INV{n}", "turnover", (600, 3200), 1, False),
        ("FASTER PAYMENT {p} REF{n}", "turnover", (200, 900), 1, False),
        ("DD HOMEFIELD BROADBAND", "phone_office", (34, 34), -1, True),             # home broadband share
        ("DD WESTFIELD POWER", "premises", (60, 140), -1, True),                    # home electricity: use-of-home
        ("CARD PAYMENT TO CLOUDHAVEN SOFTWARE", "phone_office", (9, 60), -1, False),
        ("CARD PAYMENT TO RAILLINK TICKETS", "car_van_travel", (14, 96), -1, False),
        ("CARD PAYMENT TO CAFE LUNA", "other_expenses", (4, 28), -1, True),         # client meeting or lunch
        ("CARD PAYMENT TO PAPERBOX STATIONERY", "phone_office", (6, 45), -1, False),
        ("CARD PAYMENT TO NORTHSTAR ELECTRONICS", "other_expenses", (25, 480), -1, True),  # laptop or personal
        ("DD PROFESSIONAL INSTITUTE FEE", "professional_fees", (15, 15), -1, False),
        ("CASH WITHDRAWAL ATM {n}", "drawings_personal", (20, 150), -1, True),
        ("CARD PAYMENT TO BRIGHTADS ONLINE", "advertising", (15, 90), -1, False),
    ] + COMMON},
    "market_stall": {"label": "self-employed market-stall seller of handmade candles and gifts (cash and card takings)", "merchants": [
        ("CASH DEPOSIT MARKET TAKINGS", "turnover", (90, 520), 1, False),
        ("CARD SETTLEMENT SPARKPAY {n}", "turnover", (40, 330), 1, False),
        ("CARD PAYMENT TO WAXWORKS WHOLESALE", "cost_of_goods", (40, 260), -1, False),
        ("CARD PAYMENT TO JARBARN PACKAGING", "cost_of_goods", (12, 90), -1, False),
        ("CARD PAYMENT TO MARKETHALL PITCH FEE", "premises", (25, 25), -1, False),
        ("DD HARLOW FUEL STATION {n}", "car_van_travel", (25, 70), -1, True),
        ("CASH WITHDRAWAL FLOAT {n}", "transfer", (40, 100), -1, True),             # till float: not an expense
        ("CASH WITHDRAWAL ATM {n}", "drawings_personal", (20, 120), -1, True),
        ("CARD PAYMENT TO CRAFTFAYRE ONLINE", "advertising", (10, 45), -1, False),
        ("CARD PAYMENT TO TOPMART HARDWARE", "other_expenses", (5, 60), -1, True),
        ("CARD PAYMENT TO CAFE LUNA", "drawings_personal", (4, 20), -1, True),
        ("DD STALLSURE INSURANCE", "other_expenses", (19, 19), -1, False),
    ] + COMMON},
}
CLIENTS = gen.CLIENTS
PEOPLE = gen.PEOPLE


def make_txns(persona, seed, n=32, start=date(2026, 4, 6), opening=2450.00):
    r = random.Random(seed)
    M = PERSONAS[persona]["merchants"]
    picks = r.sample(range(len(M)), len(M))[:n] + [r.choice(range(len(M))) for _ in range(max(0, n - len(M)))]
    picks = picks[:n]
    days = sorted(r.randint(0, 88) for _ in picks)
    bal, out = opening, []
    for d, idx in zip(days, picks):
        tpl, cat, (lo, hi), sign, amb = M[idx]
        desc = tpl.format(c=r.choice(CLIENTS), p=r.choice(PEOPLE), n=r.randint(1000, 9999))
        amt = round(sign * (r.uniform(lo, hi) if lo != hi else lo), 2)
        bal = round(bal + amt, 2)
        out.append({"date": (start + timedelta(days=d)).isoformat(), "description": desc, "amount": amt,
                    "balance": bal, "category": cat, "ambiguous": amb})
    return out, opening


# ---------------------------------------------------------------- layouts: writers
def _fmt_money(x):
    return f"{abs(x):,.2f}"


def _pdf(path, title, header_lines, cols, rows, footer="Synthetic test document. Not a real bank statement."):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4
    c.setFont("Helvetica-Bold", 15); c.drawString(40, H - 50, title)
    c.setFont("Helvetica", 9)
    y = H - 70
    for h in header_lines:
        c.drawString(40, y, h); y -= 13
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    for x, h, _ in cols:
        c.drawString(x, y, h)
    y -= 14; c.setFont("Helvetica", 9)
    for row in rows:                      # row = list of cell strings (or list of lines per cell)
        nlines = max(len(cell) if isinstance(cell, list) else 1 for cell in row)
        for (x, _, align), cell in zip(cols, row):
            lines = cell if isinstance(cell, list) else [cell]
            for k, ln in enumerate(lines):
                (c.drawRightString if align == "r" else c.drawString)(x, y - 11 * k, ln)
        y -= 11 * nlines + 4
        if y < 60:
            c.showPage(); c.setFont("Helvetica", 9); y = H - 60
    c.setFont("Helvetica-Oblique", 7); c.drawString(40, 40, footer)
    c.save()


def split_desc(d):
    w = d.split()
    if len(w) < 4:
        return [d]
    k = max(2, len(w) // 2 + 1)
    return [" ".join(w[:k]), " ".join(w[k:])]


def write_layout(layout, path, txns, opening, persona_name="SAMPLE TRADER"):
    hdr = [f"Account holder: {persona_name} (fictional)   Sort code 00-00-00   Acc 00000000",
           f"Period {gen.fmt_d(txns[0]['date'])} to {gen.fmt_d(txns[-1]['date'])}"]
    D = date.fromisoformat
    if layout == "fenwick":      # DD/MM/YY, 2-line details, one amount col + CR/DR balance
        cols = [(40, "Date", "l"), (100, "Details", "l"), (440, "Amount", "r"), (540, "Balance", "r")]
        rows = [["", ["BROUGHT FORWARD"], "", f"{_fmt_money(opening)} CR"]]
        for t in txns:
            b = t["balance"]
            rows.append([D(t["date"]).strftime("%d/%m/%y"), split_desc(t["description"]), _fmt_money(t["amount"]),
                         f"{_fmt_money(b)} {'CR' if b >= 0 else 'DR'}"])
        _pdf(path, "FENWICK & DALE BANK (fictional)", ["Current account statement"] + hdr, cols, rows)
    elif layout == "quillon":    # ISO date, signed amount, no balance
        cols = [(40, "Posted", "l"), (110, "Narrative", "l"), (520, "Amount GBP", "r")]
        rows = [[t["date"], t["description"], f"{t['amount']:+,.2f}"] for t in txns]
        _pdf(path, "QUILLON DIRECT (fictional)", ["Business account activity"] + hdr, cols, rows)
    elif layout == "tarn":       # '9 Apr' no year, out/in columns, balance
        cols = [(40, "Date", "l"), (95, "Transaction", "l"), (380, "Out", "r"), (450, "In", "r"), (540, "Balance", "r")]
        rows = [["", "Opening balance", "", "", _fmt_money(opening)]]
        for t in txns:
            a = t["amount"]
            rows.append([f"{D(t['date']).day} {D(t['date']).strftime('%b')}", t["description"],
                         _fmt_money(a) if a < 0 else "", _fmt_money(a) if a > 0 else "",
                         f"{t['balance']:,.2f}"])
        _pdf(path, "TARN BUILDING SOCIETY (fictional)", ["Business saver-current statement",
             "Tax year 2026/27: dates shown without year"] + hdr, cols, rows)
    elif layout == "corvid":     # ISO date, type code, trailing-minus debits, balance
        cols = [(40, "Date", "l"), (105, "Type", "l"), (145, "Description", "l"), (430, "Value", "r"), (540, "Balance", "r")]
        rows = [["", "", "OPENING", "", _fmt_money(opening)]]
        for t in txns:
            a = t["amount"]
            typ = "DD" if t["description"].startswith("DD ") else ("TFR" if "TRANSFER" in t["description"] else ("ATM" if "CASH W" in t["description"] else "POS"))
            rows.append([t["date"], typ, t["description"], f"{abs(a):,.2f}{'-' if a < 0 else '+'}", f"{t['balance']:,.2f}"])
        _pdf(path, "CORVID DIRECT BANKING (fictional)", ["Statement of account"] + hdr, cols, rows)
    else:
        raise ValueError(layout)


def write_csv_layout(layout, path, txns):
    D = date.fromisoformat
    with open(path, "w", newline="") as f:
        if layout == "csv_a":
            w = csv.writer(f); w.writerow(["Date", "Description", "Money Out", "Money In", "Balance"])
            for t in txns:
                a = t["amount"]
                w.writerow([D(t["date"]).strftime("%d/%m/%Y"), t["description"], f"{-a:.2f}" if a < 0 else "",
                            f"{a:.2f}" if a > 0 else "", f"{t['balance']:.2f}"])
        else:                    # csv_b: semicolon, ISO, signed amount, type, no balance, preamble rows
            f.write("Account export;fictional;generated for test\n")
            w = csv.writer(f, delimiter=";"); w.writerow(["Transaction Date", "Narrative", "Amount", "Type"])
            for t in txns:
                w.writerow([t["date"], t["description"], f"{t['amount']:.2f}", "CR" if t["amount"] > 0 else "DR"])


# ---------------------------------------------------------------- deterministic parsers (no model)
def _money(s):
    return float(s.replace(",", ""))


def parse_pdf(layout, path, opening):
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
    out, prev = [], opening
    year_for = lambda m: 2027 if m in (1, 2, 3) or (m == 4 and False) else 2026
    for line in txt.splitlines():
        if "Synthetic" in line or not line.strip():
            continue
        if layout == "fenwick":
            m = re.match(r"^(\d\d)/(\d\d)/(\d\d)\s+(.+?)\s{2,}([\d,]+\.\d\d)\s+([\d,]+\.\d\d) (CR|DR)\s*$", line)
            if m:
                bal = _money(m[6]) * (1 if m[7] == "CR" else -1)
                out.append({"date": f"20{m[3]}-{m[2]}-{m[1]}", "description": m[4].strip(), "amount": round(bal - prev, 2), "balance": bal})
                prev = bal
            elif out and re.match(r"^\s{8,}\S", line) and "BROUGHT" not in line and not re.search(r"\d\.\d\d", line):
                out[-1]["description"] += " " + line.strip()
        elif layout == "quillon":
            m = re.match(r"^(\d{4}-\d\d-\d\d)\s+(.+?)\s{2,}([+-][\d,]+\.\d\d)\s*$", line)
            if m:
                out.append({"date": m[1], "description": m[2].strip(), "amount": _money(m[3]), "balance": None})
        elif layout == "tarn":
            m = re.match(r"^(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(.+?)\s{2,}([\d,]+\.\d\d)\s+(-?[\d,]+\.\d\d)\s*$", line)
            if m:
                mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(m[2]) + 1
                y = 2027 if mon <= 3 else 2026
                bal = _money(m[5])
                out.append({"date": f"{y}-{mon:02d}-{int(m[1]):02d}", "description": m[3].strip(), "amount": round(bal - prev, 2), "balance": bal})
                prev = bal
        elif layout == "corvid":
            m = re.match(r"^(\d{4}-\d\d-\d\d)\s+(DD|POS|TFR|ATM)\s+(.+?)\s{2,}([\d,]+\.\d\d)([+-])\s+(-?[\d,]+\.\d\d)\s*$", line)
            if m:
                out.append({"date": m[1], "description": m[3].strip(), "amount": _money(m[4]) * (1 if m[5] == "+" else -1), "balance": _money(m[6])})
    return out


def parse_csv_layout(layout, path):
    out = []
    lines = Path(path).read_text().splitlines()
    if layout == "csv_a":
        for row in list(csv.reader(lines))[1:]:
            d, desc, o, i, b = row
            dd, mm, yy = d.split("/")
            out.append({"date": f"{yy}-{mm}-{dd}", "description": desc, "amount": -float(o) if o else float(i), "balance": float(b)})
    else:
        for row in list(csv.reader(lines, delimiter=";"))[2:]:
            out.append({"date": row[0], "description": row[1], "amount": float(row[2]), "balance": None})
    return out


def parse_year_less(ds):
    """'9 Apr' -> tax-year date. 'dd/mm/yy', 'dd.mm.yyyy' also."""
    ds = str(ds).strip()
    m = re.match(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})$", ds)
    if m:
        y = int(m[3]); y += 2000 if y < 100 else 0
        return f"{y}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.match(r"^(\d{1,2}) ([A-Za-z]{3})$", ds)
    if m:
        mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(m[2].lower()) + 1
        return f"{2027 if mon <= 3 else 2026}-{mon:02d}-{int(m[1]):02d}"
    return ds


def parse_sheet(path):
    path = Path(path)
    if path.suffix == ".xlsx":
        import openpyxl
        rows = [list(r) for r in openpyxl.load_workbook(path).active.iter_rows(values_only=True)][1:]
    else:
        rows = list(csv.reader(path.read_text().splitlines()))[1:]
    return [{"date": parse_year_less(r[0]), "description": str(r[1]), "amount": round(float(r[2]), 2), "balance": None}
            for r in rows if r and r[0]]


# ---------------------------------------------------------------- the 14-doc plan
PLAN = [  # name, kind, layout, persona, seed
    ("fenwick_trade", "pdf", "fenwick", "tradesperson", 101),
    ("quillon_consult", "pdf", "quillon", "consultant", 102),
    ("tarn_stall", "pdf", "tarn", "market_stall", 103),
    ("corvid_trade", "pdf", "corvid", "tradesperson", 104),
    ("fenwick_consult", "pdf", "fenwick", "consultant", 105),
    ("csv_a_trade", "csv", "csv_a", "tradesperson", 106),
    ("csv_b_stall", "csv", "csv_b", "market_stall", 107),
    ("sheet_trade", "xlsx", "sheet", "tradesperson", 108),
    ("sheet_consult", "xlsx", "sheet", "consultant", 109),
    ("scan_trade", "scan", "northbank", "tradesperson", 110),
    ("photo_consult", "photo", "northbank", "consultant", 111),
    ("scan_stall", "scan", "northbank", "market_stall", 112),
]
# 12 documents above; two more to reach 14: a second spreadsheet persona and a second csv layout
PLAN += [("sheet_stall", "xlsx", "sheet", "market_stall", 113), ("csv_a_consult", "csv", "csv_a", "consultant", 114)]
PRIOR_SEED_OFFSET = 1000   # prior-quarter data for the merchant-memory rules


def build(outdir):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, kind, layout, persona, seed in PLAN:
        tx, op = make_txns(persona, seed)
        if kind == "pdf":
            f = f"{name}.pdf"; write_layout(layout, out / f, tx, op)
        elif kind == "csv":
            f = f"{name}.csv"; write_csv_layout(layout, out / f, tx)
        elif kind == "xlsx":
            f = f"{name}.xlsx"
            rows = gen.write_messy_csv(out / f"_{name}.csv", tx, seed)
            (out / f"_{name}.csv").unlink(); gen.write_xlsx(out / f, rows)
            tx = [{**x, "bank_description": x["description"], "description": x["sheet_description"], "balance": None} for x in tx]
            op = None
        else:   # scan / photo: render PDF page then degrade
            tmp = out / f"_{name}"
            gen.write_pdf(out / f"_{name}.pdf", tx, op)
            subprocess.run(["pdftoppm", "-r", "110", "-png", "-singlefile", str(out / f"_{name}.pdf"), str(tmp)], check=True)
            from PIL import Image
            f = f"{name}.jpg"
            gen.degrade(Image.open(f"{tmp}.png"), "scan" if kind == "scan" else "photo", seed).save(out / f, quality=70)
            (out / f"_{name}.pdf").unlink(); Path(f"{tmp}.png").unlink()
        (out / f"{name}.truth.json").write_text(json.dumps({"file": f, "opening_balance": op, "persona": persona, "layout": layout, "kind": kind, "lines": tx}, indent=1))
        meta[name] = {"file": f, "kind": kind, "layout": layout, "persona": persona}
    return meta


def extract(name, datadir):
    """Deterministic extraction (no model) for non-image docs. Returns list of line dicts."""
    d = Path(datadir); t = json.loads((d / f"{name}.truth.json").read_text())
    kind, layout, f = t["kind"], t["layout"], d / t["file"]
    if kind == "pdf":
        return parse_pdf(layout, f, t["opening_balance"])
    if kind == "csv":
        return parse_csv_layout(layout, f)
    if kind == "xlsx":
        return parse_sheet(f)
    raise ValueError("image docs need the model")
