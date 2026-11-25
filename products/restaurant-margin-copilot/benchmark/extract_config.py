"""The frozen part of the extractor: prompt, JSON schema and run configuration.

KILL-TEST.md: prompt and config are tuned on the DEV set only, then frozen. `python freeze.py` writes FROZEN.json with
the SHA-256 of everything in this file that affects a call (PROMPT, SCHEMA, CONFIG and the price table). extract.py refuses
`--set test` unless the hash in FROZEN.json matches this file. Change anything here after freezing and the test run is refused.
"""
from __future__ import annotations

import hashlib
import json

import budget

PROMPT = """You read one page of a UK supplier invoice, credit note or till receipt from a restaurant's supplier, as an image.
The image may be a flat scan or a phone photo that is rotated, skewed, blurred, shadowed or crumpled.
Return only the JSON that the schema asks for. Copy what is printed. Never calculate, guess or repair numbers.

How to read the page:
1. First list the column headers you can see (column_headers), left to right, or an empty list when the layout has none
   (till receipts and simple butcher or greengrocer notes often have none).
2. Then go through the product rows from top to bottom, one row at a time. For each row, first write row_text: the whole
   printed row, left to right, as one string, before you fill in the fields. The photo may be rotated or skewed, so a row
   runs along a tilted line: follow the text baseline, and use stripes, rules and the row's own description to keep a row's
   numbers together. Numbers belong to the row whose text line they sit on, not to the row above or below. Some layouts
   print a row on two text lines (description, then "qty x price" and the amount): treat both as one row.
3. Self-check each row: line_total should be close to qty x unit_price less any discount percentage. If it is not, look at
   the row again; you may have attached a number from a neighbouring row. Still report the values exactly as printed.

Header (null when this page does not show it):
- supplier_name, invoice_number (the invoice, credit note or sale reference, as printed), invoice_date as YYYY-MM-DD
  (UK dates are day first).
- is_credit_note is true when the page says CREDIT NOTE or CREDIT, false when it says invoice, sale or similar.

Lines: one entry per product row on this page, in page order. Skip headings, subtotals, VAT summaries and the legend.
- description: the product text exactly as printed, abbreviations included (for example "BEEF MINCE 20% 5KG").
- pack_size: the size of ONE priced unit of the product, in the form a person would write it: "12x1L", "6 x 2.5kg", "5kg",
  "24x330ml", "dozen", "180", or "" when the row has no pack. Some layouts print the pack in its own column, others inside
  the product description ("BEEF MINCE 20% 5KG" is a 5kg pack; "CHIPS 2.5KG X4" is 4x2.5kg; "TOMATO PASSATA 6X700G" is
  6x700g): copy it from there, written as count x size ("4x2.5kg", not "2.5KG X4") or a single size ("5kg"), and leave
  the description unchanged. When a count is followed by a total weight, as in "X2 400G", the pack is that total: "400g". pack_size is never the quantity bought: text such as
  "2 x 4.99" or "6 x" on a receipt means quantity times price, not a pack. A weighed line priced per kg (for example
  "1.730 kg @ 1.15/kg") has pack_size "".
- unit: what unit_price is charged per: "case", "each", "kg", "pack" or "box". Use "kg" for lines sold by weight and priced
  per kg. Use the unit column when there is one. Without one, use "case" for multi-packs such as 12x1L, "pack" or "each" for
  a single pack, and "each" when unsure.
- qty: the number of units, or the weight in kg for weighed lines. On a credit note (the page says CREDIT NOTE or CREDIT,
  or its line totals are negative), and on any line that is a credit or return, qty is negative and line_total is negative,
  even when the page prints the quantity without a minus sign. qty always has the same sign as line_total: a negative
  line_total means a negative qty. unit_price stays positive.
- unit_price: the price per unit before any discount, in pounds, as printed.
- line_total: the net amount for the row after any discount, in pounds, before VAT. Never include VAT. Negative for credits.
- vat_rate: the VAT percentage for the row as a number, 0, 5 or 20. If the page uses code letters (A, B, S, Z...), use the
  legend or summary on the page to turn the code into a percentage. If a VAT column shows a percentage, use it.

Totals: net, vat and gross exactly as printed in the totals block of this page, in pounds (negative on credit notes).
Use null for each total this page does not print. A page that says "continued" has null totals.
"""

_NUM = {"type": ["number", "null"]}
_STR = {"type": ["string", "null"]}
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["column_headers", "supplier_name", "invoice_number", "invoice_date", "is_credit_note", "lines", "totals"],
    "properties": {
        "column_headers": {"type": "array", "items": {"type": "string"}},
        "supplier_name": _STR,
        "invoice_number": _STR,
        "invoice_date": _STR,
        "is_credit_note": {"type": ["boolean", "null"]},
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["row_text", "description", "pack_size", "unit", "qty", "unit_price", "line_total", "vat_rate"],
                "properties": {
                    "row_text": {"type": "string"},
                    "description": {"type": "string"},
                    "pack_size": {"type": "string"},
                    "unit": {"type": "string", "enum": ["case", "each", "kg", "pack", "box"]},
                    "qty": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "line_total": {"type": "number"},
                    "vat_rate": {"type": "number"},
                },
            },
        },
        "totals": {
            "type": "object",
            "additionalProperties": False,
            "required": ["net", "vat", "gross"],
            "properties": {"net": _NUM, "vat": _NUM, "gross": _NUM},
        },
    },
}

CONFIG = {
    "deployment_env": "AZURE_OPENAI_DEPLOYMENT_MINI",  # never the pro deployment
    "price_model": "gpt-5-mini",
    "reasoning_effort": "medium",  # chosen on DEV (results/DEV-TUNING.md): low was 78% vs medium 86-87%
    "max_output_tokens": 16000,
    "retry_max_output_tokens": 32000,  # one retry after length, invalid JSON or timeout; then the page counts as wrong
    "timeout_s": 180,
    "max_long_edge_px": 2048,
    "image_detail": "high",
    "transient_retries": 3,  # 429 and 5xx only (nothing billed), with backoff; separate from the one 32k retry
    "backoff_base_s": 2.0,
    "est_image_tokens": 2200,  # pre-call estimate for the budget guard (high detail, 2048 px: about 1100 real)
}


def canonical() -> str:
    return json.dumps({"prompt": PROMPT, "schema": SCHEMA, "config": CONFIG, "prices": budget.PRICES}, sort_keys=True,
                      separators=(",", ":"))


def frozen_hash() -> str:
    return hashlib.sha256(canonical().encode()).hexdigest()
