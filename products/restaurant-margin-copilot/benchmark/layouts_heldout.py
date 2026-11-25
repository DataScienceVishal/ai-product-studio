"""Held-out layouts: broadliner B, greengrocer, dairy and drinks wholesaler. Written AFTER the prompt was frozen (FROZEN.json).

All names, addresses and VAT numbers are invented. Imported by generate.load_heldout(); registers three layouts through
generate.register_layout(). Visually distinct from the dev layouts: B is landscape with the quantity first and VAT codes,
the greengrocer is a monospaced A5 delivery note, the dairy and drinks wholesaler is a boxed portrait invoice with a VAT summary.
"""
from reportlab.lib import colors
from reportlab.lib.units import mm

import generate as g

# ------------------------------------------------------------------ broadliner B (landscape, quantity first, VAT codes)
BROADLINER_B = {"name": "Calder Valley Catering Supplies plc", "addr": ["Brook Mill Business Park", "Hollinsworth, HW8 2PL"],
                "vat": "GB 000 6667 76", "prefix": "CV"}
BROADLINER_B_CATALOG = [
    ("CHKN FILLET MINI 2KG PK", "2kg", "pack", 11, 16, 0, False), ("OIL SUNFLWR 20 LTR JERRY", "20L", "each", 27, 35, 0, False),
    ("FLR STRONG WHT BREAD 16KG", "16kg", "each", 13, 18, 0, False), ("TOMATO PLUM WHL 6X2.5KG", "6x2.5kg", "case", 14, 20, 0, False),
    ("CHEESE CHEDDAR MED 5KG", "5kg", "each", 26, 34, 0, False), ("CREAM SNGL 12X500ML", "12x500ml", "case", 15, 21, 0, False),
    ("MARGARINE CATERING 10KG", "10kg", "each", 14, 20, 0, False), ("EGG LIQUID PAST 5X1L", "5x1L", "case", 12, 17, 0, False),
    ("DEGREASER HD SPRAY 750ML", "750ml", "each", 2.4, 4.2, 20, False), ("CLING FILM 450MM X 300M", "", "each", 6, 10, 20, False),
    ("TABLE ROLL WHT 40CM X 100M", "", "each", 7, 12, 20, False), ("SUGAR CASTER 3KG", "3kg", "each", 3, 5, 0, False),
    ("RICE LONG GRAIN 20KG", "20kg", "each", 18, 26, 0, False), ("GRAVY GRANULES BEEF 2KG", "2kg", "each", 7, 11, 0, False),
    ("SPAGHETTI DRY 6X500G", "6x500g", "case", 5, 8, 0, False), ("PEPPER WHITE GRND 1KG", "1kg", "each", 14, 20, 0, False),
    ("MILK WHOLE 12X1L", "12x1L", "case", 8, 12, 0, False), ("HAM COOKED SLCD 1KG", "1kg", "each", 8, 12, 0, False),
    ("FRIES 9MM FRZN 4X2.5KG", "4x2.5kg", "case", 10, 15, 0, False), ("GLOVES VINYL CLR M 100", "100", "box", 3, 5.5, 20, False),
    ("VINEGAR BREWED 5 LTR", "5L", "each", 3, 6, 0, False), ("SEA SALT COARSE 1.5KG", "1.5kg", "each", 1.2, 2.4, 0, False),
    ("MAYONNAISE LT 10 LTR", "10L", "each", 14, 20, 0, False), ("CONTAINER FOIL 1/2 GN X50", "50", "box", 14, 22, 20, False),
    ("YOG GREEK STYLE 10KG", "10kg", "each", 14, 20, 0, False), ("SYRUP GOLDEN 6X680G", "6x680g", "case", 13, 19, 0, False),
    ("COOKING CHOC 2X2.5KG", "2x2.5kg", "case", 26, 36, 0, False), ("LPG PROPANE CYL 19KG REFILL", "19kg", "each", 36, 44, 5, False),
    ("EGGS LARGE FR 15 DOZEN", "180", "case", 22, 29, 0, False), ("HONEY SQUEEZY 12X340G", "12x340g", "case", 22, 30, 0, False),
]
_VCODE = {0: "Z", 5: "R", 20: "S"}


def render_broadliner_b(c, inv):
    W, H = 297 * mm, 210 * mm
    sup = g.SUPPLIERS["broadliner_b"]
    chunks = g._chunks(inv["lines"], g.ROWS_PER_PAGE["broadliner_b"])
    for pi, chunk in enumerate(chunks):
        c.setFillColor(colors.HexColor("#7a1f1f"))
        c.rect(0, H - 22 * mm, 70 * mm, 22 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(8 * mm, H - 14 * mm, "CALDER")
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(78 * mm, H - 10 * mm, sup["name"])
        c.setFont("Helvetica", 8)
        c.drawString(78 * mm, H - 15 * mm, ", ".join(sup["addr"]) + "  |  VAT " + sup["vat"])
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(W - 10 * mm, H - 12 * mm, "CREDIT NOTE" if inv["credit_note"] else "INVOICE")
        c.setFont("Helvetica", 9)
        c.drawRightString(W - 10 * mm, H - 18 * mm, f"Ref {inv['invoice_no']}   Date {g._date_text('broadliner_b', inv['date'])}   Sheet {pi + 1} of {len(chunks)}")
        cols = [("QTY", 22, "r"), ("U/M", 26, "l"), ("PRODUCT DESCRIPTION", 42, "l"), ("SIZE", 140, "l"), ("PRICE", 192, "r"),
                ("DISC %", 212, "r"), ("VAT", 228, "l"), ("NET VALUE", 285, "r")]
        y = H - 34 * mm
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#dddddd"))
        c.rect(8 * mm, y - 2 * mm, W - 16 * mm, 6.5 * mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        for t, x, al in cols:
            (c.drawRightString if al == "r" else c.drawString)(x * mm, y, t)
        y -= 8 * mm
        c.setFont("Helvetica", 8.5)
        for ln in chunk:
            vals = [g.fq(ln["qty"]), g.UNIT_CODE[ln["unit"]], ln["description"], ln["pack_size"], g.money(ln["unit_price"]),
                    f"{ln['discount_pct']}.0" if ln["discount_pct"] else "", _VCODE[ln["vat_rate"]], g.money(ln["line_total"])]
            for (t, x, al), v in zip(cols, vals):
                (c.drawRightString if al == "r" else c.drawString)(x * mm, y, v)
            c.setStrokeColor(colors.HexColor("#bbbbbb"))
            c.line(8 * mm, y - 2 * mm, W - 8 * mm, y - 2 * mm)
            c.setStrokeColor(colors.black)
            y -= 8 * mm
        if pi == len(chunks) - 1:
            t = inv["totals"]
            c.setFont("Helvetica", 8)
            c.drawString(8 * mm, 30 * mm, "VAT codes:  Z = zero rate 0%    R = reduced rate 5%    S = standard rate 20%")
            yy = 30 * mm
            c.setFont("Helvetica-Bold", 10)
            for label, v in (("GOODS", t["net"]), ("VAT", t["vat"]), ("INVOICE TOTAL" if not inv["credit_note"] else "CREDIT TOTAL", t["gross"])):
                c.drawRightString(255 * mm, yy, label)
                c.drawRightString(285 * mm, yy, ("-" if v < 0 else "") + "GBP " + g.money(abs(v)))
                yy -= 6 * mm
        else:
            c.setFont("Helvetica-Oblique", 8)
            c.drawRightString(W - 10 * mm, 14 * mm, "Totals on last sheet")
        c.showPage()


# ------------------------------------------------------------------ greengrocer (monospaced A5 delivery note)
GREENGROCER = {"name": "Marrow Lane Greengrocers", "addr": ["3 Marrow Lane Market", "Ashby Vale, AV1 9QT"], "vat": "GB 000 3334 43", "prefix": "ML"}
GREENGROCER_CATALOG = [
    ("POTATO MARIS PIPER 25KG", "25kg", "each", 14, 20, 0, False), ("TOMATOES VINE 6KG BOX", "6kg", "box", 12, 18, 0, False),
    ("ONION BROWN 10KG", "10kg", "each", 7, 11, 0, False), ("CARROT LOOSE 20KG", "20kg", "each", 9, 14, 0, False),
    ("LEMONS 15CT BOX", "15", "box", 5, 9, 0, False), ("LETTUCE COS", "", "each", 0.8, 1.4, 0, False),
    ("AVOCADO RIPE 12S", "12", "box", 11, 17, 0, False), ("MUSHROOM CHESTNUT 3KG", "3kg", "box", 9, 14, 0, False),
    ("PARSLEY FLAT BUNCH", "", "each", 0.6, 1.1, 0, False), ("BASIL POT LIVING", "", "each", 1.2, 2.0, 0, False),
    ("CAULIFLOWER", "", "each", 1.1, 1.9, 0, False), ("BANANAS", "", "kg", 0.9, 1.5, 0, True),
    ("BROCCOLI", "", "kg", 2, 3.5, 0, True), ("RASPBERRIES 12X125G", "12x125g", "case", 14, 22, 0, False),
    ("PEPPERS RED MIXED 5KG", "5kg", "case", 11, 17, 0, False), ("COURGETTE", "", "kg", 1.6, 2.8, 0, True),
    ("SPINACH BABY 500G", "500g", "each", 2.4, 3.8, 0, False), ("GARLIC WHITE", "", "kg", 5, 8, 0, True),
    ("CELERY HEAD", "", "each", 0.9, 1.5, 0, False), ("APPLE BRAMLEY 12KG", "12kg", "box", 14, 21, 0, False),
    ("EGGS FREE RANGE DOZEN", "dozen", "each", 2.4, 3.6, 0, False), ("CARRIER BAGS 100", "100", "pack", 3, 5, 20, False),
]


def render_greengrocer(c, inv):
    W, H = 148 * mm, 210 * mm
    sup = g.SUPPLIERS["greengrocer"]
    chunks = g._chunks(inv["lines"], g.ROWS_PER_PAGE["greengrocer"])
    for pi, chunk in enumerate(chunks):
        c.setFont("Courier-Bold", 14)
        c.drawString(10 * mm, H - 14 * mm, sup["name"].upper())
        c.setFont("Courier", 8)
        c.drawString(10 * mm, H - 19 * mm, "; ".join(sup["addr"]))
        c.drawString(10 * mm, H - 24 * mm, "VAT " + sup["vat"])
        c.setFont("Courier-Bold", 10)
        c.drawString(10 * mm, H - 33 * mm, ("CREDIT NOTE " if inv["credit_note"] else "DELIVERY NOTE ") + inv["invoice_no"])
        c.drawRightString(138 * mm, H - 33 * mm, g._date_text("greengrocer", inv["date"]))
        c.setFont("Courier", 8)
        c.drawString(10 * mm, H - 38 * mm, "To: Copper Kettle Kitchen            pg %d/%d" % (pi + 1, len(chunks)))
        y = H - 47 * mm
        c.drawString(10 * mm, y, "QTY    ITEM                              PRICE     AMOUNT")
        c.drawString(10 * mm, y - 3 * mm, "-" * 74)
        y -= 8 * mm
        c.setFont("Courier", 8.5)
        for ln in chunk:
            c.drawString(10 * mm, y, g.fq(ln["qty"]))
            c.drawString(24 * mm, y, ln["description"][:30])
            c.drawRightString(112 * mm, y, g.money(ln["unit_price"]) + ("/kg" if ln["unit"] == "kg" else " ea"))
            c.drawRightString(138 * mm, y, g.money(ln["line_total"]) + ("*" if ln["vat_rate"] else ""))
            y -= 6.5 * mm
        if pi == len(chunks) - 1:
            c.drawString(10 * mm, y, "-" * 74)
            g._totals_block(c, inv, 138 * mm, y - 6 * mm, font="Courier-Bold", size=9)
            c.setFont("Courier", 7)
            c.drawString(10 * mm, 14 * mm, "Items marked * carry 20% VAT. All other goods are zero rated.")
        c.showPage()


# ------------------------------------------------------------------ dairy and drinks wholesaler (boxed portrait, VAT summary)
DAIRY_DRINKS = {"name": "Tidewater Dairy & Drinks Ltd", "addr": ["Dock Road Warehouse 6", "Portleigh, PL7 3DR"], "vat": "GB 000 4445 54", "prefix": "TW"}
DAIRY_DRINKS_CATALOG = [
    ("MILK FULL FAT 6X2L", "6x2L", "case", 7, 10, 0, False), ("MILK SEMI 12X1L", "12x1L", "case", 8, 12, 0, False),
    ("CREAM DOUBLE 6X1L", "6x1L", "case", 14, 19, 0, False), ("BUTTER SALTED 40X250G", "40x250g", "case", 70, 90, 0, False),
    ("CHEESE CHEDDAR 5KG BLOCK", "5kg", "each", 24, 33, 0, False), ("YOGHURT NATURAL 6X1KG", "6x1kg", "case", 11, 16, 0, False),
    ("COLA CLASSIC 24X330ML", "24x330ml", "case", 11, 15, 20, False), ("WATER SPARKLING 12X75CL", "12x75cl", "case", 8, 12, 20, False),
    ("WINE RED MERLOT 6X75CL", "6x75cl", "case", 36, 48, 20, False), ("WINE WHITE PINOT 6X75CL", "6x75cl", "case", 34, 46, 20, False),
    ("LAGER PREMIUM 4.2% 24X500ML", "24x500ml", "case", 28, 38, 20, False), ("JUICE ORANGE 12X1L", "12x1L", "case", 12, 17, 20, False),
    ("TONIC SLIM 24X200ML", "24x200ml", "case", 10, 15, 20, False), ("CIDER KEG 50L", "50L", "each", 95, 125, 20, False),
    ("GIN LONDON DRY 6X70CL", "6x70cl", "case", 96, 132, 20, False), ("GINGER BEER 12X200ML", "12x200ml", "case", 8, 12, 20, False),
    ("COFFEE BEANS ESPRESSO 1KG", "1kg", "each", 11, 16, 0, False), ("TEA BAGS BREAKFAST 1100", "1100", "box", 12, 18, 0, False),
    ("PROSECCO DOC 6X75CL", "6x75cl", "case", 42, 58, 20, False), ("EGGS FREE RANGE 15 DOZEN", "180", "case", 22, 29, 0, False),
    ("ICE CREAM VANILLA 4L", "4L", "each", 7, 11, 0, False), ("JUICE APPLE 12X1L", "12x1L", "case", 11, 16, 20, False),
    ("VODKA 6X70CL", "6x70cl", "case", 84, 112, 20, False), ("DELIVERY CHARGE", "", "each", 8, 15, 20, False),
]


def render_dairy_drinks(c, inv):
    W, H = 210 * mm, 297 * mm
    sup = g.SUPPLIERS["dairy_drinks"]
    chunks = g._chunks(inv["lines"], g.ROWS_PER_PAGE["dairy_drinks"])
    for pi, chunk in enumerate(chunks):
        c.setFillColor(colors.HexColor("#0b6e4f"))
        c.rect(0, H - 14 * mm, W, 14 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(12 * mm, H - 10 * mm, "TIDEWATER DAIRY & DRINKS")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(12 * mm, H - 22 * mm, ", ".join(sup["addr"]) + "   VAT No. " + sup["vat"])
        c.setFont("Helvetica-Bold", 13)
        c.drawString(12 * mm, H - 33 * mm, "CREDIT NOTE" if inv["credit_note"] else "SALES INVOICE")
        x = 12
        for label, val in (("Document", inv["invoice_no"]), ("Tax point", g._date_text("dairy_drinks", inv["date"])), ("Account", "CK-0417"), ("Page", f"{pi + 1}/{len(chunks)}")):
            c.setFont("Helvetica", 7)
            c.rect(x * mm, H - 50 * mm, 44 * mm, 11 * mm)
            c.drawString((x + 2) * mm, H - 43 * mm, label)
            c.setFont("Helvetica-Bold", 9)
            c.drawString((x + 2) * mm, H - 48 * mm, val)
            x += 46
        y = H - 62 * mm
        cols = [("PRODUCT", 12, "l"), ("SIZE", 100, "l"), ("QTY", 134, "r"), ("PRICE", 156, "r"), ("VAT", 168, "r"), ("LINE VALUE", 198, "r")]
        c.setFont("Helvetica-Bold", 8)
        c.line(12 * mm, y + 5 * mm, 198 * mm, y + 5 * mm)
        for t, xx, al in cols:
            (c.drawRightString if al == "r" else c.drawString)(xx * mm, y, t)
        c.line(12 * mm, y - 2 * mm, 198 * mm, y - 2 * mm)
        y -= 9 * mm
        c.setFont("Helvetica", 9)
        for ln in chunk:
            vals = [ln["description"], ln["pack_size"], g.fq(ln["qty"]), g.money(ln["unit_price"]), "S" if ln["vat_rate"] else "Z", g.money(ln["line_total"])]
            for (t, xx, al), v in zip(cols, vals):
                (c.drawRightString if al == "r" else c.drawString)(xx * mm, y, v)
            y -= 8 * mm
        if pi == len(chunks) - 1:
            c.line(12 * mm, y + 4 * mm, 198 * mm, y + 4 * mm)
            y -= 4 * mm
            c.setFont("Helvetica", 8)
            c.drawString(12 * mm, y, "VAT SUMMARY   Z = 0%   S = 20%")
            for rate, code in ((0, "Z"), (20, "S")):
                goods = sum(ln["line_total"] for ln in inv["lines"] if ln["vat_rate"] == rate)
                y -= 5 * mm
                c.drawString(12 * mm, y, f"{code}   goods {g.money(goods)}   vat {g.money(inv['totals']['vat_by_rate'].get(str(rate), 0.0))}")
            g._totals_block(c, inv, 198 * mm, y + 3 * mm, label_net="Goods", size=10)
        c.showPage()


g.register_layout("broadliner_b", BROADLINER_B, BROADLINER_B_CATALOG, 11, render_broadliner_b, (297 * mm, 210 * mm), "%d-%b-%y")
g.register_layout("greengrocer", GREENGROCER, GREENGROCER_CATALOG, 16, render_greengrocer, (148 * mm, 210 * mm), "%d.%m.%y")
g.register_layout("dairy_drinks", DAIRY_DRINKS, DAIRY_DRINKS_CATALOG, 14, render_dairy_drinks, (210 * mm, 297 * mm), "%d-%b-%Y")
