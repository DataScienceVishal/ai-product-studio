#!/usr/bin/env python3
"""Realism supplement (T-56 slice S7): 12 synthetic sheets with the wording and layout problems found in
benchmark/REALISM.md (items 1-5). Seed 20261126. Reported separately; pass marks unchanged; it does not decide the
kill test (benchmark/KILL_TEST_AMENDMENT_4.md). The 30 test sheets, the 5 tuning sheets and their truth are not touched.

Usage: python3 supplement.py [--out supplement]
Outputs under --out: data/sheets/S801.pdf.., data/truth/S801.json.., manifest.json. Byte-for-byte reproducible
(the AES-encrypted sheet is built with seeded randomness).
"""
import argparse
import contextlib
import io
import json
import os
import random
import secrets
from pathlib import Path

import generate as g
import taxonomy as tx

HERE = Path(__file__).resolve().parent
SEED = 20261126
RAM = {"PET": "plastic", "rPET": "plastic", "PETG": "plastic", "HDPE": "plastic", "PP": "plastic", "PS": "plastic",
       "PVC": "plastic", "PE/PET laminate": "plastic", "glass": "glass", "aluminium": "aluminium", "steel": "steel",
       "paper": "paper_board", "corrugated board": "paper_board", "kraft paper": "paper_board"}


def pres(value, quote, page=1):
    return {"status": "present", "value": value, "refs": [{"page": page, "quote": quote}]}


MISS = {"status": "missing"}


def comp(name, material, colour, weight, feats=None):
    feats = feats or {}
    assert set(feats) <= set(tx.PLAUSIBLE[name]), (name, feats)
    return {"name": name, "material": material, "colour": colour, "weight_g": weight,
            "features": {k: feats.get(k, MISS) for k in tx.PLAUSIBLE[name]},
            "ram_category": RAM[material["value"]] if material["status"] == "present" else "missing"}


class Sheet:
    """A Doc plus the truth components being collected; helpers add a row and return its page."""

    def __init__(self, rng):
        self.doc = g.Doc()
        self.rng = rng
        self.supplier = rng.choice(g.SUPPLIERS)

    def kv(self, label, value):
        self.doc.cols(label, value)
        return self.doc.page

    def text(self, s, kind="text"):
        self.doc.text(s, kind)
        return self.doc.page


def wt(rng, lo, hi, nd=1):
    return round(rng.uniform(lo, hi), nd)


# ------------------------------------------------------------------ the twelve sheets

def s801(rng):  # REALISM item 1: weight with tolerance, "gm" and oz
    s = Sheet(rng)
    d = s.doc
    s.text("Packaging specification: 500 ml water bottle and food tray", "title")
    d.text("")
    wb = wt(rng, 30, 44, 2)
    s.text("Bottle", "h")
    pm = s.kv("Material", "PET")
    pc = s.kv("Colour", "Clear")
    pw = s.kv("Weight", f"{wb:.2f}gm ± 2.00gm")
    pl = s.kv("Label", "permanent paper label")
    s.kv("Closure", "n/a")
    d.text("")
    oz = round(rng.uniform(1.2, 1.6), 2)
    s.text("Food tray", "h")
    tm = s.kv("Material", "PS")
    tc = s.kv("Colour", "White")
    tw = s.kv("Weight", f"{oz:.2f} oz (+/- 0.04 oz)")
    s.text("Notes: weights are nominal, tolerance as shown.")
    comps = [comp("bottle", pres("PET", "PET", pm), pres("clear", "Clear", pc),
                  pres(round(wb, 2), f"{wb:.2f}gm ± 2.00gm", pw),
                  {"label": pres("paper label, permanent", "permanent paper label", pl)}),
             comp("tray", pres("PS", "PS", tm), pres("white", "White", tc),
                  pres(round(oz * tx.G_PER_OZ, 2), f"{oz:.2f} oz (+/- 0.04 oz)", tw))]
    return s, comps, dict(items=[1], template="table")


def s802(rng):  # item 1: unit only in the row label
    s = Sheet(rng)
    d = s.doc
    s.text("Specification: HDPE cap and PET bottle", "title")
    d.text("")
    wc, wb = wt(rng, 2.5, 6), wt(rng, 30, 55)
    s.text("Closure", "h")
    cm = s.kv("Material", "HDPE")
    cc = s.kv("Colour", "Natural")
    cw = s.kv("Weight (g)", f"{wc}")
    s.kv("Pallet weight (kg)", "412")
    d.text("")
    s.text("Bottle", "h")
    bm = s.kv("Resin", "PET")
    bc = s.kv("Shade", "Amber")
    bw = s.kv("Unit weight (gms)", f"{wb}")
    s.kv("Case weight (kg)", "8.4")
    comps = [comp("cap", pres("HDPE", "HDPE", cm), pres("natural", "Natural", cc), pres(wc, f"Weight (g) | {wc}", cw)),
             comp("bottle", pres("PET", "PET", bm), pres("amber", "Amber", bc), pres(wb, f"Unit weight (gms) | {wb}", bw))]
    return s, comps, dict(items=[1], template="two_column")


def s803(rng):  # item 4: blends (largest share, tie -> PET)
    s = Sheet(rng)
    d = s.doc
    s.text("Material declaration: PET bottle and tray", "title")
    d.text("")
    wb, wt_ = wt(rng, 24, 40), wt(rng, 10, 26)
    s.text("Bottle", "h")
    bm = s.kv("Material", "rPET 30% + PET 70%")
    bc = s.kv("Colour", "Clear")
    bw = s.kv("Weight", f"{wb} g")
    d.text("")
    s.text("Tray", "h")
    tm = s.kv("Material", "50% rPET / 50% PET")
    tc = s.kv("Colour", "Black")
    tw = s.kv("Weight", f"{wt_} g")
    comps = [comp("bottle", pres("PET", "rPET 30% + PET 70%", bm), pres("clear", "Clear", bc), pres(wb, f"{wb} g", bw)),
             comp("tray", pres("PET", "50% rPET / 50% PET", tm), pres("black", "Black", tc), pres(wt_, f"{wt_} g", tw))]
    return s, comps, dict(items=[4], template="table")


def s804(rng):  # item 4: recycled content in the cell, "Finish: Clear", marketing lines, out-of-vocab colour
    s = Sheet(rng)
    d = s.doc
    s.text("Eco range: tray and shipper", "title")
    d.text("")
    wt_, wc = wt(rng, 14, 24), wt(rng, 60, 90)
    s.text("Tray", "h")
    tm = s.kv("Material", "rPET (PCR 100%)")
    tc = s.kv("Finish", "Clear")
    tw = s.kv("Weight", f"{wt_} g")
    s.text("100% recyclable. Recycling code 1 (PET).")
    d.text("")
    s.text("Shipper", "h")
    cm = s.kv("Material", "minimum of 25% PCR kraft paper")
    s.kv("Colour", "Variable Coloured")
    cw = s.kv("Weight", f"{wc} g")
    s.text("Recyclable*")
    s.text("*where kerbside collection exists.")
    comps = [comp("tray", pres("rPET", "rPET (PCR 100%)", tm), pres("clear", "Clear", tc), pres(wt_, f"{wt_} g", tw)),
             comp("outer carton", pres("kraft paper", "minimum of 25% PCR kraft paper", cm), MISS,
                  pres(wc, f"{wc} g", cw))]  # "Variable Coloured" names no vocabulary colour: missing
    return s, comps, dict(items=[4], template="table")


def s805(rng):  # item 4: colour code only ("WhiteSolid W1229" is not in the closed vocabulary -> missing)
    s = Sheet(rng)
    d = s.doc
    s.text("Screw cap 38 mm, tamper evident", "title")
    d.text("")
    w = wt(rng, 3, 8)
    pm = s.kv("Material", "PP")
    s.kv("Colour", "WhiteSolid")
    s.kv("Colour ID", "W1229")
    pw = s.kv("Weight", f"{w} g")
    s.kv("Liner", "TBC")
    s.text("Resin identification: SPI code 5 (PP). 100% recyclable.")
    comps = [comp("cap", pres("PP", "PP", pm), MISS, pres(w, f"{w} g", pw))]
    return s, comps, dict(items=[4], template="table")


def s806(rng):  # item 3: catalogue, one target item
    s = Sheet(rng)
    d = s.doc
    s.text("Product code PB-250-24: 250 ml round bottle, 24/410 neck", "title")
    d.text("")
    s.text("Range overview. Weights are nominal.")
    d.text("")
    wd = [70, 65, 55, 80, 80, 80]
    d.row(["Code", "Volume", "Neck", "Material", "Colour", "Weight"], wd, header=True)
    codes = [("PB-100-24", "100 ml", "24/410", "PET", "Clear"), ("PB-250-24", "250 ml", "24/410", "PET", "Clear"),
             ("PB-250-28", "250 ml", "28/410", "PET", "Amber"), ("PB-500-28", "500 ml", "28/410", "PET", "Clear"),
             ("PB-500-38", "500 ml", "38/400", "PET", "Green"), ("HB-250-24", "250 ml", "24/410", "HDPE", "White"),
             ("HB-500-28", "500 ml", "28/410", "HDPE", "Natural"), ("HB-1000-38", "1000 ml", "38/400", "HDPE", "White")]
    weights = [round(rng.uniform(14, 90), 1) for _ in codes]
    target = 1
    page = d.page
    for (c, v, n, m, col), w in zip(codes, weights):
        d.row([c, v, n, m, col, f"{w} g"], wd)
    c, v, n, m, col = codes[target]
    w = weights[target]
    comps = [comp("bottle", pres(m, m, page), pres(col.lower(), col, page), pres(w, f"{w} g", page))]
    return s, comps, dict(items=[3], template="catalogue", target_item=c)


def s807(rng):  # item 3: "various closure options" and secondary packaging with no weights
    s = Sheet(rng)
    d = s.doc
    s.text("500 ml amber bottle, 28/410", "title")
    d.text("")
    w = wt(rng, 40, 60)
    pm = s.kv("Material", "PET")
    pc = s.kv("Colour", "Amber")
    pw = s.kv("Weight", f"{w} g")
    s.kv("Closure", "Various 28/410 stock closure options")
    d.text("")
    s.text("Secondary packaging", "h")
    s.kv("Inner liner", "MDPE liner")
    s.kv("Outer box", "brown cardboard box")
    s.kv("Pallet", "standard pallet, stretch wrapped")
    comps = [comp("bottle", pres("PET", "PET", pm), pres("amber", "Amber", pc), pres(w, f"{w} g", pw))]
    return s, comps, dict(items=[3], template="table")


def s808(rng):  # item 2 / D3: areal and case weights only -> weight missing
    s = Sheet(rng)
    d = s.doc
    s.text("Converted materials: pouch film, paper label stock, shipper board", "title")
    d.text("")
    s.text("Pouch film", "h")
    fm = s.kv("Construction", "PE/PET laminate")
    fc = s.kv("Colour", "Clear")
    s.kv("Thickness (µm)", "80")
    s.kv("Gauge", "320 gauge")
    s.kv("Case weight (kg)", "12.4")
    d.text("")
    s.text("Label stock", "h")
    lm = s.kv("Substrate", "paper")
    lc = s.kv("Colour", "White")
    s.kv("Grammage", "80 gsm")
    s.kv("Case weight (lb)", "22")
    d.text("")
    s.text("Shipper board", "h")
    om = s.kv("Material", "corrugated board")
    oc = s.kv("Colour", "Brown")
    s.kv("Board weight", "450 gsm")
    s.kv("Pallet weight (kg)", "380")
    comps = [comp("pouch", pres("PE/PET laminate", "PE/PET laminate", fm), pres("clear", "Clear", fc), MISS),
             comp("label", pres("paper", "paper", lm), pres("white", "White", lc), MISS),
             comp("outer carton", pres("corrugated board", "corrugated board", om), pres("brown", "Brown", oc), MISS)]
    return s, comps, dict(items=[2], template="table")


def s809(rng):  # item 5: two blocks, labels first, values second (reading-order scramble)
    s = Sheet(rng)
    w = wt(rng, 2.5, 7)
    labels = ["Item", "Material", "Colour", "Net weight", "Liner", "Print"]
    values = ["Screw cap", "polypropylene", "Blue", f"{w} g", "polyethylene liner", "no print, no coating"]
    s.layout = ("two_block", "Cap specification", labels, values)
    comps = [comp("cap", pres("PP", "polypropylene"), pres("blue", "Blue"), pres(w, f"{w} g"),
                  {"liner": pres("PE liner", "polyethylene liner"),
                   "ink_coating": pres("no ink or coating", "no print, no coating")})]
    return s, comps, dict(items=[5], template="two_block")


def s810(rng):  # item 5: multi-column table with units in the headers
    s = Sheet(rng)
    d = s.doc
    s.text("Component table, 330 ml still water pack", "title")
    d.text("")
    wd = [90, 90, 70, 100, 100]
    d.row(["Item", "Material", "Colour", "Height (mm)", "Weight"], wd, header=True)
    page = d.page
    wb, wc, wl = wt(rng, 20, 30), wt(rng, 2, 4), wt(rng, 0.8, 2)
    d.row(["Bottle", "PET", "Clear", "180", f"{wb} g"], wd)
    d.row(["Screw cap", "PP", "Blue", "14", f"{wc} g"], wd)
    d.row(["Wrap label", "PP film", "White", "60", f"{wl} g"], wd)
    comps = [comp("bottle", pres("PET", "PET", page), pres("clear", "Clear", page), pres(wb, f"{wb} g", page)),
             comp("cap", pres("PP", "PP", page), pres("blue", "Blue", page), pres(wc, f"{wc} g", page)),
             comp("label", pres("PP", "PP film", page), pres("white", "White", page), pres(wl, f"{wl} g", page))]
    return s, comps, dict(items=[5], template="unit_header")


def s811(rng):  # item 5: one page in French
    s = Sheet(rng)
    d = s.doc
    s.text("Specification sheet: 1 litre bottle", "title")
    d.text("")
    wb = wt(rng, 35, 50)
    pm = s.kv("Material", "HDPE")
    pc = s.kv("Colour", "White")
    pw = s.kv("Weight", f"{wb} g")
    d.newpage()
    s.text("Fiche technique : bouchon", "title")
    d.text("")
    wc = wt(rng, 2.5, 5)
    fm = s.kv("Matière", "PP")
    fc = s.kv("Couleur", "transparent")
    fw = s.kv("Poids net", f"{wc} g")
    s.kv("Doublure", "n/a")
    comps = [comp("bottle", pres("HDPE", "HDPE", pm), pres("white", "White", pc), pres(wb, f"{wb} g", pw)),
             comp("cap", pres("PP", "PP", fm), pres("clear", "transparent", fc), pres(wc, f"{wc} g", fw))]
    return s, comps, dict(items=[5], template="table")


def s812(rng):  # item 5: AES-128 encrypted, empty user password
    s = Sheet(rng)
    d = s.doc
    s.text("Closure and bottle, 750 ml", "title")
    d.text("")
    wc, wb = wt(rng, 3, 7), wt(rng, 55, 75)
    cm = s.kv("Material", "HDPE")
    cc = s.kv("Colour", "Black")
    cw = s.kv("Cap weight", f"{wc} g")
    d.text("")
    bm = s.kv("Bottle material", "glass")
    bc = s.kv("Bottle colour", "Green")
    bw = s.kv("Bottle weight", f"{wb} g")
    comps = [comp("cap", pres("HDPE", "HDPE", cm), pres("black", "Black", cc), pres(wc, f"{wc} g", cw)),
             comp("bottle", pres("glass", "glass", bm), pres("green", "Green", bc), pres(wb, f"{wb} g", bw))]
    return s, comps, dict(items=[5], template="table", encrypted=True)


SHEETS = [s801, s802, s803, s804, s805, s806, s807, s808, s809, s810, s811, s812]


# ------------------------------------------------------------------ rendering

def render_two_block(title, labels, values, header, form):
    """Labels drawn first, values second, so the plain text layer lists every label before any value."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    W, H = A4
    c.setFont("Helvetica", 8)
    c.drawString(50, H - 35, header)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, H - 65, title)
    c.setFont("Helvetica", 10)
    for i, lab in enumerate(labels):
        c.drawString(50, H - 110 - 22 * i, lab)
    for i, val in enumerate(values):
        c.drawString(250, H - 110 - 22 * i, val)
    c.setFont("Helvetica", 8)
    c.drawString(50, 30, "Page 1 of 1")
    c.drawString(400, 30, form)
    c.showPage()
    c.save()
    return buf.getvalue()


@contextlib.contextmanager
def seeded_randomness(seed):
    """pypdf draws IVs, salts and the file id from os.urandom / secrets; seed them so the output is reproducible."""
    rng = random.Random(seed)
    old = os.urandom, secrets.token_bytes
    os.urandom = lambda n: rng.randbytes(n)
    secrets.token_bytes = lambda n=32: rng.randbytes(n)
    try:
        yield
    finally:
        os.urandom, secrets.token_bytes = old


def encrypt_aes128(pdf, seed):
    from pypdf import PdfReader, PdfWriter
    with seeded_randomness(seed):
        w = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
        w.encrypt("", owner_password="studio-owner", algorithm="AES-128")
        out = io.BytesIO()
        w.write(out)
    return out.getvalue()


def generate_supplement(out, seed=SEED):
    out = Path(out)
    for d in ("data/sheets", "data/truth"):
        (out / d).mkdir(parents=True, exist_ok=True)
    manifest = dict(seed=seed, supplement=[], note="Realism supplement, reported separately; see KILL_TEST_AMENDMENT_4.md")
    truths = []
    for n, fn in enumerate(SHEETS, start=1):
        sid = f"S8{n:02d}"
        rng = random.Random(f"{seed}-{sid}")
        s, comps, meta = fn(rng)
        header, form = f"{s.supplier}  |  Packaging specification", f"Form PS-{rng.randint(100, 999)}"
        if hasattr(s, "layout"):
            _, title, labels, values = s.layout
            pdf, pages = render_two_block(title, labels, values, header, form), 1
        else:
            pdf, _ = g.render_pdf(s.doc, header, form, False, rng)
            pages = len(s.doc.pages)
        if meta.get("encrypted"):
            pdf = encrypt_aes128(pdf, f"{seed}-{sid}-enc")
        truth = {"sheet_id": sid, "tier": "moderate", "layout": "supplement", "source": "synthetic", "seed": seed,
                 "template": meta["template"], "components": comps}
        if meta.get("target_item"):
            truth["target_item"] = meta["target_item"]
        (out / "data/sheets" / f"{sid}.pdf").write_bytes(pdf)
        (out / "data/truth" / f"{sid}.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n")
        row = dict(sheet_id=sid, tier="moderate", layout="supplement", template=meta["template"], scanned=False,
                   pages=pages, realism_items=meta["items"], encrypted=bool(meta.get("encrypted")))
        if meta.get("target_item"):
            row["target_item"] = meta["target_item"]
        manifest["supplement"].append(row)
        truths.append(truth)
    manifest["stats"] = g.stats(truths)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "supplement"))
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    m = generate_supplement(a.out, a.seed)
    print(f"generated {len(m['supplement'])} supplement sheets into {a.out}")
    print(json.dumps(m["stats"], indent=2))
