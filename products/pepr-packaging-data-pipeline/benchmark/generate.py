#!/usr/bin/env python3
"""Deterministic generator of synthetic supplier packaging spec sheets (T-56).

Usage: python3 generate.py [--out data] [--seed 20261124] [--tuning-seed 20261125]

The truth JSON is written from the same data model that renders the PDF, so it is exact.
Every present value carries the page and a quote that appears on that page. Scanned sheets
are rendered as text PDFs, then rasterised, rotated and noised; the text that was drawn is
recorded in manifest.json (page_text) so traceability can be checked without OCR.

Outputs under --out:
  sheets/S001.pdf..S030.pdf, truth/S001.json..   the 30 test sheets
  tuning/S901.pdf..S905.pdf, tuning_truth/...    5 held-out tuning sheets (other seed)
  manifest.json                                  tiers, layouts, templates, messiest 10, stats,
                                                 recorded page text of image-only sheets
Output is byte-for-byte reproducible (PDF dates are fixed).
"""
import argparse
import io
import json
import random
import re
import textwrap
from pathlib import Path

import taxonomy as tx
from taxonomy import PLAUSIBLE, VOCAB, NAME_VARIANTS, G_PER_OZ

HERE = Path(__file__).resolve().parent
SEED = 20261124
TUNING_SEED = 20261125
CORE = ("material", "colour", "weight_g")

# name -> list of (value, ram, displays)
COMPONENTS = {
    "bottle": [("PET", "plastic", ["PET", "polyethylene terephthalate", "PET (virgin)", "PET-A"]),
               ("HDPE", "plastic", ["HDPE", "high-density polyethylene", "PE-HD"]),
               ("glass", "glass", ["glass", "soda-lime glass", "flint glass"])],
    "cap": [("PP", "plastic", ["PP", "polypropylene", "PP copolymer"]),
            ("HDPE", "plastic", ["HDPE", "high-density polyethylene", "PE-HD"]),
            ("aluminium", "aluminium", ["aluminium", "aluminum", "Al"])],
    "label": [("paper", "paper_board", ["paper", "uncoated paper", "wet-strength paper"]),
              ("PP", "plastic", ["PP film", "BOPP", "polypropylene film"])],
    "outer carton": [("corrugated board", "paper_board", ["corrugated board", "corrugated fibreboard", "corr. board"]),
                     ("kraft paper", "paper_board", ["kraft paper", "kraft liner", "kraft"])],
    "sleeve": [("PETG", "plastic", ["PETG", "PET-G", "glycol-modified PET"]),
               ("PVC", "plastic", ["PVC", "polyvinyl chloride", "rigid PVC film"])],
    "tray": [("rPET", "plastic", ["rPET", "recycled PET", "r-PET"]),
             ("PS", "plastic", ["PS", "polystyrene", "HIPS"])],
    "can": [("aluminium", "aluminium", ["aluminium", "aluminum", "Al"]),
            ("steel", "steel", ["tinplate steel", "tinplate", "steel"])],
    "pouch": [("PE/PET laminate", "plastic", ["PE/PET laminate", "PET/PE laminate", "PE/PET lam."])],
}
WEIGHT_RANGE = {"bottle": (18, 60), "cap": (2, 9), "label": (0.5, 3), "outer carton": (60, 180),
                "sleeve": (1, 4), "tray": (8, 30), "can": (12, 35), "pouch": (4, 12)}
CARBON = tx.CARBON_BLACK
COLOURS = {"clear": ["clear", "transparent", "clr"], "natural": ["natural", "nat.", "uncoloured"],
           "black": ["black", "blk", "jet black"],
           CARBON: [CARBON, "carbon black pigmented", "black, carbon black", "CB black"],
           "white": ["white", "wht", "bright white"], "amber": ["amber", "amber tint", "amb"],
           "green": ["green", "grn", "flint green"], "brown": ["brown", "kraft brown", "brn"],
           "blue": ["blue", "blu", "royal blue"]}
FIELD_LABELS = {"material": ["Material", "Resin", "Substrate", "Polymer", "Construction"],
                "colour": ["Colour", "Shade", "Tint", "Finish colour"],
                "weight_g": ["Weight", "Nett wt", "Mass", "Unit weight", "Net mass"]}
ALL_CORE_LABELS = sum(FIELD_LABELS.values(), [])
FEATURE_LABELS = {"label": ["Label", "Decoration label", "Labelling"],
                  "closure": ["Closure", "Cap fitted", "Lid type"],
                  "liner": ["Liner", "Seal liner", "Wad"],
                  "ink_coating": ["Ink / coating", "Print", "Decoration", "Surface finish"],
                  "sleeve": ["Sleeve", "Shrink sleeve", "Sleeving"],
                  "adhesive": ["Adhesive", "Glue", "Bonding"],
                  "barrier_layer": ["Barrier layer", "Barrier", "Oxygen barrier"]}
MISS_MARKERS = ["absent", "n/a", "TBC", "to be confirmed", "blank"]
SUPPLIERS = ["Northfield Packaging Ltd", "Calder Plastics", "Brightwell Containers", "Hartley Print and Pack",
             "Mersey Glassworks", "Oakridge Converters", "Tamar Closures", "Bexley Board Co"]
FILLER = ["Following the March trial run this item was approved by the customer.",
          "Production is on line 3 at the Telford plant, two shifts.",
          "Batch records are held for seven years and available on request.",
          "Lead time is quoted at five weeks from order confirmation.",
          "Minimum order quantity applies; see the price list for break points.",
          "Artwork proofs must be signed off before tooling is released.",
          "Samples were dispatched to the customer laboratory in week 41."]


def _o(units, missing=0, conflict=0, scanned=False):
    return dict(units=units, missing=missing, conflict=conflict, scanned=scanned)


def plan():
    """sheet number -> (tier, layout, template, n_components, options)"""
    p = {}
    for n, t in zip(range(1, 11), ["table", "table", "table", "matrix", "bom", "bom", "prose", "prose", "prose", "table"]):
        p[n] = ("clean", "prose" if t == "prose" else "table", t, 1, _o(["g"]))
    p[11] = ("moderate", "prose", "prose", 2, _o(["g", "kg"], 1))
    p[12] = ("moderate", "prose", "prose", 2, _o(["g", "kg"], 1, 1))
    p[13] = ("moderate", "prose", "prose", 2, _o(["g", "kg"], 1))
    p[14] = ("moderate", "mixed_units", "matrix", 3, _o(["g", "kg", "oz", "mg"]))
    p[15] = ("moderate", "mixed_units", "bom", 3, _o(["g", "kg", "oz", "mg"], 0, 1))
    p[16] = ("moderate", "mixed_units", "two_column", 3, _o(["g", "kg", "oz", "mg"], 0, 1))
    p[17] = ("moderate", "multi_component", "matrix", 4, _o(["g", "kg"], 1, 1))
    p[18] = ("moderate", "multi_component", "two_column", 4, _o(["g", "kg"], 1, 1))
    p[19] = ("moderate", "missing_fields", "table", 2, _o(["g", "oz"], 3, 1))
    p[20] = ("moderate", "missing_fields", "bom", 3, _o(["g", "oz"], 3, 1))
    for n, t in zip(range(21, 26), ["prose_buried", "matrix", "table", "bom", "two_column"]):
        p[n] = ("messy", "scanned", t, 3, _o(["g", "kg", "oz", "mg"], 2, 1, True))
    for n, t in zip(range(26, 31), ["table", "prose_buried", "two_column", "bom", "matrix"]):
        p[n] = ("messy", "contradictory", t, 3, _o(["g", "kg", "oz", "mg"], 2, 2))
    return p


def tuning_plan():
    """Held-out tuning sheets, different seed: clean, multi-component with missing, mixed units,
    scanned with conflict, contradictory."""
    return {
        901: ("clean", "table", "table", 1, _o(["g"])),
        902: ("moderate", "multi_component", "matrix", 4, _o(["g", "kg"], 2)),
        903: ("moderate", "mixed_units", "two_column", 3, _o(["g", "kg", "oz", "mg"], 1)),
        904: ("messy", "scanned", "bom", 3, _o(["g", "kg", "oz", "mg"], 1, 1, True)),
        905: ("messy", "contradictory", "table", 3, _o(["g", "kg", "oz"], 2, 2)),
    }


def fmt_num(x, nd=3):
    s = f"{x:.{nd}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


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
    PER_PAGE = 34

    def __init__(self):
        self.pages = [[]]
        self.count = 0
        self.foots = {}

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
        assert all(len(c) <= 40 or w > 250 for c, w in zip(cells, widths)), cells
        return self.add(("row", cells, widths, header))

    def cols(self, left, right, bold=False):
        assert len(left or "") <= 48 and len(right or "") <= 48, (left, right)
        return self.add(("cols", left, right, bold))

    def block(self, lines):
        if self.count + len(lines) > self.PER_PAGE:
            self.newpage()
        for ln in lines:
            assert len(ln) <= 95
            self.add(("text", ln))
        return self.page

    def foot(self, page, s):
        self.foots.setdefault(page, []).append(s)


# ---------------------------------------------------------------- data model

def pick_colour(rng, mat):
    ram = mat[1]
    if ram in ("aluminium", "steel"):
        return "natural"
    if ram == "glass":
        return rng.choice(["clear", "amber", "green", "brown"])
    if ram == "paper_board":
        return rng.choice(["natural", "white", "brown"])
    if rng.random() < 0.22:
        return CARBON
    return rng.choice(["clear", "natural", "black", "white", "blue", "green", "amber"])


def accepted_for(key, value):
    """Every listed wording of the value except the canonical one (taxonomy vocab, not just those used here)."""
    return [w for w in tx.key_vocab(key)[value] if w != value]


def make_distractors(rng, tier, name, w):
    pool = [("Gross weight (filled)", f"{int(w * rng.uniform(8, 14)) + 40} g"),
            ("Pallet weight", f"{rng.randint(380, 620)} kg"),
            ("Wall thickness", f"{rng.uniform(0.3, 0.9):.2f} mm"),
            ("Case count", f"{rng.choice([12, 24, 48, 96])} per case"),
            ("Tolerance", f"+/- {rng.choice([0.2, 0.3, 0.5])} g"),
            ("Gross wt per case", f"{rng.uniform(4, 12):.1f} kg")]
    if name in ("bottle", "cap"):
        pool.append(("Cap torque", f"{rng.uniform(1.2, 2.8):.1f} Nm"))
    if tier == "clean":
        return [("Case count", f"{rng.choice([12, 24, 48, 96])} per case")]
    return rng.sample(pool, rng.choice([1, 2]) if tier == "moderate" else rng.choice([2, 3]))


def build_components(rng, tier, names, opt):
    n_comp = len(names)
    conf_idx = set(rng.sample(range(n_comp), opt["conflict"])) if opt["conflict"] else set()
    slots = [(i, f) for i in range(n_comp) for f in CORE if not (i in conf_idx and f == "weight_g")]
    miss = {}
    for s in (rng.sample(slots, opt["missing"]) if opt["missing"] else []):
        miss[s] = rng.choice(MISS_MARKERS)
    units = list(opt["units"])
    rng.shuffle(units)
    p_feat = {"clean": 0.6, "moderate": 0.5, "messy": 0.45}[tier]
    comps = []
    for i, name in enumerate(names):
        mat = rng.choice(COMPONENTS[name])
        mat_d = mat[2][0] if tier == "clean" else rng.choice(mat[2][:3] if tier == "moderate" else mat[2])
        col = pick_colour(rng, mat)
        cdisp = COLOURS[col]
        col_d = cdisp[0] if tier == "clean" else rng.choice(cdisp[:3] if tier == "moderate" else cdisp)
        lo, hi = WEIGHT_RANGE[name]
        w = round(rng.uniform(lo, hi), 1)
        unit = units[i % len(units)]
        wdisp, wgrams = weight_display(w, unit)
        keys = list(PLAUSIBLE[name])
        if tier == "clean":
            present = set(rng.sample(keys, max(1, round(len(keys) * p_feat))))
        else:
            present = {k for k in keys if rng.random() < p_feat}
        feats, fmark = {}, {}
        for k in keys:
            if k in present:
                canon = rng.choice(sorted(VOCAB[k]))
                shown = canon if tier == "clean" else rng.choice(VOCAB[k][canon])
                feats[k] = (canon, shown)
            elif tier != "clean" and rng.random() < 0.35:
                fmark[k] = rng.choice(["n/a", "TBC", "to be confirmed", "none stated"])
        pickl = (lambda L: rng.choice(L[:3])) if tier == "clean" else (lambda L: rng.choice(L))
        labels = {f: pickl(FIELD_LABELS[f]) for f in CORE}
        labels.update({k: pickl(FEATURE_LABELS[k]) for k in keys})
        nd = name if tier == "clean" else rng.choice(NAME_VARIANTS[name])
        conflict = None
        if i in conf_idx:
            delta = rng.choice([1.5, 2.0, 2.5, 3.0]) + 0.03 * w
            u2 = rng.choice(opt["units"])
            d2, g2 = weight_display(round(w + delta, 1), u2)
            tol = max(tx.WEIGHT_TOL_ABS, tx.WEIGHT_TOL_REL * max(wgrams, g2))
            assert abs(g2 - wgrams) > 2 * tol
            conflict = dict(disp2=d2, grams2=g2)
        comps.append(dict(
            name=name, nd=nd, mat=mat, mat_d=mat_d, col=col, col_d=col_d, w=w, wdisp=wdisp, wgrams=wgrams,
            wtext=wdisp, feats=feats, fmark=fmark, feat_order=keys[:], labels=labels,
            miss={f: miss[(i, f)] for f in CORE if (i, f) in miss}, conflict=conflict,
            distract=make_distractors(rng, tier, name, w)))
    return comps


def core_text(c, f):
    """Text shown for a core field: str, '' for blank, None for absent."""
    mode = c["miss"].get(f)
    if mode is None:
        return {"material": c["mat_d"], "colour": c["col_d"], "weight_g": c["wtext"]}[f]
    if mode == "absent":
        return None
    return "" if mode == "blank" else mode


def core_quote(c, f):
    return {"material": c["mat_d"], "colour": c["col_d"], "weight_g": c["wdisp"]}[f]


def comp_rows(c, rng, tier):
    """(key|None, label, text, quote|None) for every property a component shows."""
    rows = []
    for f in CORE:
        t = core_text(c, f)
        if t is not None:
            ok = f not in c["miss"]
            rows.append((f if ok else None, c["labels"][f], t, core_quote(c, f) if ok else None))
    for k in c["feat_order"]:
        if k in c["feats"]:
            rows.append((k, c["labels"][k], c["feats"][k][1], c["feats"][k][1]))
        elif k in c["fmark"]:
            rows.append((None, c["labels"][k], c["fmark"][k], None))
    for lab, txt in c["distract"]:
        rows.append((None, lab, txt, None))
    if tier != "clean":
        rng.shuffle(rows)
    return rows


def non_core_rows(c, rng, tier):
    out = []
    for key, lab, txt, q in comp_rows(c, rng, tier):
        if key in CORE or (key is None and lab in ALL_CORE_LABELS):
            continue
        out.append((key, lab, txt, q))
    return out


# ---------------------------------------------------------------- templates

def t_table(doc, comps, refs, rng, tier):
    widths = [150, 250]
    for i, c in enumerate(comps):
        doc.text(f"Component: {c['nd']}", "h")
        doc.row(["Property", "Specification"], widths, True)
        for key, lab, txt, q in comp_rows(c, rng, tier):
            pg = doc.row([lab, txt], widths)
            if key:
                refs[(i, key)] = (pg, q)
        doc.add(("gap",))


def t_matrix(doc, comps, refs, rng, tier):
    widths = [100, 140, 130, 100]
    L = comps[0]["labels"]
    doc.text("Component summary", "h")
    doc.row(["Component", L["material"], L["colour"], L["weight_g"]], widths, True)
    for i, c in enumerate(comps):
        pg = doc.row([c["nd"]] + [core_text(c, f) or "" for f in CORE], widths)
        for f in CORE:
            if f not in c["miss"]:
                refs[(i, f)] = (pg, core_quote(c, f))
    doc.add(("gap",))
    doc.text("Additional specification notes", "h")
    for i, c in enumerate(comps):
        for key, lab, txt, q in non_core_rows(c, rng, tier):
            pg = doc.text(f"{c['nd']} - {lab.lower()}: {txt}")
            if key:
                refs[(i, key)] = (pg, q)


def t_bom(doc, comps, refs, rng, tier):
    widths = [30, 100, 260, 90]
    L = comps[0]["labels"]
    doc.text("Bill of materials", "h")
    doc.row(["No.", "Item", f"{L['material']} / {L['colour']}", L["weight_g"]], widths, True)
    for i, c in enumerate(comps):
        parts = [t for t in (core_text(c, "material"), core_text(c, "colour")) if t]
        pg = doc.row([str(i + 1), c["nd"], ", ".join(parts), core_text(c, "weight_g") or ""], widths)
        for f in CORE:
            if f not in c["miss"]:
                refs[(i, f)] = (pg, core_quote(c, f))
    doc.add(("gap",))
    doc.text("Decoration, fittings and logistics", "h")
    for i, c in enumerate(comps):
        for key, lab, txt, q in non_core_rows(c, rng, tier):
            pg = doc.text(f"Item {i + 1} ({c['nd']}) - {lab}: {txt}")
            if key:
                refs[(i, key)] = (pg, q)


def t_prose(doc, comps, refs, rng, tier):
    fr = {"material": ["The {nd} is moulded or formed from {x}.", "Material of construction: {x}.", "Made from {x} throughout."],
          "colour": ["Finished colour is {x}.", "Supplied in {x}.", "Shade supplied: {x}."],
          "weight_g": ["A typical unit weighs {x} including any tolerance.", "Nominal mass per piece: {x}.", "Each unit is {x} nett."]}
    ff = ["{lab} fitted to the {nd}: {x}.", "Note that we use {x} on this item.", "{lab} - {x}."]
    for i, c in enumerate(comps):
        doc.text(f"The {c['nd']}", "h")
        for f in CORE:
            t = core_text(c, f)
            if t is None or (t == "" and f in c["miss"]):
                continue
            if f in c["miss"]:
                doc.text(f"{c['labels'][f]} for the {c['nd']}: {t}.")
                continue
            frame = rng.choice(fr[f]) if tier != "clean" else fr[f][0]
            pg = doc.text(frame.format(nd=c["nd"], x=t))
            refs[(i, f)] = (pg, core_quote(c, f))
        for k in c["feat_order"]:
            if k in c["feats"]:
                shown = c["feats"][k][1]
                frame = rng.choice(ff) if tier != "clean" else ff[0]
                pg = doc.text(frame.format(lab=c["labels"][k], nd=c["nd"], x=shown))
                refs[(i, k)] = (pg, shown)
            elif k in c["fmark"]:
                doc.text(f"{c['labels'][k]}: {c['fmark'][k]}.")
        for lab, txt in c["distract"]:
            doc.text(f"{lab} is {txt}.")
        doc.add(("gap",))


def t_buried(doc, comps, refs, rng, tier):
    fr = {"material": ["For the {nd} we have standardised on {x}.", "Material: the {nd} is produced in {x}, as approved at the March review.",
                       "Supply for this item is {x} from the Telford plant."],
          "colour": ["It is finished in {x}.", "The customer specified {x}.", "Colour was matched to the approved sample: {x}."],
          "weight_g": ["Unit mass is {x} (see also pallet data).", "Weighed samples averaged {x}.", "Nominal nett mass {x}."]}
    ff = ["Customer sign-off covered the following: {x}.", "As per trial, {x} is used.", "Please note {x} on this item.",
          "The converter confirmed {x}."]
    for i, c in enumerate(comps):
        doc.text(f"{c['nd']} (technical remarks)", "h")
        sents = []  # (key, text, quote)
        for f in CORE:
            t = core_text(c, f)
            if t is None or (t == "" and f in c["miss"]):
                continue
            if f in c["miss"]:
                sents.append((None, f"{c['labels'][f]}: {t}.", None))
            else:
                sents.append((f, rng.choice(fr[f]).format(nd=c["nd"], x=t), core_quote(c, f)))
        for k in c["feat_order"]:
            if k in c["feats"]:
                sents.append((k, rng.choice(ff).format(x=c["feats"][k][1]), c["feats"][k][1]))
        for lab, txt in c["distract"]:
            sents.append((None, f"{lab} is {txt}.", None))
        for fl in rng.sample(FILLER, 3):
            sents.append((None, fl, None))
        rng.shuffle(sents)
        para = " ".join(s[1] for s in sents)
        lines = textwrap.wrap(para, 86, break_long_words=False, break_on_hyphens=False)
        pg = doc.block(lines)
        for key, _, q in sents:
            if key:
                refs[(i, key)] = (pg, q)
        doc.add(("gap",))


def t_two_column(doc, comps, refs, rng, tier):
    for a in range(0, len(comps), 2):
        group = list(range(a, min(a + 2, len(comps))))
        cols = []
        for i in group:
            c = comps[i]
            lines = [(None, f"{c['nd']}", None)]
            for key, lab, txt, q in comp_rows(c, rng, tier):
                lines.append((key, f"{lab}: {txt}", q))
            cols.append(lines)
        n = max(len(x) for x in cols)
        for r in range(n):
            cell = [x[r] if r < len(x) else (None, None, None) for x in cols]
            while len(cell) < 2:
                cell.append((None, None, None))
            pg = doc.cols(cell[0][1], cell[1][1], bold=(r == 0))
            for ci, (key, _, q) in zip(group, cell):
                if key:
                    refs[(ci, key)] = (pg, q)
        doc.add(("gap",))


TEMPLATES = {"table": t_table, "matrix": t_matrix, "bom": t_bom, "prose": t_prose,
             "prose_buried": t_buried, "two_column": t_two_column}


# ---------------------------------------------------------------- sheet assembly

def present_str(value, quote, page, accepted=None):
    d = dict(status="present", value=value, refs=[dict(page=page, quote=quote)])
    if accepted:
        d["accepted_values"] = accepted
    return d


def build_sheet(sid, seed, tier, layout, template, n_comp, opt):
    rng = random.Random(f"{seed}-{sid}")
    names = rng.sample(sorted(COMPONENTS), n_comp)
    supplier = rng.choice(SUPPLIERS)
    comps = build_components(rng, tier, names, opt)

    # conflict display mode: footnote on the same page, or a separate notes page
    modes = []
    fnum = 0
    for c in comps:
        if c["conflict"]:
            mode = "notes" if template == "prose_buried" else rng.choice(["notes", "footnote"])
            c["conflict"]["mode"] = mode
            modes.append(mode)
            if mode == "footnote":
                fnum += 1
                c["conflict"]["fn"] = fnum
                c["wtext"] = f"{c['wdisp']} ({fnum})"

    doc = Doc()
    header = f"{supplier} | Packaging Specification | CONFIDENTIAL"
    form = f"Form PS-{rng.randint(100, 999)} rev {rng.choice('ABCD')}"
    doc.text(supplier, "title")
    doc.text("Packaging Specification Sheet", "title2")
    doc.text(f"Ref {sid}-{rng.randint(1000, 9999)}   Issue {rng.randint(1, 4)}   Product code {rng.choice('ABCDEF')}{rng.randint(100, 999)}")
    doc.add(("gap",))
    refs = {}
    TEMPLATES[template](doc, comps, refs, rng, tier)

    conf_refs = {}
    notes = [(i, c) for i, c in enumerate(comps) if c["conflict"] and c["conflict"]["mode"] == "notes"]
    for i, c in enumerate(comps):
        cf = c["conflict"]
        if cf and cf["mode"] == "footnote":
            pg = refs[(i, "weight_g")][0]
            doc.foot(pg, f"({cf['fn']}) {c['nd']}: unit weight on retest {cf['disp2']}.")
            conf_refs[i] = (pg, cf["disp2"])
    if notes:
        doc.newpage()
        doc.text("Packing and handling notes", "h")
        for i, c in notes:
            pg = doc.text(f"Packing note: {c['nd']} net weight {c['conflict']['disp2']} per unit.")
            conf_refs[i] = (pg, c["conflict"]["disp2"])
        doc.text("Pallet pattern and carton quantities per customer order.")

    tcs = []
    for i, c in enumerate(comps):
        tc = dict(name=c["name"], features={})
        if "material" in c["miss"]:
            tc["material"] = dict(status="missing")
            tc["ram_category"] = "missing"
        else:
            pg, q = refs[(i, "material")]
            tc["material"] = present_str(c["mat"][0], q, pg, accepted_for("material", c["mat"][0]) or None)
            tc["ram_category"] = c["mat"][1]
        if "colour" in c["miss"]:
            tc["colour"] = dict(status="missing")
        else:
            pg, q = refs[(i, "colour")]
            tc["colour"] = present_str(c["col"], q, pg, accepted_for("colour", c["col"]) or None)
        if "weight_g" in c["miss"]:
            tc["weight_g"] = dict(status="missing")
        else:
            pg, q = refs[(i, "weight_g")]
            if c["conflict"]:
                pg2, q2 = conf_refs[i]
                tc["weight_g"] = dict(status="conflict", conflict_values=[c["wgrams"], c["conflict"]["grams2"]],
                                      refs=[dict(page=pg, quote=q), dict(page=pg2, quote=q2)])
            else:
                tc["weight_g"] = dict(status="present", value=c["wgrams"], refs=[dict(page=pg, quote=q)])
        for k in PLAUSIBLE[c["name"]]:
            if k in c["feats"]:
                pg, q = refs[(i, k)]
                tc["features"][k] = present_str(c["feats"][k][0], q, pg)
            else:
                tc["features"][k] = dict(status="missing")
        tcs.append(tc)
    truth = dict(sheet_id=sid, tier=tier, layout=layout, template=template, source="synthetic", seed=seed,
                 components=tcs)
    return doc, header, form, truth, modes


# ---------------------------------------------------------------- rendering

def render_pdf(doc, header, form, scanned, rng):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    W, H = A4
    total = len(doc.pages)
    texts = []
    for n, items in enumerate(doc.pages, 1):
        lines = [header]
        c.setFont("Helvetica", 8)
        c.drawString(50, H - 35, header)
        y = H - 65
        for it in items:
            kind = it[0]
            if kind == "gap":
                y -= 10
            elif kind in ("title", "title2", "h"):
                c.setFont("Helvetica-Bold", {"title": 15, "title2": 12, "h": 11}[kind])
                c.drawString(50, y, it[1])
                lines.append(it[1])
                y -= 20
            elif kind == "text":
                c.setFont("Helvetica", 10)
                c.drawString(50, y, it[1])
                lines.append(it[1])
                y -= 17
            elif kind == "cols":
                c.setFont("Helvetica-Bold" if it[3] else "Helvetica", 10)
                if it[1]:
                    c.drawString(50, y, it[1])
                if it[2]:
                    c.drawString(310, y, it[2])
                lines.append("   ".join(s for s in (it[1], it[2]) if s))
                y -= 17
            elif kind == "row":
                cells, widths, hd = it[1], it[2], it[3]
                x = 50
                c.setFont("Helvetica-Bold" if hd else "Helvetica", 10)
                for txt, wd in zip(cells, widths):
                    c.rect(x, y - 5, wd, 17)
                    c.drawString(x + 4, y, txt)
                    x += wd
                lines.append(" | ".join(cells))
                y -= 17
        c.setFont("Helvetica", 8)
        fy = 100
        for s in doc.foots.get(n, []):
            c.drawString(50, fy, s)
            lines.append(s)
            fy -= 10
        foot = f"Page {n} of {total}"
        c.drawString(50, 30, foot)
        c.drawString(400, 30, form)
        lines.append(f"{foot}   {form}")
        texts.append("\n".join(lines))
        c.showPage()
    c.save()
    pdf = buf.getvalue()
    return (rasterise(pdf, rng) if scanned else pdf), texts


_DATE = re.compile(rb"(/(?:CreationDate|ModDate) \()D:\d{14}([^)]*\))")


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
    # Pillow stamps the current time; replace with a fixed date of the same length
    return _DATE.sub(rb"\1D:20261124000000\2", out.getvalue())


def stats(truths):
    st = dict(sheets=len(truths), components=0, scored_slots=0, present_slots=0, missing_slots=0,
              conflict_slots=0, carbon_black_components=0)
    for t in truths:
        st["components"] += len(t["components"])
        for c in t["components"]:
            if c["colour"].get("value") == CARBON:
                st["carbon_black_components"] += 1
        for _, _, status in tx.scored_slots(t):
            st["scored_slots"] += 1
            st[f"{status}_slots"] += 1
    return st


def generate(out, seed=SEED, tuning_seed=TUNING_SEED):
    out = Path(out)
    for d in ("sheets", "truth", "tuning", "tuning_truth"):
        (out / d).mkdir(parents=True, exist_ok=True)
    pl = plan()
    manifest = dict(seed=seed, tuning_seed=tuning_seed, test=[], tuning=[], messiest_10=[])
    jobs = [(f"S{n:03d}", seed, *pl[n], "sheets", "truth") for n in range(1, 31)]
    tp = tuning_plan()
    jobs += [(f"S{n:03d}", tuning_seed, *tp[n], "tuning", "tuning_truth") for n in sorted(tp)]
    test_truths, tuning_truths = [], []
    for sid, sd, tier, layout, template, n_comp, opt, pdir, tdir in jobs:
        doc, header, form, truth, modes = build_sheet(sid, sd, tier, layout, template, n_comp, opt)
        pdf, texts = render_pdf(doc, header, form, opt["scanned"], random.Random(f"{sd}-{sid}-scan"))
        (out / pdir / f"{sid}.pdf").write_bytes(pdf)
        (out / tdir / f"{sid}.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n")
        row = dict(sheet_id=sid, tier=tier, layout=layout, template=template, scanned=opt["scanned"],
                   pages=len(doc.pages), conflict_modes=modes)
        if opt["scanned"]:
            row["page_text"] = texts  # text rendered onto the raster; scorer-side only
        if pdir == "sheets":
            manifest["test"].append(row)
            test_truths.append(truth)
            if tier == "messy":
                manifest["messiest_10"].append(sid)
        else:
            manifest["tuning"].append(row)
            tuning_truths.append(truth)
    manifest["stats"] = dict(test=stats(test_truths), tuning=stats(tuning_truths))
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
    print(json.dumps(m["stats"], indent=2))
