"""Re-score saved model outputs (no API calls). Prints a markdown table and updates pilot.json scores."""
import json
from pathlib import Path
import score

HERE = Path(__file__).parent
p = json.loads((HERE / "results/pilot.json").read_text())
parsed = {}
for name in p["runs"]:
    f = HERE / f"results/raw_{name}.json"
    parsed[name] = json.loads(f.read_text()) if f.exists() else {"lines": []}
p["scores"] = score.score_all(HERE / "data", parsed)
(HERE / "results/pilot.json").write_text(json.dumps(p, indent=1))
cols = ["date_acc", "amount_acc", "desc_acc", "balance_acc", "category_acc", "routed_to_review",
        "auto_category_acc", "undetected_errors_in_auto", "review_time_ratio"]
print("| doc | " + " | ".join(cols) + " |")
for k, s in p["scores"].items():
    print(f"| {k} | " + " | ".join(str(s[c]) for c in cols) + " |")
