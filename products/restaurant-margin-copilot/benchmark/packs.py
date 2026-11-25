"""Pack-size normalisation: turn (pack text, unit) into a cost per gram, millilitre or each.

Examples: "12x1L" -> 12000 ml; "6x400g" -> 2400 g; "5kg" -> 5000 g; unit "kg" with no pack -> 1000 g.
When the unit itself is a measure (kg, g, l, ml) the price is per that measure and the pack text is ignored.
"""
from __future__ import annotations

import re

MEASURES = {"kg": ("g", 1000.0), "g": ("g", 1.0), "l": ("ml", 1000.0), "ltr": ("ml", 1000.0),
            "litre": ("ml", 1000.0), "cl": ("ml", 10.0), "ml": ("ml", 1.0)}
_NUM = r"(\d+(?:\.\d+)?)"
_MEAS = "|".join(sorted(MEASURES, key=len, reverse=True))
_MULTI = re.compile(rf"^{_NUM}\s*x\s*{_NUM}\s*({_MEAS})$")
_SINGLE = re.compile(rf"^{_NUM}\s*({_MEAS})$")
_SUFFIX = re.compile(r"(?<=.)(case|box|bag|tub|tray|ctn|carton)$")
_COUNT = re.compile(r"^(\d+)\s*(?:s|ct|pk|pack|pcs|x)?$")


def parse_pack(pack: str | None) -> tuple[str, float] | None:
    """(kind, base amount) for a pack text such as '12x1L', or None when it is empty or unreadable."""
    p = (pack or "").strip().lower().replace(" ", "")
    p = _SUFFIX.sub("", p)  # "5kg case" -> "5kg", "12 box" -> "12"
    if p in ("dozen", "doz"):
        return "each", 12.0
    if not p or p in ("each", "ea", "-"):
        return None
    if m := _MULTI.match(p):
        kind, mult = MEASURES[m.group(3)]
        return kind, float(m.group(1)) * float(m.group(2)) * mult
    if m := _SINGLE.match(p):
        kind, mult = MEASURES[m.group(2)]
        return kind, float(m.group(1)) * mult
    if m := _COUNT.match(p):
        return "each", float(m.group(1))
    return None


def base_amount(pack: str | None, unit: str | None) -> tuple[str, float]:
    """The base amount that one priced unit contains: (kind, amount)."""
    u = (unit or "").strip().lower()
    if u in MEASURES:
        return MEASURES[u][0], MEASURES[u][1]
    return parse_pack(pack) or ("each", 1.0)


def cost_per_base(unit_price: float, pack: str | None, unit: str | None) -> tuple[str, float]:
    kind, amount = base_amount(pack, unit)
    return kind, float(unit_price) / amount


def packs_equivalent(a: tuple, b: tuple, tolerance: float = 0.005) -> bool:
    """True when two (unit_price, pack, unit) triples cost the same per g/ml/each within the tolerance (0.5%)."""
    ka, ca = cost_per_base(*a)
    kb, cb = cost_per_base(*b)
    if ka != kb:
        return False
    if ca == cb:
        return True
    return abs(ca - cb) <= tolerance * max(abs(ca), abs(cb))
