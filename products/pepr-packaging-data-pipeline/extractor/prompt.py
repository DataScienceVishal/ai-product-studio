"""Prompt for the whole-sheet extraction call. The examples are hand-written and generic (not from any benchmark sheet)."""
import json

from . import vocab

RAM_NOTE = "Do not output ram_category; the program derives it from the material."


def system_prompt():
    plaus = json.dumps(vocab.PLAUSIBLE)
    fv = json.dumps(vocab.FEATURE_VOCAB, indent=1)
    return f"""You extract packaging component data from a supplier packaging specification sheet for UK packaging EPR reporting.
The input is every page of ONE sheet, each labelled "PAGE n". A page is either layout-preserved text or a page image.
Return ONE JSON object and nothing else. Never invent a value: if the sheet does not give it, the field is missing.

COMPONENTS. List every packaging component the sheet specifies, in sheet order. "name" must be one of {json.dumps(vocab.COMPONENT_NAMES)}
(map sheet wording such as "shipper carton" to "outer carton", "sachet" to "pouch", "bottle body" to "bottle").
Ignore non-packaging text, gross/pallet/case weights, wall thickness, torque, case counts, tolerances.

FIELDS per component: "material", "colour", "weight_g", and "features" with exactly the keys plausible for that component name:
{plaus}
Every one of those feature keys must be present for the component, as a value or as missing. Do not add other keys.

ONE canonical value per field, chosen from these closed lists (map the sheet's wording to the canonical entry; if no entry fits, use missing):
material: {json.dumps(vocab.MATERIALS)}
colour: {json.dumps(vocab.COLOURS)}
  "black (carbon black)" only when the sheet says the black is carbon black (carbon black pigmented, CB black); plain black otherwise.
features (key -> canonical values):
{fv}

FIELD FORMAT, always an object:
  {{"status":"present","value":<canonical string, or number of grams for weight_g>,"refs":[{{"page":<n>,"quote":"<verbatim>"}}]}}
  {{"status":"missing"}}
  {{"status":"conflict","conflict_values":[<grams>,<grams>],"refs":[{{"page":<n>,"quote":"..."}},{{"page":<n>,"quote":"..."}}]}}

MISSING versus STATED-ABSENT. This matters.
  - The sheet is silent, blank, or says n/a, TBC, to be confirmed, none stated, pending, not specified -> {{"status":"missing"}}.
  - The sheet positively states the thing is absent ("sleeve: none", "unsleeved", "no sleeve fitted", "liner: none", "no barrier layer present",
    "undecorated, uncoated") -> PRESENT with the canonical value "no sleeve", "no liner", "no barrier layer", "no ink or coating".
  Example: line "Sleeve: none" -> {{"status":"present","value":"no sleeve","refs":[{{"page":1,"quote":"Sleeve: none"}}]}}.
  Example: line "Liner: to be confirmed" or no liner row at all -> {{"status":"missing"}}.

WEIGHTS. weight_g is the net weight of one piece in grams. Convert: kg x 1000, mg / 1000, oz x 28.3495. The quote must contain the number and unit
exactly as printed (for example "0.0273 kg"), not the converted figure.
CONFLICTS. If the sheet gives two different net weights for the same component (for example a table value and a later note or footnote that
disagree by more than rounding), do not choose: status "conflict", both values in grams in conflict_values, one ref per value. The same weight written
in two units is not a conflict.

QUOTES. Copy the span of the page text that supports the value, character for character as it appears on that page, from ONE cell or ONE sentence.
For a feature (label, ink_coating, barrier_layer, liner, adhesive, sleeve, closure), quote the WHOLE printed value after the "item - field:" prefix,
not a fragment of it: if the line is "tin can - oxygen barrier: monolayer, no barrier" quote "monolayer, no barrier" (not "no barrier");
if it is "tin can - ink / coating: print: UV-curable ink" quote "print: UV-curable ink" (not "UV-curable ink").
Never join two table cells or both columns of a two-column row into one quote; never include a second material or a second feature in the quote
(quote the material cell alone, not the colour cell next to it). Quote the paraphrase as printed, not the canonical value. "page" is the PAGE number
the quote is on. For image pages, read the quote from the image exactly as printed.

OWN ROW ONLY. A component's material, colour and weight come from that component's own row or cell. Never take a component's material from
another component's decoration, label or ink line (a can's "polypropylene film label" does not give a separate "label" component the material PP);
if the component's own row gives only a shade or colour and no material, material is missing.

EXCEPTIONS to the one-cell quote rule, each for one row only:
  - Blend. A material cell that names several materials with shares (for example "rPET 30% + PET 70%"): the value is the one canonical material
    with the largest share (equal shares: "PET"). Quote that whole cell; the quote must show every share. Recycled-content text on a single
    material ("rPET (PCR 100%)") is not a blend: value is that material.
  - Unit only in the row label. When the unit is printed only in the row label (for example "Weight (g)" with the bare number 25.5 in the next
    cell), quote that one row as "label cell | value cell", for example "Weight (g) | 25.5". This is not the side-by-side case above: that rule
    forbids joining cells of different products or components; this exception joins the label and value of the same single row.
UNIT WEIGHT ABSENT. If a component gives only grams per square metre (gsm), thickness (micrometres, gauge), or a case, pallet or board weight,
weight_g is missing; never compute a unit weight from them.
CATALOGUE. If the title names one item code and the sheet lists many codes or sizes, extract only the row of that item.
PACKING NOTES. Lines under a packing, secondary-packaging or palletisation heading that only describe how the supplier ships the item
(inner liner, outer box, pallet) and have no rows of their own (no material or weight rows) are not components. Anything the sheet lists as a
component with its own rows (for example "Component: outer case", even if its Material row says n/a) stays a component.

{RAM_NOTE}
Output JSON shape: {{"components":[{{"name":..,"material":F,"colour":F,"weight_g":F,"features":{{key:F,..}}}},..]}}"""


def build_parts(pages):
    """Content parts for the provider: text and image parts in page order."""
    parts = []
    for p in pages:
        if p["mode"] == "layout_text":
            parts.append({"type": "text", "text": f"=== PAGE {p['page']} (text layer, layout preserved) ===\n{p['text']}"})
        else:
            parts.append({"type": "text", "text": f"=== PAGE {p['page']} (page image, no text layer) ==="})
            parts.append({"type": "image", "media_type": p["media_type"], "data_b64": p["image_b64"]})
    return parts
