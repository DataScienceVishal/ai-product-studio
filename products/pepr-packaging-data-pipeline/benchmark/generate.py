#!/usr/bin/env python3
"""Deterministic generator of synthetic supplier packaging spec sheets (T-56 slice 2).

Usage: python3 generate.py [--out data] [--seed 20261124] [--tuning-seed 20261125]

The truth JSON is written from the same data model that renders the PDF, so it is
exact. Every present value carries the page and a quote that appears on that page.
Scanned sheets are rendered as text PDFs, then rasterised, rotated and noised.

Outputs under --out:
  sheets/S001.pdf..S030.pdf, truth/S001.json..   the 30 test sheets
  tuning/S901.pdf..S905.pdf, tuning_truth/...    5 held-out tuning sheets (other seed)
  manifest.json                                  tiers, layouts, messiest 10, tuning ids
Tuning ids use S9xx because truth.schema.json requires ^S[0-9]{3}$.
"""
import argparse
import io
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20261124
TUNING_SEED = 20261125
G_PER_OZ = 28.3495

# name -> list of (value, ram, display_clean, display_abbrev, accepted)
COMPONENTS = {
    "bottle": [("PET", "plastic", "PET", "PET", ["polyethylene terephthalate"]),
               ("HDPE", "plastic", "HDPE", "HDPE nat.", ["high-density polyethylene"]),
               ("glass", "glass", "soda-lime glass", "soda-lime glass", ["soda lime glass"])],
    "cap": [("PP", "plastic", "PP", "PP blk", ["polypropylene"]),
            ("HDPE", "plastic", "HDPE", "HDPE", ["high-density polyethylene"]),
            ("aluminium", "aluminium", "aluminium", "Al", ["aluminum"])],
    "label": [("paper", "paper_board", "paper", "paper", []),
              ("PP", "plastic", "PP film", "PP film", ["polypropylene"])],
    "outer carton": [("corrugated board", "paper_board", "corrugated board", "corr. board", []),
                     ("kraft paper", "paper_board", "kraft paper", "kraft", [])],
    "sleeve": [("PETG", "plastic", "PETG", "PETG", []), ("PVC", "plastic", "PVC", "PVC", [])],
    "tray": [("rPET", "plastic", "rPET", "rPET", ["recycled PET"]), ("PS", "plastic", "PS", "PS", ["polystyrene"])],
    "can": [("aluminium", "aluminium", "aluminium", "Al", ["aluminum"]),
            ("steel", "steel", "tinplate steel", "tinplate", ["tinplate"])],
    "pouch": [("PE/PET laminate", "plastic", "PE/PET laminate", "PE/PET lam.", [])],
}
WEIGHT_RANGE = {"bottle": (18, 60), "cap": (2, 9), "label": (0.5, 3), "outer carton": (60, 180),
                "sleeve": (1, 4), "tray": (8, 30), "can": (12, 35), "pouch": (4, 12)}
COLOURS = {"clear": ["clear"], "natural": ["natural", "nat."], "black": ["black", "blk"],
           "white": ["white"], "amber": ["amber"], "green": ["green"], "brown": ["brown"], "blue": ["blue"]}
FEATURES = {
    "label": ["full wrap PP label", "paper label, wash-off"],
    "closure": ["PP cap, no liner", "HDPE cap with PE liner"],
    "ink_coating": ["UV-cured ink", "water-based varnish"],
    "sleeve": ["PVC shrink sleeve", "PETG shrink sleeve"],
    "adhesive": ["hot-melt adhesive", "water-based adhesive"],
    "barrier_layer": ["EVOH barrier layer", "no barrier layer"],
}
FEATURE_LABEL = {"label": "Label", "closure": "Closure", "ink_coating": "Ink / coating",
                 "sleeve": "Sleeve", "adhesive": "Adhesive", "barrier_layer": "Barrier layer"}
SUPPLIERS = ["Northfield Packaging Ltd", "Calder Plastics", "Brightwell Containers", "Hartley Print and Pack",
             "Mersey Glassworks", "Oakridge Converters", "Tamar Closures", "Bexley Board Co"]

# sheet number -> (tier, layout, style, n_components, options)
def plan():
    p = {}
    for n in range(1, 11):
        p[n] = ("clean", "table", "table", 1, dict(units=["g"], missing=0, conflict=0, abbrev=False, scanned=False))
    for n in (11, 12, 13):
        p[n] = ("moderate", "prose", "prose", 2, dict(units=["g", "kg"], missing=1, conflict=0, abbrev=False, scanned=False))
    for n in (14, 15, 16):
        p[n] = ("moderate", "mixed_units", "matrix", 3, dict(units=["g", "kg", "oz", "mg"], missing=0, conflict=0, abbrev=False, scanned=False))
    for n in (17, 18):
        p[n] = ("moderate", "multi_component", "matrix", 4, dict(units=["g", "kg"], missing=1, conflict=0, abbrev=False, scanned=False))
    for n in (19, 20):
        p[n] = ("moderate", "missing_fields", "table", 2, dict(units=["g", "oz"], missing=3, conflict=0, abbrev=False, scanned=False))
    styles = ["prose", "matrix", "table", "matrix", "prose"]
    for i, n in enumerate(range(21, 26)):
        p[n] = ("messy", "scanned", styles[i], 3, dict(units=["g", "kg", "oz", "mg"], missing=2, conflict=1 if i % 2 == 0 else 0, abbrev=True, scanned=True))
    for i, n in enumerate(range(26, 31)):
        p[n] = ("messy", "contradictory", ["table", "matrix", "prose", "matrix", "table"][i], 3,
                dict(units=["g", "kg", "oz"], missing=2, conflict=2, abbrev=True, scanned=False))
    return p


def fmt_num(x, nd=3):
    return f"{x:.{nd}f}".rstrip("0").rstrip(".") if "." in f"{x:.{nd}f}" else f"{x:.{nd}f}"


def weight_display(w, unit):
    """Return (display string, truth grams)."""
    if unit == "g":
        return f"{fmt_num(w, 1)} g", round(w, 1)
    if unit == "kg":
        s = fmt_num(w / 1000, 4)
        return f"{s} kg", round(float(s) * 1000, 1)
    if unit == "mg":
        mg = int(round(w * 1000))
        return f"{mg} mg", round(mg / 1000, 1)
    s = f"{w / G_PER_OZ:.3f}"
    return f"{s} oz", round(float(s) * G_PER_OZ, 1)


class Doc:
    PER_PAGE = 38

    def __init__(self):
        self.pages = [[]]
        self.count = 0

    @property
    def page(self):
        return len(self.pages)

    def newpage(self):
        self.pages.append([])
        self.count = 0

    def add(self, item):
        if self.count >= self.PER_PAGE:
            self.newpage()
        self.pages[-1].append(item)
        self.count += 1
        return self.page

    def text(self, s, kind="text"):
        assert len(s) <= 95, s
        return self.add((kind, s))

    def row(self, cells, widths, header=False):
        return self.add(("row", cells, widths, header))


def build_sheet(sid, seed, tier, layout, style, n_comp, opt):
    rng = random.Random(f"{seed}-{sid}")
    names = rng.sample(list(COMPONENTS), n_comp)
    supplier = rng.choice(SUPPLIERS)
    comps = []
    # decide missing fields: list of (comp idx, field)
    slots = [(i, f) for i in range(n_comp) for f in ("material", "colour", "weight_g")]
    miss = set(rng.sample(slots, opt["missing"])) if opt["missing"] else set()
    cand = [i for i in range(n_comp) if (i, "weight_g") not in miss]
    conf_idx = set(rng.sample(cand, min(opt["conflict"], len(cand)))) if opt["conflict"] else set()
    for i, name in enumerate(names):
        mat = rng.choice(COMPONENTS[name])
        colour = rng.choice(list(COLOURS))
        if mat[1] in ("aluminium", "steel"):
            colour = "natural"
        lo, hi = WEIGHT_RANGE[name]
        w = round(rng.uniform(lo, hi), 1)
        keys = rng.sample(list(FEATURES), rng.randint(1, 3))
        feats = {k: rng.choice(FEATURES[k]) for k in keys}
        # in non-clean tiers some features are explicitly missing
        miss_feats = []
        if tier != "clean":
            others = [k for k in FEATURES if k not in feats]
            miss_feats = rng.sample(others, 1)
        comps.append(dict(name=name, mat=mat, colour=colour, w=w, feats=feats, miss_feats=miss_feats,
                          unit=rng.choice(opt["units"]),
                          conflict=i in conf_idx, w2=None))
        if comps[-1]["conflict"]:
            delta = rng.choice([1.5, 2.0, 2.5, 3.0])
            comps[-1]["w2"] = round(w + delta, 1)

    doc = Doc()
    truth_comps = []
    doc.text(supplier, "title")
    doc.text("Packaging Specification Sheet", "title2")
    doc.text(f"Ref {sid}-{rng.randint(1000, 9999)}   Issue {rng.randint(1, 4)}   Product code {rng.choice('ABCDEF')}{rng.randint(100, 999)}")
    doc.add(("gap",))

    def mk(cp):
        tc = dict(name=cp["name"], features={}, ram_category="missing")
        return tc

    def mat_disp(cp):
        return cp["mat"][3] if opt["abbrev"] else cp["mat"][2]

    def col_disp(cp):
        opts = COLOURS[cp["colour"]]
        return opts[-1] if opt["abbrev"] else opts[0]

    def present_str(value, quote, page, accepted=None):
        d = dict(status="present", value=value, refs=[dict(page=page, quote=quote)])
        if accepted:
            d["accepted_values"] = accepted
        return d

    def accepted_for_mat(cp):
        acc = list(cp["mat"][4])
        if opt["abbrev"] and cp["mat"][3] != cp["mat"][0]:
            acc.append(cp["mat"][3])
        return acc

    def accepted_for_col(cp):
        d = col_disp(cp)
        return [d] if d != cp["colour"] else None

    def set_fields(i, cp, tc, pages):
        """pages: dict field -> page where the primary value was rendered."""
        if (i, "material") in miss:
            tc["material"] = dict(status="missing")
            tc["ram_category"] = "missing"
        else:
            tc["material"] = present_str(cp["mat"][0], mat_disp(cp), pages["material"], accepted_for_mat(cp) or None)
            tc["ram_category"] = cp["mat"][1]
        if (i, "colour") in miss:
            tc["colour"] = dict(status="missing")
        else:
            tc["colour"] = present_str(cp["colour"], col_disp(cp), pages["colour"], accepted_for_col(cp))
        if (i, "weight_g") in miss:
            tc["weight_g"] = dict(status="missing")
        else:
            disp, grams = weight_display(cp["w"], cp["unit"])
            cp["wdisp"], cp["wgrams"] = disp, grams
            if cp["conflict"]:
                tc["weight_g"] = dict(status="conflict", conflict_values=[grams, cp["w2"]],
                                      refs=[dict(page=pages["weight_g"], quote=disp)])  # 2nd ref added with notes
            else:
                tc["weight_g"] = dict(status="present", value=grams, refs=[dict(page=pages["weight_g"], quote=disp)])
        for k in FEATURE_LABEL:
            if k in cp["feats"]:
                tc["features"][k] = None  # filled by renderer
            elif k in cp["miss_feats"]:
                tc["features"][k] = dict(status="missing")

    def cell(i, cp, field):
        if (i, field) in miss:
            return "-"
        if field == "material":
            return mat_disp(cp)
        if field == "colour":
            return col_disp(cp)
        return weight_display(cp["w"], cp["unit"])[0]

    if style == "matrix":
        widths = [110, 130, 90, 90]
        doc.text("Component summary", "h")
        doc.row(["Component", "Material", "Colour", "Weight"], widths, True)
        pgs = []
        for i, cp in enumerate(comps):
            pg = doc.row([cp["name"], cell(i, cp, "material"), cell(i, cp, "colour"), cell(i, cp, "weight_g")], widths)
            pgs.append(dict(material=pg, colour=pg, weight_g=pg))
        doc.add(("gap",))
        doc.text("Additional specification notes", "h")
        for i, cp in enumerate(comps):
            tc = mk(cp)
            set_fields(i, cp, tc, pgs[i])
            for k, v in cp["feats"].items():
                pg = doc.text(f"{cp['name']} - {FEATURE_LABEL[k].lower()}: {v}")
                tc["features"][k] = present_str(v, v, pg)
            truth_comps.append(tc)
    else:
        for i, cp in enumerate(comps):
            tc = mk(cp)
            if style == "table":
                widths = [150, 250]
                doc.text(f"Component: {cp['name']}", "h")
                doc.row(["Property", "Specification"], widths, True)
                pg = {}
                for f, lab in (("material", "Material"), ("colour", "Colour"), ("weight_g", "Weight")):
                    pg[f] = doc.row([lab, cell(i, cp, f)], widths)
                set_fields(i, cp, tc, pg)
                for k, v in cp["feats"].items():
                    p2 = doc.row([FEATURE_LABEL[k], v], widths)
                    tc["features"][k] = present_str(v, v, p2)
                doc.add(("gap",))
            else:  # prose
                doc.text(f"The {cp['name']}", "h")
                pg = {}
                m = cell(i, cp, "material")
                c = cell(i, cp, "colour")
                w = cell(i, cp, "weight_g")
                if (i, "material") in miss:
                    pg["material"] = doc.text(f"The material of the {cp['name']} is not stated on this sheet.")
                else:
                    pg["material"] = doc.text(f"The {cp['name']} is moulded or formed from {m}.")
                if (i, "colour") in miss:
                    pg["colour"] = doc.text("Colour to be confirmed by the buyer.")
                else:
                    pg["colour"] = doc.text(f"Finished colour is {c}.")
                if (i, "weight_g") in miss:
                    pg["weight_g"] = doc.text("Weights are available on request.")
                else:
                    pg["weight_g"] = doc.text(f"A typical unit weighs {w} including any tolerance.")
                set_fields(i, cp, tc, pg)
                for k, v in cp["feats"].items():
                    p2 = doc.text(f"{FEATURE_LABEL[k]} fitted to the {cp['name']}: {v}.")
                    tc["features"][k] = present_str(v, v, p2)
                doc.add(("gap",))
            truth_comps.append(tc)

    # contradictory notes on a new page
    if any(cp["conflict"] for cp in comps):
        doc.newpage()
        doc.text("Packing and handling notes", "h")
        for i, cp in enumerate(comps):
            if cp["conflict"]:
                s = f"{fmt_num(cp['w2'], 1)} g"
                pg = doc.text(f"Packing note: {cp['name']} net weight {s} per unit.")
                tc = truth_comps[i]
                tc["weight_g"]["refs"].append(dict(page=pg, quote=s))
        doc.text("Pallet pattern and carton quantities per customer order.")

    truth = dict(sheet_id=sid, tier=tier, layout=layout, source="synthetic", seed=seed, components=truth_comps)
    return doc, truth


def render_pdf(doc, scanned, rng):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    W, H = A4
    total = len(doc.pages)
    for n, items in enumerate(doc.pages, 1):
        y = H - 60
        for it in items:
            kind = it[0]
            if kind == "gap":
                y -= 10
            elif kind in ("title", "title2", "h"):
                c.setFont("Helvetica-Bold", {"title": 15, "title2": 12, "h": 11}[kind])
                c.drawString(50, y, it[1])
                y -= 20
            elif kind == "text":
                c.setFont("Helvetica", 10)
                c.drawString(50, y, it[1])
                y -= 17
            elif kind == "row":
                cells, widths, header = it[1], it[2], it[3]
                x = 50
                c.setFont("Helvetica-Bold" if header else "Helvetica", 10)
                for txt, wd in zip(cells, widths):
                    c.rect(x, y - 5, wd, 17)
                    c.drawString(x + 4, y, txt)
                    x += wd
                y -= 17
        c.setFont("Helvetica", 8)
        c.drawString(50, 30, f"Page {n} of {total}")
        c.showPage()
    c.save()
    pdf = buf.getvalue()
    return rasterise(pdf, rng) if scanned else pdf


def rasterise(pdf_bytes, rng):
    import numpy as np
    import pypdfium2 as pdfium
    from PIL import Image, ImageFilter
    pdf = pdfium.PdfDocument(pdf_bytes)
    imgs = []
    nrng = np.random.default_rng(rng.randint(0, 2**31))
    for i in range(len(pdf)):
        img = pdf[i].render(scale=1.5).to_pil().convert("L")
        angle = rng.uniform(-2.0, 2.0)
        img = img.rotate(angle, expand=False, fillcolor=255, resample=Image.BICUBIC)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        arr = np.asarray(img).astype(np.float32)
        arr += nrng.normal(0, 14, arr.shape)
        arr *= nrng.uniform(0.93, 1.0)
        imgs.append(Image.fromarray(np.clip(arr, 0, 255).astype("uint8")))
    out = io.BytesIO()
    imgs[0].save(out, format="PDF", save_all=True, append_images=imgs[1:], resolution=108)
    return out.getvalue()


def clean_truth(t):
    for c in t["components"]:
        c["features"] = {k: v for k, v in c["features"].items() if v is not None}
    return t


def generate(out, seed=SEED, tuning_seed=TUNING_SEED):
    out = Path(out)
    for d in ("sheets", "truth", "tuning", "tuning_truth"):
        (out / d).mkdir(parents=True, exist_ok=True)
    pl = plan()
    manifest = dict(seed=seed, tuning_seed=tuning_seed, test=[], tuning=[], messiest_10=[])
    jobs = [(f"S{n:03d}", seed, *pl[n], "sheets", "truth") for n in range(1, 31)]
    tun = {901: pl[2], 902: pl[8], 903: pl[12], 904: pl[15], 905: pl[22]}
    jobs += [(f"S{n:03d}", tuning_seed, *tun[n], "tuning", "tuning_truth") for n in tun]
    for sid, sd, tier, layout, style, n_comp, opt, pdir, tdir in jobs:
        doc, truth = build_sheet(sid, sd, tier, layout, style, n_comp, opt)
        truth = clean_truth(truth)
        pdf = render_pdf(doc, opt["scanned"], random.Random(f"{sd}-{sid}-scan"))
        (out / pdir / f"{sid}.pdf").write_bytes(pdf)
        (out / tdir / f"{sid}.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n")
        row = dict(sheet_id=sid, tier=tier, layout=layout, scanned=opt["scanned"], pages=len(doc.pages))
        if pdir == "sheets":
            manifest["test"].append(row)
            if tier == "messy":
                manifest["messiest_10"].append(sid)
        else:
            manifest["tuning"].append(row)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "data"))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--tuning-seed", type=int, default=TUNING_SEED)
    a = ap.parse_args()
    m = generate(a.out, a.seed, a.tuning_seed)
    print(f"generated {len(m['test'])} test and {len(m['tuning'])} tuning sheets into {a.out}")
