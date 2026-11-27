"""A5 and A6c review sheet: 100 claims from the E2 exports with a fixed seed, or all of them if fewer (SPEC A5)."""
from __future__ import annotations

import csv
import random
from pathlib import Path

A5_SEED = 20261127
SAMPLE_SIZE = 100
COLUMNS = ["claim_id", "draft", "claim", "cited", "passage_text", "supported_yes_no", "unsupported_or_contradicted_found", "notes"]


def gap_exempt_rows(drafts: list[dict]) -> list[dict]:
    """The gap sentences A4 exempts, as review rows (id "gap-<draft>-<i>", nothing cited), so a person reads what the rule let
    through. drafts: [{"id", "text"}] (the E2 exports). Imported lazily: score pulls in the app's sentence splitter."""
    from eval import score
    rows = []
    for d in drafts:
        for i, sentence in enumerate(score.split_claims(d["text"])[1]):
            rows.append({"id": f"gap-{d['id']}-{i:03d}", "draft": d["id"], "claim": sentence, "cited": [],
                         "passage_text": "(gap sentence exempt from A4: is anything asserted here?)"})
    return rows


def sample_claims(claims: list[dict], n: int = SAMPLE_SIZE, seed: int = A5_SEED, gap_exempt: list[dict] | None = None) -> list[dict]:
    """claims: [{"id", "draft", "claim", "cited", "passage_text"}]. gap_exempt (from gap_exempt_rows) joins the population, so
    the A4 exemption is human-checked too. Sorted by id first, so the draw depends only on the seed
    and the set of claims, never on the order they were exported in. Fewer than n: all of them."""
    ordered = sorted([*claims, *(gap_exempt or [])], key=lambda c: str(c["id"]))
    if len(ordered) <= n:
        return ordered
    chosen = random.Random(seed).sample(range(len(ordered)), n)
    return [ordered[i] for i in sorted(chosen)]


def write_sheet(claims: list[dict], path: Path | str, n: int = SAMPLE_SIZE, seed: int = A5_SEED,
                gap_exempt: list[dict] | None = None) -> int:
    rows = sample_claims(claims, n, seed, gap_exempt)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for c in rows:
            w.writerow([c["id"], c.get("draft", ""), c["claim"], " ".join(f"E-{i}" for i in c.get("cited", [])),
                        c.get("passage_text", ""), "", "", ""])
    return len(rows)
