"""Deterministic generator of fictional UK supplier invoices with ground truth.

All suppliers, addresses and VAT numbers are invented. Run:  python generate.py --out data

Produces data/dev (10 invoices, seed 1001). data/test (50 invoices, seed 2025) needs the held-out layouts, written later. Per invoice:
  <id>.json        ground truth
  <id>.pdf         the clean document
  <id>_p<N>.png    clean page images (clean invoices)
  <id>_p<N>.jpg    phone-photo page images (distorted invoices, about half of TEST)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

import distort

TEST_SEED, DEV_SEED = 2025, 1001  # KILL-TEST.md: test 2025 (rerun 2026), dev 1001
RENDER_DPI = 200
CENT = Decimal("0.01")

SUPPLIERS = {
    "broadliner_a": {"name": "Fenwick & Dale Foodservice Ltd", "addr": ["Unit 14 Marsh Lane Trading Estate", "Northcote, NC4 7XT"],
                     "vat": "GB 000 1112 21", "prefix": "FD"},
    "butcher": {"name": "Harker & Sons Family Butchers", "addr": ["22 Tanners Row", "Wexbridge, WX2 1AB"],
                "vat": "GB 000 2223 32", "prefix": "HS"},
    "cashcarry": {"name": "Bulkbuy Cash & Carry", "addr": ["Ring Road Retail Park", "Midford, MF5 0ZZ"],
                  "vat": "GB 000 5556 65", "prefix": "BB"},
}
# Held-out layouts (broadliner_b, greengrocer, dairy_drinks) are deliberately NOT implemented here: KILL-TEST.md says their
# code is written only after the prompt is frozen. They plug in through HELDOUT_LAYOUTS (see load_heldout).
DEV_LAYOUTS = ["broadliner_a", "cashcarry", "butcher"]
HELDOUT_LAYOUTS = ["broadliner_b", "greengrocer", "dairy_drinks"]

# (printed description, pack_size, unit, price low, price high, vat %, weighed)
CATALOG = {
    "broadliner_a": [
        ("CHICKEN BREAST FIL SKLS 2.5KG", "2.5kg", "case", 14, 19, 0, False),
        ("OIL RAPESEED CATERING 20L", "20L", "each", 28, 36, 0, False),
        ("FLOUR PLAIN WHT 16KG", "16kg", "each", 12, 17, 0, False),
        ("TOM CHOPPED IN JUICE 6X400G", "6x400g", "case", 6, 9, 0, False),
        ("CHEESE MOZZ BLK 2.3KG", "2.3kg", "each", 13, 18, 0, False),
        ("CREAM DBL 6X1L", "6x1L", "case", 14, 19, 0, False),
        ("BUTTER UNSLTD 20X250G", "20x250g", "case", 38, 50, 0, False),
        ("EGGS MED FR RANGE 180", "180", "case", 21, 28, 0, False),
        ("CLNG FLUID MULTI SURF 5L", "5L", "each", 4, 7, 20, False),
        ("FOIL CATERING 450MMX90M", "", "each", 9, 14, 20, False),
        ("NAPKIN 2PLY WHT 2000", "2000", "case", 11, 16, 20, False),
        ("SUGAR GRAN 15KG", "15kg", "each", 14, 19, 0, False),
        ("RICE BASMATI 10KG", "10kg", "each", 16, 23, 0, False),
        ("STOCK BEEF PASTE 6X1KG", "6x1kg", "case", 24, 33, 0, False),
        ("PASTA PENNE DRY 3KG", "3kg", "each", 3, 6, 0, False),
        ("BLK PEPPER GRND 500G", "500g", "each", 5, 9, 0, False),
        ("MILK SEMI SKIM 6X2L", "6x2L", "case", 7, 10, 0, False),
        ("BACON SMKD RINDLESS 2KG", "2kg", "each", 13, 18, 0, False),
        ("POTATO CHIP FRZN 4X2.5KG", "4x2.5kg", "case", 11, 16, 0, False),
        ("GLOVE NITRILE BLU L X100", "100", "box", 4, 7, 20, False),
        ("VINEGAR MALT 5L", "5L", "each", 3, 6, 0, False),
        ("SALT TABLE FINE 3KG", "3kg", "each", 2, 4, 0, False),
        ("MAYO CATERING 5L", "5L", "each", 8, 12, 0, False),
        ("PLASTIC TAKEAWAY CNTR 500CC X250", "250", "case", 18, 26, 20, False),
        ("YOGHURT NAT 5KG", "5kg", "each", 6, 9, 0, False),
        ("HONEY CLEAR 3KG", "3kg", "each", 14, 20, 0, False),
        ("CHOC DARK CHIPS 2.5KG", "2.5kg", "each", 15, 21, 0, False),
        ("BIN LINER HD BLK 200S", "200", "box", 12, 17, 20, False),
        ("LPG CYLINDER REFILL 13KG", "13kg", "each", 24, 30, 5, False),  # fictional: 5% rate used so the VAT mix covers it
        ("EGGS FREE RANGE DOZEN", "dozen", "each", 2.4, 3.6, 0, False),
        ("SPICE MIX CAJUN 6 X 2.5KG", "6 x 2.5kg", "case", 38, 52, 0, False),
        ("CHICKEN WINGS 5KG CASE", "5kg case", "case", 16, 22, 0, False),
    ],
    "butcher": [
        ("BEEF MINCE 20% 5KG", "5kg", "pack", 32, 42, 0, False),
        ("RUMP STEAK TRIMMED", "", "kg", 14, 18, 0, True),
        ("PORK BELLY RIND ON", "", "kg", 5, 8, 0, True),
        ("CHICKEN THIGH BONE IN 10KG", "10kg", "case", 22, 30, 0, False),
        ("LAMB SHOULDER BONE IN", "", "kg", 9, 13, 0, True),
        ("BACON SMKD BACK 2KG", "2kg", "pack", 14, 19, 0, False),
        ("BEEF DICED CHUCK", "", "kg", 8, 11, 0, True),
        ("BEEF MARROW BONES", "", "kg", 2, 4, 0, True),
        ("BLACK PUDDING 1KG", "1kg", "each", 5, 8, 0, False),
        ("PORK SAUS 8S 454G", "454g", "pack", 3, 5, 0, False),
        ("SIRLOIN 28D HUNG", "", "kg", 22, 29, 0, True),
        ("CHICKEN WHOLE FR 1.8KG", "1.8kg", "each", 6, 9, 0, False),
        ("DUCK BREAST X2 400G", "400g", "pack", 7, 10, 0, False),
        ("LAMB RACK FRENCH TRIM", "", "kg", 24, 32, 0, True),
        ("BUTCHERS STRING 500G", "500g", "each", 3, 5, 20, False),
        ("DISPOSABLE GLOVES BLU X100", "100", "box", 3, 5, 20, False),
        ("OX CHEEK", "", "kg", 9, 12, 0, True),
        ("PORK SAUSAGE DOZEN", "dozen", "each", 3, 5, 0, False),
        ("PORK SHOULDER DICED", "", "kg", 6, 9, 0, True),
    ],
    "cashcarry": [
        ("CHKN WHOLE FR 1.8KG", "1.8kg", "each", 5, 8, 0, False),
        ("BIN LINERS 200S", "200", "pack", 9, 14, 20, False),
        ("WASHING UP LIQ 5L", "5L", "each", 3, 6, 20, False),
        ("CHIPS 2.5KG X4", "4x2.5kg", "case", 10, 15, 0, False),
        ("SALAD CREAM 5L", "5L", "each", 6, 9, 0, False),
        ("KETCHUP SACHET 1000", "1000", "box", 12, 17, 0, False),
        ("SPONGE SCOURER 10PK", "10", "pack", 2, 4, 20, False),
        ("SMKD SALMON SLICED 1KG", "1kg", "each", 18, 26, 0, False),
        ("BREAD ROLL WHT 12PK", "12", "pack", 1.5, 2.6, 0, False),
        ("CHILLI SAUCE 6X1L", "6x1L", "case", 14, 20, 0, False),
        ("TISSUE CENTREFEED 6RL", "6", "pack", 7, 11, 20, False),
        ("CHEDDAR MATURE 5KG", "5kg", "each", 24, 33, 0, False),
        ("COOKING OIL VEG 20L", "20L", "each", 26, 34, 0, False),
        ("ONION BROWN LOOSE", "", "kg", 0.7, 1.2, 0, True),
        ("POTATO BAKING LOOSE", "", "kg", 0.9, 1.5, 0, True),
        ("MINCED BEEF 5% 2KG", "2kg", "each", 11, 16, 0, False),
        ("COFFEE JAR INST 750G", "750g", "each", 11, 16, 0, False),
        ("PAPER TOWEL ROLL 6PK", "6", "pack", 6, 9, 20, False),
        ("EGGS LRG FR 30", "30", "each", 4, 6, 0, False),
        ("LPG CYLINDER 13KG", "13kg", "each", 25, 31, 5, False),  # fictional 5% line
        ("BANANAS LOOSE", "", "kg", 0.8, 1.3, 0, True),
        ("FRYING FAT 4X12.5KG", "4 x 12.5kg", "case", 70, 90, 0, False),
        ("SOFT DRINK COLA 24X330ML", "24x330ml", "case", 9, 13, 20, False),
        ("SOFT DRINK LEMON 24X330ML", "24x330ml", "case", 9, 13, 20, False),
        ("BIN BAGS BLACK ROLL 100", "100", "pack", 6, 9, 20, False),
        ("MILK WHL 4PT", "", "each", 1.6, 2.2, 0, False),
        ("SUNFLWR OIL 5L", "5L", "each", 8, 12, 0, False),
        ("TOMATO PASSATA 6X700G", "6x700g", "case", 6, 9, 0, False),
    ],
}
# Rows per page decide page count: a "single page" invoice has 10..rows lines, a multi-page one has rows+1..3*rows (max 2-3 pages).
ROWS_PER_PAGE = {"broadliner_a": 12, "butcher": 12, "cashcarry": 14}
UNIT_CODE = {"case": "CS", "each": "EA", "kg": "KG", "pack": "PK", "box": "BX"}


def q2(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def money(x) -> str:
    return f"{Decimal(str(x)):,.2f}"


def fq(qty) -> str:
    q = Decimal(str(qty))
    return str(int(q)) if q == q.to_integral() else f"{q:.2f}"


def build_invoice(rng: random.Random, key: str, inv_id: str, credit: bool, distorted: bool, multipage: bool,
                  base_date: date) -> dict:
    sup = SUPPLIERS[key]
    per = ROWS_PER_PAGE[key]
    cat = CATALOG[key]
    if multipage:  # 2 to 3 pages
        n = rng.randint(per + 1, min(per * 3, len(cat)))
    else:
        n = rng.randint(min(10, per), min(per - 1, len(cat)))  # one line of headroom for a possible negative line
    items = rng.sample(cat, n)
    lines = []
    for desc, pack, unit, plo, phi, vat, weighed in items:
        if weighed:
            qty = Decimal(str(round(rng.uniform(0.8, 9.5), 2)))
        else:
            qty = Decimal(rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 6, 8]))
        price = Decimal(str(round(rng.uniform(plo, phi), 2)))
        disc = rng.choice([5, 10]) if key == "broadliner_a" and rng.random() < 0.18 else 0
        lines.append({"description": desc, "qty": qty, "pack_size": pack, "unit": unit, "unit_price": price,
                      "discount_pct": disc, "vat_rate": vat, "code": f"{sup['prefix']}{rng.randint(10000, 99999)}"})
    if not credit and rng.random() < 0.15:  # a returned or damaged item credited on a normal invoice
        src = rng.choice(lines)
        lines.append({"description": "CR " + src["description"] + " DAMAGED", "qty": Decimal(-1), "pack_size": src["pack_size"],
                      "unit": src["unit"], "unit_price": src["unit_price"], "discount_pct": 0, "vat_rate": src["vat_rate"],
                      "code": src["code"]})
    if credit:
        for ln in lines:
            ln["qty"] = -ln["qty"]
    for k, ln in enumerate(lines):
        ln["line_total"] = q2(ln["qty"] * ln["unit_price"] * (Decimal(100) - ln["discount_pct"]) / Decimal(100))
        ln["page"] = k // per + 1
    net = sum((ln["line_total"] for ln in lines), Decimal(0))
    vat_by_rate = {}
    for rate in sorted({ln["vat_rate"] for ln in lines}):
        part = sum((ln["line_total"] for ln in lines if ln["vat_rate"] == rate), Decimal(0))
        vat_by_rate[str(rate)] = q2(part * Decimal(rate) / Decimal(100))
    vat = sum(vat_by_rate.values(), Decimal(0))
    d = base_date + timedelta(days=rng.randint(0, 60))
    number = f"{rng.randint(10000, 99999)}" if not credit else f"CN{rng.randint(1000, 9999)}"
    inv = {
        "id": inv_id, "layout": key, "heldout": key in HELDOUT_LAYOUTS, "supplier": sup["name"], "invoice_no": number,
        "date": d.isoformat(), "credit_note": credit, "distorted": distorted, "pages": max(1, -(-len(lines) // per)),
        "lines": [{**ln, "qty": float(ln["qty"]), "unit_price": float(ln["unit_price"]), "line_total": float(ln["line_total"])}
                  for ln in lines],
        "totals": {"net": float(net), "vat": float(vat) + 0.0, "gross": float(net + vat) + 0.0,
                   "vat_by_rate": {r: float(v) + 0.0 for r, v in vat_by_rate.items()}},
    }
    check_totals(inv)
    return inv


def check_totals(inv: dict) -> None:
    """The generator checks its own arithmetic before anything is written (KILL-TEST.md section 1)."""
    lines = inv["lines"]
    net = round(sum(ln["line_total"] for ln in lines), 2)
    assert abs(net - inv["totals"]["net"]) < 0.005, (inv["id"], "net")
    vat = round(sum(inv["totals"]["vat_by_rate"].values()), 2)
    assert abs(vat - inv["totals"]["vat"]) < 0.005, (inv["id"], "vat")
    assert abs(round(net + vat, 2) - inv["totals"]["gross"]) < 0.005, (inv["id"], "gross")
    for ln in lines:
        expect = round(ln["qty"] * ln["unit_price"] * (100 - ln["discount_pct"]) / 100, 2)
        assert abs(expect - ln["line_total"]) < 0.0101, (inv["id"], ln["description"], "line total")
    assert inv["credit_note"] == all(ln["qty"] < 0 for ln in lines) or not inv["credit_note"]


# ------------------------------------------------------------------ rendering

DATE_FORMATS = {"broadliner_a": "%d/%m/%Y", "butcher": "%d %b %Y", "cashcarry": "%d/%m/%Y"}


def _date_text(key: str, iso: str) -> str:
    d = date.fromisoformat(iso)
    return d.strftime(DATE_FORMATS[key])


def _chunks(lines, per):
    return [lines[i:i + per] for i in range(0, len(lines), per)] or [[]]


def _totals_block(c, inv, x_right, y, label_net="Net total", font="Helvetica", size=10):
    t = inv["totals"]
    c.setFont(font + "-Bold" if font == "Helvetica" else font, size)
    for label, val in (("Net", t["net"]), ("VAT", t["vat"]), ("TOTAL" + (" CREDIT" if inv["credit_note"] else ""), t["gross"])):
        c.drawRightString(x_right - 28 * mm, y, label if label != "Net" else label_net)
        c.drawRightString(x_right, y, "£" + money(val) if val >= 0 else "-£" + money(-val))
        y -= size * 1.6


def _vat_text(r: int) -> str:
    return f"{r}%"


def render_broadline(c, inv):
    W, H = 210 * mm, 297 * mm
    sup = SUPPLIERS["broadliner_a"]
    chunks = _chunks(inv["lines"], ROWS_PER_PAGE["broadliner_a"])
    for pi, chunk in enumerate(chunks):
        c.setFillColor(colors.HexColor("#1d4e89"))
        c.rect(0, H - 30 * mm, W, 30 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(15 * mm, H - 16 * mm, sup["name"])
        c.setFont("Helvetica", 8)
        c.drawString(15 * mm, H - 22 * mm, ", ".join(sup["addr"]) + "   VAT Reg " + sup["vat"])
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(15 * mm, H - 42 * mm, "CREDIT NOTE" if inv["credit_note"] else "TAX INVOICE")
        c.setFont("Helvetica", 9)
        c.drawString(15 * mm, H - 49 * mm, f"{'Credit note' if inv['credit_note'] else 'Invoice'} No: {inv['invoice_no']}")
        c.drawString(15 * mm, H - 54 * mm, f"Date: {_date_text('broadliner_a', inv['date'])}")
        c.drawString(110 * mm, H - 49 * mm, "Deliver to: The Copper Kettle Kitchen")
        c.drawString(110 * mm, H - 54 * mm, "Account: CK00417    Page %d of %d" % (pi + 1, len(chunks)))
        cols = [("Code", 12, "l"), ("Description", 33, "l"), ("Pack", 99, "l"), ("Qty", 124, "r"), ("UoM", 128, "l"),
                ("Price", 153, "r"), ("Disc%", 166, "r"), ("VAT", 178, "r"), ("Net", 196, "r")]
        y = H - 64 * mm
        c.setFillColor(colors.HexColor("#e6edf5"))
        c.rect(10 * mm, y - 2 * mm, 190 * mm, 7 * mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 8)
        for title, x, al in cols:
            (c.drawRightString if al == "r" else c.drawString)(x * mm, y, title)
        y -= 8 * mm
        c.setFont("Helvetica", 8)
        for i, ln in enumerate(chunk):
            if i % 2:
                c.setFillColor(colors.HexColor("#f6f8fb"))
                c.rect(10 * mm, y - 2 * mm, 190 * mm, 7 * mm, fill=1, stroke=0)
                c.setFillColor(colors.black)
            vals = [ln["code"], ln["description"], ln["pack_size"], fq(ln["qty"]), UNIT_CODE[ln["unit"]], money(ln["unit_price"]),
                    f"{ln['discount_pct']}" if ln["discount_pct"] else "", _vat_text(ln["vat_rate"]), money(ln["line_total"])]
            for (title, x, al), v in zip(cols, vals):
                (c.drawRightString if al == "r" else c.drawString)(x * mm, y, v)
            y -= 7 * mm
        if pi < len(chunks) - 1:
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(15 * mm, 20 * mm, "continued overleaf")
        else:
            c.line(10 * mm, y + 3 * mm, 200 * mm, y + 3 * mm)
            _totals_block(c, inv, 196 * mm, y - 4 * mm)
            c.setFont("Helvetica", 7)
            c.drawString(15 * mm, 18 * mm, "Payment terms 30 days. Goods remain our property until paid. Short deliveries must be reported in 24h.")
        c.showPage()


def render_butcher(c, inv):
    W, H = 210 * mm, 297 * mm
    sup = SUPPLIERS["butcher"]
    chunks = _chunks(inv["lines"], ROWS_PER_PAGE["butcher"])
    for pi, chunk in enumerate(chunks):
        c.setFont("Times-Bold", 26)
        c.drawCentredString(W / 2, H - 22 * mm, "HARKER & SONS")
        c.setFont("Times-Italic", 12)
        c.drawCentredString(W / 2, H - 29 * mm, "Family Butchers since 1962")
        c.setFont("Times-Roman", 9)
        c.drawCentredString(W / 2, H - 35 * mm, ", ".join(sup["addr"]) + "  VAT " + sup["vat"])
        c.rect(12 * mm, H - 40 * mm, 186 * mm, 0.6 * mm, fill=1)
        c.setFont("Times-Bold", 12)
        c.drawString(15 * mm, H - 50 * mm, ("CREDIT NOTE no. " if inv["credit_note"] else "Invoice no. ") + inv["invoice_no"])
        c.setFont("Times-Roman", 11)
        c.drawRightString(195 * mm, H - 50 * mm, "Date " + _date_text("butcher", inv["date"]))
        c.drawString(15 * mm, H - 57 * mm, "Customer: The Copper Kettle Kitchen")
        c.drawRightString(195 * mm, H - 57 * mm, f"Sheet {pi + 1}/{len(chunks)}")
        y = H - 68 * mm
        c.setFont("Times-Bold", 10)
        c.drawString(15 * mm, y, "ITEM")
        c.drawRightString(120 * mm, y, "WEIGHT / QTY")
        c.drawRightString(152 * mm, y, "PRICE")
        c.drawString(158 * mm, y, "V")
        c.drawRightString(195 * mm, y, "AMOUNT")
        c.line(12 * mm, y - 2 * mm, 198 * mm, y - 2 * mm)
        y -= 9 * mm
        c.setFont("Times-Roman", 10.5)
        for ln in chunk:
            c.drawString(15 * mm, y, ln["description"])
            if ln["unit"] == "kg":
                qty_t, price_t = f"{fq(ln['qty'])} kg", f"{money(ln['unit_price'])}/kg"
            else:
                qty_t, price_t = f"{fq(ln['qty'])} x", f"{money(ln['unit_price'])} ea"
            c.drawRightString(120 * mm, y, qty_t)
            c.drawRightString(152 * mm, y, price_t)
            c.drawString(158 * mm, y, "S" if ln["vat_rate"] else "Z")
            c.drawRightString(195 * mm, y, money(ln["line_total"]))
            y -= 8 * mm
        if pi == len(chunks) - 1:
            c.line(12 * mm, y + 4 * mm, 198 * mm, y + 4 * mm)
            _totals_block(c, inv, 195 * mm, y - 3 * mm, font="Times-Bold")
            c.setFont("Times-Italic", 9)
            c.drawString(15 * mm, 25 * mm, "Z = zero rated (0%), S = standard rated (20%). Thank you for your custom.")
        c.showPage()


def render_cashcarry(c, inv):
    W, H = 85 * mm, 270 * mm
    sup = SUPPLIERS["cashcarry"]
    chunks = _chunks(inv["lines"], ROWS_PER_PAGE["cashcarry"])
    code = {20: "A", 0: "B", 5: "C"}
    for pi, chunk in enumerate(chunks):
        y = H - 12 * mm
        c.setFont("Courier-Bold", 12)
        c.drawCentredString(W / 2, y, sup["name"].upper())
        c.setFont("Courier", 7.5)
        for a in sup["addr"] + ["VAT No " + sup["vat"], "Trade customer: COPPER KETTLE"]:
            y -= 4 * mm
            c.drawCentredString(W / 2, y, a)
        y -= 6 * mm
        c.drawString(5 * mm, y, ("CREDIT " if inv["credit_note"] else "SALE ") + "REF " + inv["invoice_no"])
        c.drawRightString(80 * mm, y, _date_text("cashcarry", inv["date"]))
        y -= 3 * mm
        c.drawString(5 * mm, y, "-" * 39)
        y -= 5 * mm
        for ln in chunk:
            c.setFont("Courier", 7.5)
            c.drawString(5 * mm, y, ln["description"][:38])
            y -= 3.6 * mm
            if ln["unit"] == "kg":
                detail = f"{abs(ln['qty']):.3f} kg @ {money(ln['unit_price'])}/kg"
            else:
                detail = f"{fq(abs(ln['qty']))} x {money(ln['unit_price'])}"
            c.drawString(8 * mm, y, detail)
            lt = money(abs(ln["line_total"]))
            c.drawRightString(76 * mm, y, ("-" if ln["line_total"] < 0 else "") + lt)
            c.drawString(77 * mm, y, code[ln["vat_rate"]])
            y -= 5 * mm
        if pi == len(chunks) - 1:
            c.drawString(5 * mm, y, "-" * 39)
            y -= 5 * mm
            t = inv["totals"]
            c.setFont("Courier-Bold", 8)
            for label, v in (("NET", t["net"]), ("VAT", t["vat"]), ("TOTAL", t["gross"])):
                c.drawString(8 * mm, y, label)
                c.drawRightString(76 * mm, y, ("-" if v < 0 else "") + money(abs(v)))
                y -= 4.5 * mm
            c.setFont("Courier", 7)
            c.drawString(5 * mm, y - 2 * mm, "VAT CODES A=20.0% B=0.0% C=5.0%")
        else:
            c.setFont("Courier", 7)
            c.drawString(5 * mm, 10 * mm, f"** continued ({pi + 1}/{len(chunks)}) **")
        c.showPage()


RENDERERS = {"broadliner_a": (render_broadline, (210 * mm, 297 * mm)), "butcher": (render_butcher, (210 * mm, 297 * mm)),
             "cashcarry": (render_cashcarry, (85 * mm, 270 * mm))}


def register_layout(key, supplier, catalog, rows_per_page, renderer, page_size, date_format):
    """Hook for the held-out layouts (layouts_heldout.py, written only after the prompt is frozen)."""
    SUPPLIERS[key], CATALOG[key], ROWS_PER_PAGE[key] = supplier, catalog, rows_per_page
    RENDERERS[key], DATE_FORMATS[key] = (renderer, page_size), date_format


def load_heldout() -> bool:
    """Import layouts_heldout if it exists; it calls register_layout() for broadliner_b, greengrocer and dairy_drinks."""
    try:
        import layouts_heldout  # noqa: F401
    except ModuleNotFoundError as e:
        if e.name != "layouts_heldout":
            raise
        return False
    return all(k in RENDERERS for k in HELDOUT_LAYOUTS)


def render_pdf(inv: dict) -> bytes:
    fn, size = RENDERERS[inv["layout"]]
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=size, invariant=1)  # invariant: no timestamps, so output is byte-stable
    c.setTitle(inv["id"])
    fn(c, inv)
    c.save()
    return buf.getvalue()


def pdf_to_pages(pdf: bytes):
    import pymupdf as fitz  # PyMuPDF
    from PIL import Image
    doc = fitz.open(stream=pdf, filetype="pdf")
    pages = []
    for p in doc:
        pix = p.get_pixmap(dpi=RENDER_DPI, alpha=False)
        pages.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return pages


# ------------------------------------------------------------------ sets

# (layout, credit note, phone photo, multi-page). DEV: 10 invoices on the three dev layouts only.
DEV_PLAN = [
    ("broadliner_a", False, False, True), ("broadliner_a", False, True, False), ("broadliner_a", True, False, False),
    ("broadliner_a", False, True, True), ("cashcarry", False, False, True), ("cashcarry", True, True, False),
    ("cashcarry", False, True, False), ("butcher", False, False, False), ("butcher", False, True, True),
    ("butcher", False, False, False),
]


def test_plan() -> list[tuple]:
    """50 invoices: 25 on dev layouts, 25 on held-out ones; 30 phone photos, 10 credit notes, 15 multi-page.
    Layouts alternate dev / held-out so ids do not group by layout. The plan needs no held-out code; rendering does."""
    cycle = ["broadliner_a", "broadliner_b", "cashcarry", "butcher", "greengrocer", "dairy_drinks"]
    out = []
    for i in range(50):
        out.append((cycle[i % 6], i % 5 == 2, i % 5 in (0, 1, 3), i % 7 in (0, 3)))
    return out


SETS = {"test": {"seed": TEST_SEED, "plan": test_plan}, "dev": {"seed": DEV_SEED, "plan": lambda: DEV_PLAN}}


def generate_set(name: str, out_root: Path, images: bool = True) -> list[dict]:
    cfg = SETS[name]
    plan = cfg["plan"]()
    if any(layout in HELDOUT_LAYOUTS for layout, *_ in plan) and not load_heldout():
        raise SystemExit(f"set '{name}' needs the held-out layouts {HELDOUT_LAYOUTS}; layouts_heldout.py does not exist yet "
                         "(it is written only after the prompt is frozen, KILL-TEST.md section 1)")
    rng = random.Random(cfg["seed"])
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    invoices = []
    for k, (layout, credit, distorted, multipage) in enumerate(plan, 1):
        inv_id = f"{name.upper()}-{k:03d}"
        inv = build_invoice(rng, layout, inv_id, credit, distorted, multipage, date(2026, 9, 1))
        pdf = render_pdf(inv)
        files, distortion = [], []
        if images:
            pages = pdf_to_pages(pdf)
            assert len(pages) == inv["pages"], (inv_id, len(pages), inv["pages"])
            for n, img in enumerate(pages, 1):
                if distorted:
                    fname = f"{inv_id}_p{n}.jpg"
                    data, params = distort.make_photo(img, seed=cfg["seed"] * 1000 + k * 10 + n)
                    (out / fname).write_bytes(data)
                    distortion.append(params)
                else:
                    fname = f"{inv_id}_p{n}.png"
                    img.save(out / fname, optimize=True)
                files.append(fname)
        (out / f"{inv_id}.pdf").write_bytes(pdf)
        inv["images"], inv["distortion"] = files, distortion
        (out / f"{inv_id}.json").write_text(json.dumps(inv, indent=1, sort_keys=True) + "\n")
        invoices.append(inv)
    if images:
        write_manifest(out, name)
    return invoices


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(out: Path, name: str) -> dict:
    files = {p.name: file_sha256(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "MANIFEST.json"}
    manifest = {"set": name, "seed": SETS[name]["seed"], "render_dpi": RENDER_DPI, "files": files}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def verify_manifest(out: Path) -> list[str]:
    """Names of files whose hash differs from, or are missing against, MANIFEST.json (empty list = identical)."""
    manifest = json.loads((out / "MANIFEST.json").read_text())
    bad = [n for n, h in manifest["files"].items() if not (out / n).exists() or file_sha256(out / n) != h]
    bad += [p.name for p in out.iterdir() if p.is_file() and p.name != "MANIFEST.json" and p.name not in manifest["files"]]
    return bad


def truth_digest(invoices: list[dict]) -> str:
    return hashlib.sha256(json.dumps(invoices, sort_keys=True).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--sets", nargs="+", default=["dev"], choices=list(SETS))
    ap.add_argument("--no-images", action="store_true", help="ground truth and PDFs only")
    ap.add_argument("--verify", action="store_true", help="regenerate into a temp dir and compare with the committed MANIFEST.json")
    args = ap.parse_args()
    for name in args.sets:
        if args.verify:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                generate_set(name, Path(tmp))
                a = json.loads((Path(tmp) / name / "MANIFEST.json").read_text())["files"]
                b = json.loads((Path(args.out) / name / "MANIFEST.json").read_text())["files"]
                diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
                print(f"{name}: {'identical to the committed manifest' if not diff else 'DIFFERENT: ' + ', '.join(diff[:10])}")
            continue
        invs = generate_set(name, Path(args.out), images=not args.no_images)
        print(f"{name}: {len(invs)} invoices, {sum(i['pages'] for i in invs)} pages, {sum(i['distorted'] for i in invs)} phone photos, "
              f"{sum(i['credit_note'] for i in invs)} credit notes, {sum(i['pages'] > 1 for i in invs)} multi-page, "
              f"truth sha256 {truth_digest(invs)[:16]}")


if __name__ == "__main__":
    main()
