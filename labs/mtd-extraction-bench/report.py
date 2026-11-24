"""Print markdown tables from results/full.json + raw outputs (no API calls). Includes a free threshold sweep."""
import json
from pathlib import Path
import run_full, score, gen2, calib

H = Path(__file__).parent
full = json.loads((H / "results/full.json").read_text())
FMT = {"pdf": "Clean PDF", "csv": "CSV export", "xlsx": "Owner spreadsheet", "scan": "Scan (image)", "photo": "Phone photo (image)"}


def agg(rows, key):
    """Pooled ratio: sum assisted seconds / sum manual seconds over docs."""
    a = sum(r[key] for r in rows if "manual_seconds" in r); m = sum(r["manual_seconds"] for r in rows if "manual_seconds" in r)
    return a / m if m else None


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def lines_for(name):
    return json.loads((run_full.RAW / f"{name}.json").read_text())["lines"]


rows = []
for name, s in full["scores"].items():
    if s.get("not_run"):
        continue
    rows.append((name, s))
print("## per document (model_only | rules_and_risky_cap)\n")
print("| doc | kind | persona | cat acc | routed | silent errs | ratio (pilot formula) | ratio (silent charged) | calibrated: cat acc / routed / silent / ratio silent |")
print("|---|---|---|---|---|---|---|---|---|")
for name, s in rows:
    m, c = s["model_only"], s["rules_and_risky_cap"]
    print(f"| {name} | {s['kind']} | {s['persona']} | {m['category_acc']} | {m['routed_to_review']} | {m['silent_errors']} | {m['review_time_ratio']} | {m['review_time_ratio_silent']} | {c['category_acc']} / {c['routed_to_review']} / {c['silent_errors']} / {c['review_time_ratio_silent']} |")
print("\n## per format (pooled over docs)\n")
print("| format | docs | lines | model cat acc | ratio pilot formula | ratio silent charged | calibrated ratio (pilot formula) | calibrated ratio silent charged | silent errors per 100 auto lines (model / calibrated) |")
print("|---|---|---|---|---|---|---|---|---|")
for kind in ["pdf", "csv", "xlsx", "scan", "photo", "ALL"]:
    sub = [s for _, s in rows if kind == "ALL" or s["kind"] == kind]
    if not sub:
        continue
    def pool(tag, key): return agg([s[tag] for s in sub], key)
    n = sum(s["model_only"]["lines_truth"] for s in sub)
    cat = sum(s["model_only"]["category_acc"] * s["model_only"]["lines_truth"] for s in sub) / n
    def per100(tag): 
        e = sum(s[tag]["silent_errors"] for s in sub); a = sum(s[tag]["auto_lines"] for s in sub); return f"{100*e/a:.1f}" if a else "n/a"
    print(f"| {FMT.get(kind, 'All docs')} | {len(sub)} | {n} | {pct(cat)} | {pct(pool('model_only','assisted_seconds'))} | {pct(pool('model_only','assisted_seconds_silent'))} | {pct(pool('rules_and_risky_cap','assisted_seconds'))} | {pct(pool('rules_and_risky_cap','assisted_seconds_silent'))} | {per100('model_only')} / {per100('rules_and_risky_cap')} |")
print("\n## threshold sweep (all docs, calibrated, silent errors charged)\n")
print("| threshold | routed % | silent errs | ratio pilot formula | ratio silent charged |")
print("|---|---|---|---|---|")
meta = {n: {"kind": k, "persona": p} for n, k, l, p, s in gen2.PLAN}
for th in [0.7, 0.8, 0.9, 0.95]:
    res = []
    for name, s in rows:
        sc = run_full.score_variants(name, meta[name], lines_for(name), threshold=th)["rules_and_risky_cap"]
        res.append(sc)
    n = sum(r["lines_truth"] for r in res)
    routed = sum(r["routed_to_review"] * r["lines_truth"] for r in res) / n
    print(f"| {th} | {pct(routed)} | {sum(r['silent_errors'] for r in res)} | {pct(agg(res,'assisted_seconds'))} | {pct(agg(res,'assisted_seconds_silent'))} |")
print("\n## ambiguous lines (truth flagged ambiguous): model category accuracy\n")
tot = ok = 0
for name, s in rows:
    truth = json.loads((run_full.DATA / f"{name}.truth.json").read_text())["lines"]
    for t, p in score.match_lines(truth, lines_for(name)):
        if t.get("ambiguous"):
            tot += 1; ok += bool(p and p.get("category") == t["category"])
print(f"ambiguous lines {tot}, model correct {ok} ({pct(ok/tot if tot else None)})")
print("\n## tokens and cost\n")
b = full["budget"]
print("| doc | in tokens | out tokens | reasoning | latency s | USD |")
print("|---|---|---|---|---|---|")
usd = {}
for l in b["log"]:
    usd[l["label"]] = usd.get(l["label"], 0) + l["usd"]
for n, r in full["runs"].items():
    print(f"| {n} | {r.get('input_tokens')} | {r.get('output_tokens')} | {r.get('reasoning_tokens')} | {r.get('latency_s')} | {usd.get(n, 0):.2f} |")
print(f"\nTOTAL: calls {b['calls']} of {b['max_calls']}, input {b['input_tokens']}, output {b['output_tokens']}, ${b['usd']:.2f} of ${b['cap_usd']:.2f}")
