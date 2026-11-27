"""A5 and A6c review sheet: 100 claims from the E2 exports with a fixed seed, or all of them if fewer (SPEC A5)."""
from __future__ import annotations

import csv
import random
from pathlib import Path

A5_SEED = 20261127
SAMPLE_SIZE = 100
COLUMNS = ["claim_id", "draft", "claim", "cited", "passage_text", "supported_yes_no", "unsupported_or_contradicted_found", "notes"]


def sample_claims(claims: list[dict], n: int = SAMPLE_SIZE, seed: int = A5_SEED) -> list[dict]:
    """claims: [{"id", "draft", "claim", "cited", "passage_text"}]. Sorted by id first, so the draw depends only on the seed
    and the set of claims, never on the order they were exported in. Fewer than n: all of them."""
    ordered = sorted(claims, key=lambda c: str(c["id"]))
    if len(ordered) <= n:
        return ordered
    chosen = random.Random(seed).sample(range(len(ordered)), n)
    return [ordered[i] for i in sorted(chosen)]


def write_sheet(claims: list[dict], path: Path | str, n: int = SAMPLE_SIZE, seed: int = A5_SEED) -> int:
    rows = sample_claims(claims, n, seed)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for c in rows:
            w.writerow([c["id"], c.get("draft", ""), c["claim"], " ".join(f"E-{i}" for i in c.get("cited", [])),
                        c.get("passage_text", ""), "", "", ""])
    return len(rows)
