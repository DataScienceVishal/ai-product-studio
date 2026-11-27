"""ScriptedFakeAI: free, deterministic answers for tests, e2e and the offline demo (DESIGN 4.3).

Two modes:
  recorded   run_task asks `recorded_answer(task, key)` first; a file `<recorded_dir>/<task>/<key>.json` holds real
             model output written by the recording run (R1). The key is the canonical payload key, computed before the
             nonce, so the nonce never makes a recording unfindable.
  heuristic  `complete()` builds a deterministic answer from the DATA blocks, chosen by the schema title
             (ExtractOutput, DraftOutput, ClaimcheckOutput).

It reads only its own recorded_dir. It never reads eval/keys (ground truth is read by the scorer alone, the T-80
lesson): a recorded_dir inside any `eval` directory is refused.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..ai import AIResult

DEFAULT_RECORDED_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "recorded"
_KEY = re.compile(r"^[0-9a-f]{64}$")
_TASK = re.compile(r"^[a-z_]{1,20}$")
_BLOCK = re.compile(r"^(\w+):\n<<<DATA-([0-9a-f]+)>>>\n(.*?)\n<<<END-\2>>>", re.S | re.M)


def parse_blocks(user: str) -> dict[str, str]:
    return {m.group(1): m.group(3) for m in _BLOCK.finditer(user)}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _extract(blocks: dict[str, str]) -> dict:
    items, page = [], 1
    for line in blocks.get("chunk", "").splitlines():
        marker = re.match(r"^\[page (\d+)\]", line.strip())
        if marker:
            page = int(marker.group(1))
            continue
        q = re.match(r"^\s*(?:Q(?:uestion)?\s*)?(\d+(?:\.\d+)*)[.)]\s+(\S.*)$", line)
        if q:
            limit = re.search(r"maximum (?:of )?(\d[\d,]*) words", line, re.I)
            items.append({"ref": q.group(1), "kind": "question", "text": q.group(2).strip(),
                          "word_limit": int(limit.group(1).replace(",", "")) if limit else None, "page_limit": None,
                          "marks": None, "weight_pct": None, "pass_fail": None, "deadline": None,
                          "source_page": page, "source_quote": q.group(2).strip()[:200]})
    return {"items": items}


def _passages(text: str) -> dict[int, str]:
    return {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"\[E-(\d+)\]\s*(.+)", text)}


def _draft(blocks: dict[str, str]) -> dict:
    passages = _passages(blocks.get("passages", ""))
    if not passages:
        gap = "[NEEDS FIRM INPUT: no evidence found for this question]"
        return {"answer": gap, "gaps": [gap], "used_ids": []}
    parts = [f"{(_sentences(text) or [text])[0]} [E-{n}]" for n, text in sorted(passages.items())]
    return {"answer": " ".join(parts), "gaps": [], "used_ids": sorted(passages)}


def _claimcheck(blocks: dict[str, str]) -> dict:
    passages = _passages(blocks.get("passages", ""))
    claims = []
    for sentence in _sentences(blocks.get("draft", "")):
        cited = [int(n) for n in re.findall(r"\[E-(\d+)\]", sentence)]
        body = re.sub(r"\s*\[E-\d+\]", "", sentence).strip()
        source = " ".join(passages.get(n, "") for n in cited)
        facts = re.findall(r"\d[\d,.]*|\b[A-Z][A-Za-z0-9]+\b", body)
        ok = bool(cited) and all(f in source for f in facts)
        claims.append({"span": body, "kind": "factual", "cited_ids": cited, "verdict": "supported" if ok else "unsupported",
                       "evidence_quote": source[:200] if ok else None,
                       "reason": None if ok else "figures or names not found in the cited passage"})
    return {"claims": claims}


def _skeleton(schema: dict, root: dict | None = None):
    """The smallest value that satisfies a JSON schema (for a task with no heuristic and no recording)."""
    root = root or schema
    if "$ref" in schema:
        return _skeleton(root["$defs"][schema["$ref"].rsplit("/", 1)[-1]], root)
    kind = schema.get("type")
    if "anyOf" in schema:
        return _skeleton(schema["anyOf"][0], root)
    if kind == "object" or "properties" in schema:
        return {k: _skeleton(v, root) for k, v in schema.get("properties", {}).items()}
    return {"string": "", "integer": 0, "number": 0, "boolean": False, "array": [], "null": None}.get(kind)


HEURISTICS = {"ExtractOutput": _extract, "DraftOutput": _draft, "ClaimcheckOutput": _claimcheck}


class ScriptedFakeAI:
    name = "fake"
    output_headroom = 0
    disabled = False
    disabled_message = None
    cacheable = False  # canned answers are not stored in ai_cache: the demo cache holds real recorded output only

    def __init__(self, recorded_dir: Path | str | None = None):
        directory = Path(recorded_dir) if recorded_dir is not None else DEFAULT_RECORDED_DIR
        if "eval" in {part.lower() for part in directory.resolve().parts}:
            raise ValueError("ScriptedFakeAI never reads from an eval directory (answer keys live there)")
        self.recorded_dir = directory
        self.calls: list[dict] = []

    def recorded_answer(self, task: str, key: str) -> dict | None:
        if not _TASK.match(task) or not _KEY.match(key):
            return None
        path = self.recorded_dir / task / f"{key}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["output"] if isinstance(data, dict) and "output" in data else data

    def complete(self, system: str, user: str, max_output_tokens: int = 1200, *, json_schema: dict | None = None,
                 effort: str | None = None) -> AIResult:
        self.calls.append({"json_schema": json_schema, "effort": effort})
        title = (json_schema or {}).get("title")
        if json_schema is None:
            words = [w for w in user.split() if not w.startswith("<<<")]
            return AIResult(text="Summary: " + " ".join(words[:25]), input_tokens=len(words),
                            output_tokens=min(len(words), 25) + 1, model="fake")
        text = json.dumps(HEURISTICS[title](parse_blocks(user)) if title in HEURISTICS else _skeleton(json_schema))
        return AIResult(text=text, input_tokens=len(user.split()), output_tokens=len(text.split()), model="fake")
