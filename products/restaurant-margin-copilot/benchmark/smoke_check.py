"""Score a few already-extracted pages in isolation (smoke runs): python smoke_check.py results/dev-smoke DEV-002_p1 ..."""
import json
import sys
from pathlib import Path

import score

HERE = Path(__file__).resolve().parent
ext = Path(sys.argv[1])
for page_id in sys.argv[2:]:
    inv_id, pn = page_id.rsplit("_p", 1)
    t = json.loads((HERE / "data" / "dev" / f"{inv_id}.json").read_text())
    t = {**t, "lines": [ln for ln in t["lines"] if ln["page"] == int(pn)]}
    res = score.score_invoice(t, [json.loads((ext / f"{page_id}.json").read_text())])
    print(page_id, t["layout"], "lines", res["truth_lines"], "correct", res["correct"], "hallucinated", res["hallucinated"])
    for d in res["line_errors"]:
        print("   wrong:", d)
    print("   missing:", res["missing"][:5], "extra:", res["hallucinated_lines"][:3])
