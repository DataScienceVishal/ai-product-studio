"""Synthetic sole-trader document generator with ground truth. All names fictional."""
import csv, json, random, subprocess, sys
from datetime import date, timedelta
from pathlib import Path

CATS = ["turnover", "cost_of_goods", "wages", "car_van_travel", "premises", "repairs",
        "phone_office", "advertising", "interest_bank_charges", "professional_fees",
        "other_expenses", "drawings_personal", "transfer"]

# (description template, category, amount range, direction)
MERCHANTS = [
    ("BACS FROM {c} LTD INV{n}", "turnover", (180, 1400), 1),
    ("FASTER PAYMENT {p} REF{n}", "turnover", (60, 600), 1),
    ("CARD PAYMENT TO BRICKWELL TIMBER SUPPLY", "cost_of_goods", (40, 380), -1),
    ("CARD PAYMENT TO OAKHAM TRADE PARTS", "cost_of_goods", (20, 220), -1),
    ("DD HARLOW FUEL STATION {n}", "car_van_travel", (30, 85), -1),
    ("CARD PAYMENT TO MERIDIAN PARKING", "car_van_travel", (3, 18), -1),
    ("DD NORTHGATE VAN INSURANCE", "car_van_travel", (48, 48), -1),
    ("DD ELMSTEAD UNITS RENT", "premises", (350, 350), -1),
    ("DD WESTFIELD POWER", "premises", (60, 140), -1),
    ("CARD PAYMENT TO QUICKFIX TYRES", "repairs", (25, 190), -1),
    ("DD TELLOWAY MOBILE", "phone_office", (22, 22), -1),
    ("CARD PAYMENT TO PAPERBOX STATIONERY", "phone_office", (6, 45), -1),
    ("CARD PAYMENT TO BRIGHTADS ONLINE", "advertising", (15, 90), -1),
    ("MONTHLY ACCOUNT FEE NORTHBANK", "interest_bank_charges", (7, 7), -1),
    ("OVERDRAFT INTEREST", "interest_bank_charges", (3, 14), -1),
    ("DD PENNYWORTH ACCOUNTANTS", "professional_fees", (45, 45), -1),
    ("CARD PAYMENT TO TRADEBODY SUBSCRIPTION", "other_expenses", (12, 60), -1),
    ("FASTER PAYMENT TO {p} WAGES", "wages", (120, 320), -1),
    ("CARD PAYMENT TO GREENLEAF SUPERMARKET", "drawings_personal", (12, 95), -1),
    ("CARD PAYMENT TO STARLIGHT CINEMAS", "drawings_personal", (9, 30), -1),
    ("DD STREAMBOX SUBSCRIPTION", "drawings_personal", (10, 10), -1),
    ("TRANSFER TO SAVINGS 8841", "transfer", (100, 400), -1),
    ("TRANSFER FROM SAVINGS 8841", "transfer", (100, 300), 1),
    ("STANDING ORDER TO OWNER PERSONAL A/C", "drawings_personal", (300, 600), -1),
]
CLIENTS = ["ASHBY JOINERY", "LINDEN CAFE", "MORROW & SON", "KESTREL DENTAL", "HALEWOOD PTA"]
PEOPLE = ["J HARGREAVE", "P OKONKWO", "S WINTERBOURNE", "T ABERNETHY"]


def make_txns(seed, n=32, start=date(2026, 4, 6), opening=2450.00):
    r = random.Random(seed)
    # guarantee coverage of each category once, then fill randomly
    pool = list(range(len(MERCHANTS)))
    picks = r.sample(pool, len(pool))[:n] + [r.choice(pool) for _ in range(max(0, n - len(pool)))]
    picks = picks[:n]
    days = sorted(r.randint(0, 88) for _ in picks)
    bal, out = opening, []
    for d, idx in zip(days, picks):
        tpl, cat, (lo, hi), sign = MERCHANTS[idx]
        desc = tpl.format(c=r.choice(CLIENTS), p=r.choice(PEOPLE), n=r.randint(1000, 9999))
        amt = round(r.uniform(lo, hi), 2) if lo != hi else float(lo)
        amt = round(sign * amt, 2)
        bal = round(bal + amt, 2)
        out.append({"date": (start + timedelta(days=d)).isoformat(), "description": desc,
                    "amount": amt, "balance": bal, "category": cat})
    return out, opening


def fmt_d(iso):
    return date.fromisoformat(iso).strftime("%d %b %Y")


def write_csv(path, txns):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Money Out", "Money In", "Balance"])
        for t in txns:
            a = t["amount"]
            w.writerow([date.fromisoformat(t["date"]).strftime("%d/%m/%Y"), t["description"],
                        f"{-a:.2f}" if a < 0 else "", f"{a:.2f}" if a > 0 else "", f"{t['balance']:.2f}"])


def write_pdf(path, txns, opening):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4
    c.setFont("Helvetica-Bold", 16); c.drawString(40, H - 50, "NORTHBANK plc (fictional)")
    c.setFont("Helvetica", 10)
    c.drawString(40, H - 70, "Business Current Account Statement")
    c.drawString(40, H - 84, "Account holder: MR A. SAMPLE T/A SAMPLE JOINERY   Sort code 00-00-00   Acc 00000000")
    c.drawString(40, H - 98, f"Statement period: {fmt_d(txns[0]['date'])} to {fmt_d(txns[-1]['date'])}")
    y = H - 125
    c.setFont("Helvetica-Bold", 9)
    for x, h in [(40, "Date"), (110, "Description"), (350, "Paid out"), (420, "Paid in"), (490, "Balance")]:
        c.drawString(x, y, h)
    c.setFont("Helvetica", 9); y -= 14
    c.drawString(110, y, "BALANCE BROUGHT FORWARD"); c.drawRightString(540, y, f"{opening:,.2f}"); y -= 14
    for t in txns:
        a = t["amount"]
        c.drawString(40, y, fmt_d(t["date"])); c.drawString(110, y, t["description"][:42])
        c.drawRightString(395 if a < 0 else 465, y, f"{abs(a):,.2f}")
        c.drawRightString(540, y, f"{t['balance']:,.2f}"); y -= 14
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(40, 40, "Synthetic test document. Not a real bank statement.")
    c.save()


def degrade(img, kind, seed):
    import numpy as np
    from PIL import Image, ImageFilter
    r = np.random.RandomState(seed)
    img = img.convert("L")
    if kind == "scan":
        img = img.rotate(1.8, expand=True, fillcolor=255).filter(ImageFilter.GaussianBlur(0.9))
        a = np.asarray(img).astype(float) + r.normal(0, 22, (img.height, img.width))
        a = np.clip(a * 0.9 + 12, 0, 255)
    else:  # phone photo: perspective-ish rotation, uneven lighting, blur, noise
        img = img.rotate(-4.5, expand=True, fillcolor=200).filter(ImageFilter.GaussianBlur(1.3))
        a = np.asarray(img).astype(float)
        h, w = a.shape
        grad = np.linspace(0.65, 1.05, w)[None, :] * np.linspace(0.85, 1.0, h)[:, None]
        a = np.clip(a * grad + r.normal(0, 10, a.shape), 0, 255)
    return Image.fromarray(a.astype("uint8")).convert("RGB")


def write_messy_csv(path, txns, seed):
    """Owner-made sheet: free text, mixed date formats, no balance, income/expense in one column."""
    r = random.Random(seed)
    nice = {"turnover": ["paid by {c}", "{c} job money in", "customer payment"],
            "cost_of_goods": ["timber", "wood for job", "trade counter stuff"],
            "car_van_travel": ["diesel", "van", "parking"], "premises": ["unit rent", "electric"],
            "repairs": ["tyres", "fixed van"], "phone_office": ["phone", "pens paper"],
            "advertising": ["facebook ads", "leaflets"], "interest_bank_charges": ["bank fee"],
            "professional_fees": ["accountant"], "other_expenses": ["trade body sub"],
            "wages": ["paid helper"], "drawings_personal": ["food shop", "me", "netflix etc", "cinema"],
            "transfer": ["moved to savings"]}
    rows = []
    for t in txns:
        d = date.fromisoformat(t["date"])
        ds = r.choice([d.strftime("%d/%m/%y"), d.strftime("%-d %b"), d.strftime("%d.%m.%Y")])
        txt = r.choice(nice[t["category"]]).format(c=r.choice(CLIENTS).title())
        rows.append([ds, txt, f"{t['amount']:.2f}", r.choice(["", "", "cash?", "check"])])
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["when", "what", "£", "notes"]); w.writerows(rows)
    return rows


def write_xlsx(path, rows):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["when", "what", "£", "notes"])
    for r_ in rows:
        ws.append([r_[0], r_[1], float(r_[2]), r_[3]])
    wb.save(path)


def build(outdir):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    docs = {}
    t, op = make_txns(11); docs["clean_pdf"] = (t, op)
    write_pdf(out / "clean_pdf.pdf", t, op)
    t2, op2 = make_txns(22); docs["scan_image"] = (t2, op2)
    write_pdf(out / "_tmp_scan.pdf", t2, op2)
    t3, op3 = make_txns(33); docs["phone_photo"] = (t3, op3)
    write_pdf(out / "_tmp_photo.pdf", t3, op3)
    from PIL import Image
    for name, kind, seed in [("_tmp_scan", "scan", 1), ("_tmp_photo", "photo", 2)]:
        subprocess.run(["pdftoppm", "-r", "110", "-png", "-singlefile", str(out / f"{name}.pdf"), str(out / name)], check=True)
        degrade(Image.open(out / f"{name}.png"), kind, seed).save(out / ("scan_image.jpg" if kind == "scan" else "phone_photo.jpg"), quality=70)
        (out / f"{name}.pdf").unlink(); (out / f"{name}.png").unlink()
    t4, op4 = make_txns(44); docs["csv_export"] = (t4, op4)
    write_csv(out / "csv_export.csv", t4)
    t5, _ = make_txns(55); rows = write_messy_csv(out / "messy_sheet.csv", t5, 5)
    write_xlsx(out / "messy_sheet.xlsx", rows)
    # messy sheet truth has no balance
    docs["messy_sheet"] = ([{**x, "balance": None} for x in t5], None)
    files = {"clean_pdf": "clean_pdf.pdf", "scan_image": "scan_image.jpg", "phone_photo": "phone_photo.jpg",
             "csv_export": "csv_export.csv", "messy_sheet": "messy_sheet.xlsx"}
    for k, (tx, op) in docs.items():
        (out / f"{k}.truth.json").write_text(json.dumps({"file": files[k], "opening_balance": op, "lines": tx}, indent=1))
    return files


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "data"))
