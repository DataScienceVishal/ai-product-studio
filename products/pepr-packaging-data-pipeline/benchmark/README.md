# pEPR spec-sheet extraction benchmark (T-56)

Kill test and pass mark: `state/ideas/pepr-packaging-data-pipeline.md`, section "Proof test (T-56)". The pass mark is fixed there and is not repeated here as a source of truth.

## Layout (planned)

```
benchmark/
  truth.schema.json     JSON Schema for one sheet's truth
  gen/                  deterministic generator (slice 2)
  sheets/S001.pdf ...   30 synthetic test sheets
  tuning/T001.pdf ...   5 tuning sheets, different seed (prompt tuning only)
  truth/S001.json ...   hand-specified truth, one per sheet
  public/               genuinely public spec PDFs (licence noted), reported separately
  score.py              scorer (slice 4)
```

## Dataset plan

30 synthetic sheets, seed fixed in the generator, three tiers of 10:

| Tier | Layouts mixed in |
|---|---|
| clean | one component, a table, g only, all fields present |
| moderate | multi-component packs (bottle, cap, label, carton), prose, mixed units (g, kg, oz, mg), some missing fields |
| messy | scanned-look (raster, noise, skew), contradictory values between table and notes, features buried in prose, missing fields, abbreviations ("HDPE nat.", "PP blk") |

Truth is written by the generator from the same data model that renders the sheet, so it is exact. Each present value carries the page and a quote that appears on that page. Contradictions are recorded with `status: conflict` and both values. Absent fields are `status: missing`.

## Truth format

One JSON file per sheet, validated by `truth.schema.json`. Per component: `name`, `material`, `colour`, `weight_g` (grams), `features` (label, closure, ink_coating, sleeve, adhesive, barrier_layer, each optional), `ram_category`. Each field object has `status` (`present`, `missing`, `conflict`), `value` or `conflict_values`, and `refs` (`page`, `quote`). Example:

```json
{
  "sheet_id": "S014", "tier": "messy", "layout": "contradictory", "source": "synthetic", "seed": 20261124,
  "components": [{
    "name": "bottle",
    "material": {"status": "present", "value": "PET", "accepted_values": ["polyethylene terephthalate"],
                 "refs": [{"page": 1, "quote": "Body: PET, clear"}]},
    "colour": {"status": "present", "value": "clear", "refs": [{"page": 1, "quote": "Body: PET, clear"}]},
    "weight_g": {"status": "conflict", "conflict_values": [24, 26],
                 "refs": [{"page": 1, "quote": "Weight 24 g"}, {"page": 2, "quote": "net 26 g"}]},
    "features": {"label": {"status": "missing"}, "closure": {"status": "present", "value": "PP cap, no liner",
                 "refs": [{"page": 1, "quote": "Closure: PP, no liner"}]}},
    "ram_category": "plastic"
  }]
}
```

## Scoring rules (summary)

Normalisation: case, whitespace, listed synonyms, units to g (tolerance 1% or 0.1 g). Components matched by name and material. Untraced values (page reference whose quote lacks the value) are counted separately and must be 0. Fabricated values for `missing` fields and unflagged conflicts are reported separately. Public PDFs are scored apart and never change the pass mark.
