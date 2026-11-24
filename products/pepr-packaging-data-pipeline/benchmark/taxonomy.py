"""Single source of truth for the benchmark vocabulary, shared by generate.py and the future scorer.

- PLAUSIBLE: feature keys that make sense for each component type. Truth labels every one of
  them present or missing; only these keys are scored for that component.
- VOCAB: per feature key, canonical value -> paraphrases that appear on sheets. The extractor is
  given the canonical values and must return one of them; the quote holds the paraphrase.
- NAME_VARIANTS / norm_name: component-name normalisation for matching.
- parse_weight / weight_within: unit-parsing and tolerance used for weights and quote checks.
"""
import re

G_PER_OZ = 28.3495
WEIGHT_TOL_REL = 0.01
WEIGHT_TOL_ABS = 0.1

PLAUSIBLE = {
    "bottle": ["closure", "label", "sleeve", "ink_coating", "barrier_layer"],
    "cap": ["liner", "ink_coating"],
    "label": ["adhesive", "ink_coating"],
    "outer carton": ["ink_coating", "adhesive", "barrier_layer"],
    "sleeve": ["ink_coating", "adhesive"],
    "tray": ["barrier_layer", "ink_coating", "label"],
    "can": ["label", "ink_coating", "barrier_layer"],
    "pouch": ["barrier_layer", "ink_coating", "label"],
}

VOCAB = {
    "label": {
        "PP film label": ["BOPP wrap-around label", "polypropylene film label", "self-adhesive PP film label"],
        "paper label, wash-off": ["wash-off paper label", "paper label, caustic wash-off", "paper label (washes off)"],
        "paper label, permanent": ["permanent paper label", "paper label, non-wash", "paper label (permanent glue)"],
    },
    "closure": {
        "PP cap, no liner": ["PP screw cap without liner", "polypropylene cap, unlined", "PP cap (no liner)"],
        "HDPE cap with PE liner": ["HDPE cap, PE wad liner", "high-density PE cap + liner", "HDPE cap fitted with PE liner"],
        "aluminium cap with PE liner": ["ROPP aluminium cap, PE liner", "aluminum cap + PE liner", "alu cap with PE liner"],
    },
    "liner": {
        "PE liner": ["polyethylene liner", "LDPE wad liner", "liner: PE"],
        "foil induction seal": ["induction foil seal liner", "aluminium foil inner seal", "foil heat-seal liner"],
        "no liner": ["unlined", "without liner", "liner: none"],
    },
    "ink_coating": {
        "UV-cured ink": ["UV ink print", "ultraviolet-cured print", "print: UV-curable ink"],
        "water-based varnish": ["aqueous varnish", "water-based overprint varnish", "varnish (water-borne)"],
        "solvent-based ink": ["solvent ink print", "solvent-borne ink", "print in solvent-based inks"],
        "no ink or coating": ["undecorated, uncoated", "plain, no print or coating", "no print, no coating"],
    },
    "sleeve": {
        "PVC shrink sleeve": ["PVC heat-shrink sleeve", "shrink sleeve in PVC", "sleeve: PVC shrink film"],
        "PETG shrink sleeve": ["PETG heat-shrink sleeve", "shrink sleeve in PETG", "sleeve: PETG shrink film"],
        "no sleeve": ["no sleeve fitted", "sleeve: none", "unsleeved"],
    },
    "adhesive": {
        "hot-melt adhesive": ["hot melt glue", "hotmelt adhesive", "thermoplastic hot-melt"],
        "water-based adhesive": ["aqueous adhesive", "water-borne glue", "adhesive: water-based"],
        "pressure-sensitive adhesive": ["PSA (pressure sensitive)", "self-adhesive coating", "pressure-sensitive glue"],
    },
    "barrier_layer": {
        "EVOH barrier layer": ["EVOH oxygen barrier", "barrier: EVOH core layer", "EVOH barrier in wall"],
        "no barrier layer": ["no barrier layer present", "monolayer, no barrier", "barrier layer: none"],
        "aluminium foil barrier": ["foil barrier layer", "alu-foil barrier", "aluminium foil layer"],
    },
}
FEATURE_KEYS = sorted(VOCAB)

NAME_VARIANTS = {
    "bottle": ["bottle", "bottle body", "container"],
    "cap": ["cap", "screw cap", "closure cap"],
    "label": ["label", "front label", "wrap label"],
    "outer carton": ["outer carton", "shipper carton", "outer case"],
    "sleeve": ["sleeve", "shrink sleeve"],
    "tray": ["tray", "food tray"],
    "can": ["can", "tin can"],
    "pouch": ["pouch", "sachet"],
}
_INV = {v: k for k, vs in NAME_VARIANTS.items() for v in vs}


MATERIAL_VOCAB = {
    "PET": ["PET", "polyethylene terephthalate", "PET (virgin)", "PET-A"],
    "rPET": ["rPET", "recycled PET", "r-PET"],
    "PETG": ["PETG", "PET-G", "glycol-modified PET"],
    "HDPE": ["HDPE", "high-density polyethylene", "PE-HD"],
    "PP": ["PP", "polypropylene", "PP copolymer", "PP film", "BOPP", "polypropylene film"],
    "PS": ["PS", "polystyrene", "HIPS"],
    "PVC": ["PVC", "polyvinyl chloride", "rigid PVC film"],
    "glass": ["glass", "soda-lime glass", "flint glass"],
    "aluminium": ["aluminium", "aluminum", "Al"],
    "steel": ["steel", "tinplate steel", "tinplate"],
    "paper": ["paper", "uncoated paper", "wet-strength paper"],
    "corrugated board": ["corrugated board", "corrugated fibreboard", "corr. board"],
    "kraft paper": ["kraft paper", "kraft liner", "kraft"],
    "PE/PET laminate": ["PE/PET laminate", "PET/PE laminate", "PE/PET lam."],
}
CARBON_BLACK = "black (carbon black)"
COLOUR_VOCAB = {
    "clear": ["clear", "transparent", "clr"],
    "natural": ["natural", "nat.", "uncoloured"],
    "black": ["black", "blk", "jet black"],
    CARBON_BLACK: [CARBON_BLACK, "carbon black pigmented", "black, carbon black", "CB black", "carbon black"],
    "white": ["white", "wht", "bright white"],
    "amber": ["amber", "amber tint", "amb"],
    "green": ["green", "grn", "flint green"],
    "brown": ["brown", "kraft brown", "brn"],
    "blue": ["blue", "blu", "royal blue"],
}


def key_vocab(key):
    """canonical value -> every accepted wording (canonical included) for a material, colour or feature key."""
    if key == "material":
        return MATERIAL_VOCAB
    if key == "colour":
        return COLOUR_VOCAB
    return {c: [c] + [p for p in ps if p != c] for c, ps in VOCAB[key].items()}


def norm_text(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def norm_name(s):
    n = norm_text(s)
    return _INV.get(n, n)


# Amendment 3 (2026-11-24, before any model run): real sheets write grams as "gm", "gms" or "grams" (benchmark/REALISM.md).
_W = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|mg|grams|gram|gms|gm|g|oz)\b", re.I)
_FACTOR = {"g": 1.0, "gm": 1.0, "gms": 1.0, "gram": 1.0, "grams": 1.0, "kg": 1000.0, "mg": 0.001, "oz": G_PER_OZ}


def parse_weight(text):
    """First number+unit in text, converted to grams, or None."""
    m = _W.search(text)
    if not m:
        return None
    return float(m.group(1)) * _FACTOR[m.group(2).lower()]


def weight_within(a, b):
    return abs(a - b) <= max(WEIGHT_TOL_ABS, WEIGHT_TOL_REL * abs(b))


def scored_slots(truth):
    """Yield (component index, slot, status) for every scored slot of one truth file."""
    for i, c in enumerate(truth["components"]):
        for f in ("material", "colour", "weight_g"):
            yield i, f, c[f]["status"]
        if c["material"]["status"] != "missing":  # ram_category is derived from material: scored only when present
            yield i, "ram_category", "present"
        for k in PLAUSIBLE[c["name"]]:
            yield i, f"features.{k}", c["features"][k]["status"]


def norm_quote(s):
    """Normalisation for quote and page text: case, whitespace, and the ' | ' cell separator as whitespace."""
    return norm_text(str(s).replace("|", " "))


def canonical(key, s):
    """Map an extracted string to its canonical value by exact normalised match on value or listed variant.
    No containment matching. Returns None if it is not a listed wording."""
    n = norm_text(s)
    for canon, words in key_vocab(key).items():
        if n in [norm_text(w) for w in words]:
            return canon
    return None


def _hits(key, text):
    """(start, end, canonical) for every listed wording in text; the longest overlapping match wins (PET inside PETG does not count)."""
    hits = []
    for canon, words in key_vocab(key).items():
        for w in words:
            for m in re.finditer(r"(?<![a-z0-9])" + re.escape(norm_text(w)) + r"(?![a-z0-9])", text):
                hits.append((m.start(), m.end(), canon))
    return [h for h in hits if not any(o is not h and o[0] <= h[0] and h[1] <= o[1] and (o[1] - o[0]) > (h[1] - h[0])
                                      for o in hits)]


def _terms_in(key, text):
    """Canonical values whose wording occurs in text."""
    return {h[2] for h in _hits(key, text)}


# Amendment 4, D1 (2026-11-24, before any model run): a material cell may name a blend with shares.
_PCT_AFTER = re.compile(r"^\s*[(:=-]?\s*(\d+(?:\.\d+)?)\s*%")
_PCT_BEFORE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s+)?$")


def blend_winner(text):
    """Amendment 4 D1 (as tightened after review). Canonical material with the largest stated share in a PET/rPET blend
    quote (already norm_quote'd), tie -> "PET". None unless the quote names exactly PET and rPET, each with a share, all
    shares read in ONE direction (share before every name, or after every name), and the shares sum to 100 +-1."""
    hits = sorted(_hits("material", text))
    if len(hits) != 2 or {h[2] for h in hits} != {"PET", "rPET"}:
        return None
    before = bool(_PCT_BEFORE.search(text[:hits[0][0]]))  # share-before-name if the first name follows a share
    shares = {}
    for s, e, canon in hits:
        m = _PCT_BEFORE.search(text[:s]) if before else _PCT_AFTER.match(text[e:])
        if not m:
            return None
        shares[canon] = float(m.group(1))
    if abs(sum(shares.values()) - 100) > 1:
        return None
    if shares["PET"] == shares["rPET"]:
        return "PET"
    return max(shares, key=shares.get)


# Amendment 4, D2: the weight unit may sit only in the row label, "Weight (g) | 25.5".
_NUM = r"\d+(?:\.\d+)?"
_LABEL_UNIT = re.compile(r"(?=[a-z .]*(?:weight|wt|mass))[a-z .]*\((g|gm|gms|grams|kg|oz)\)\s*(" + _NUM + r")"
                         r"(?:\s*(?:\u00b1|\+/-)\s*" + _NUM + r"(?:\s*(?:g|gm|gms|grams|kg|oz))?)?")


def label_unit_weight(text):
    """Grams from a label unit in parentheses followed by a bare number, or None."""
    m = _LABEL_UNIT.fullmatch(text.strip())
    return float(m.group(2)) * _FACTOR[m.group(1)] if m else None


def quote_ok(key, value, quote, page_text=None, extra_words=()):
    """True if the quote supports the value. Rule: after norm_quote, the quote appears in the page text (when
    given) AND names exactly the value (canonical or one of its listed wordings, longest match, no other
    canonical value of the same key; a blend quote with a share for every material names its largest, tie PET, Amendment 4 D1).
    Weights: the quote holds a number+unit that parses to grams within
    tolerance of the value."""
    q = norm_quote(quote)
    if not q:
        return False
    if page_text is not None and q not in norm_quote(page_text):
        return False
    if key == "weight_g":
        g = label_unit_weight(q)  # strict full match, so it goes first ("Weight (g) 25.5 +/- 0.5 g" is 25.5, not 0.5)
        if g is None:
            g = parse_weight(q)
        return g is not None and weight_within(g, value)
    terms = _terms_in(key, q)
    for w in extra_words:  # truth-file accepted_values that are not vocabulary wordings (Amendment 4, S805 "WhiteSolid")
        if re.search(r"(?<![a-z0-9])" + re.escape(norm_text(w)) + r"(?![a-z0-9])", q):
            terms.add(value)
    if key == "material" and len(terms) > 1:
        return blend_winner(q) == value
    return terms == {value}
