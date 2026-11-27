"""Split document pages into evidence passages of 120 to 400 words (DESIGN 4.2).

Split at headings and paragraphs, pack paragraphs into passages, never cross a document, keep page_from and page_to.
A section shorter than 120 words is merged with what follows rather than left as a stub."""
from __future__ import annotations

import re
from dataclasses import dataclass

MIN_WORDS, MAX_WORDS = 120, 400
_NUMBERED = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?|[A-Z]\.)\s+\S")
_SMALL = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with", "our"}


@dataclass
class Passage:
    heading: str
    text: str
    page_from: int
    page_to: int


def looks_like_heading(line: str) -> bool:
    line = line.strip()
    words = line.split()
    if not line or len(line) > 80 or len(words) > 10 or line[-1] in ".,;:?!":
        return False
    if not any(c.isalpha() for c in line):
        return False
    if line.isupper() and len(words) >= 1 and len(line) >= 3:
        return True
    if _NUMBERED.match(line) and len(words) <= 8:
        return True
    alpha = [w for w in words if w[0].isalpha() and w.lower() not in _SMALL]
    return len(words) >= 2 and bool(alpha) and all(w[0].isupper() for w in alpha)


def _split_long(text: str) -> list[str]:
    """A paragraph over MAX_WORDS is cut at sentence ends (or hard at MAX_WORDS for a run-on)."""
    if len(text.split()) <= MAX_WORDS:
        return [text]
    out, cur, n = [], [], 0
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = sentence.split()
        while len(words) > MAX_WORDS:
            if cur:
                out.append(" ".join(cur)); cur, n = [], 0
            out.append(" ".join(words[:MAX_WORDS])); words = words[MAX_WORDS:]
        if n + len(words) > MAX_WORDS and cur:
            out.append(" ".join(cur)); cur, n = [], 0
        cur.append(" ".join(words)); n += len(words)
    if cur:
        out.append(" ".join(cur))
    return out


def chunk_pages(pages: list[dict]) -> list[Passage]:
    """pages: [{"text", "headings"}] in page order, page numbers 1-based by position."""
    # units: (page_no, kind, text) with kind "h" or "p"
    units: list[tuple[int, str, str]] = []
    for page_no, page in enumerate(pages, start=1):
        explicit = {h.strip() for h in page.get("headings", [])}
        for block in re.split(r"\n\s*\n", page["text"]):
            lines, para = [ln.strip() for ln in block.split("\n") if ln.strip()], []
            for line in lines:
                if line in explicit or looks_like_heading(line):
                    if para:
                        units.append((page_no, "p", " ".join(para))); para = []
                    units.append((page_no, "h", line))
                else:
                    para.append(line)
            if para:
                units.append((page_no, "p", " ".join(para)))

    passages: list[Passage] = []
    heading, cur, words, p_from, p_to, cur_head = "", [], 0, 0, 0, ""

    def flush() -> None:
        nonlocal cur, words, p_from, p_to, cur_head
        if cur:
            passages.append(Passage(cur_head[:300], "\n\n".join(cur), p_from, p_to))
        cur, words, cur_head = [], 0, ""

    for page_no, kind, text in units:
        if kind == "h":
            if words >= MIN_WORDS:
                flush()
            heading = text
            if not cur:
                cur_head, p_from = heading, page_no
            cur.append(text)  # the heading line stays in the passage text (it is searchable)
            p_to = page_no
            continue
        for piece in _split_long(text):
            n = len(piece.split())
            if cur and words + n > MAX_WORDS:
                flush()
                cur_head = heading
            if not cur:
                p_from = page_no
            cur.append(piece)
            words += n  # heading lines are not counted
            p_to = page_no
            if not cur_head:
                cur_head = heading
    if cur:
        if words and words < MIN_WORDS and passages and len((passages[-1].text + " " + " ".join(cur)).split()) <= MAX_WORDS:
            last = passages.pop()
            passages.append(Passage(last.heading, last.text + "\n\n" + "\n\n".join(cur), last.page_from, p_to))
        else:
            flush()
    return [p for p in passages if p.text.strip() and any(c.isalnum() for c in p.text)]
