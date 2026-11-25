"""Check the built frontend's index.html for anything the production CSP would block.

The app serves HTML with `script-src 'self'` and `style-src 'self'` (no 'unsafe-inline'), so an inline
<script> or <style> block, or a style= attribute, would be silently blocked in the browser. Stdlib only, so
CI's frontend job can run it right after `npm run build` without the backend's dependencies:

    python3 ../scripts/check_built_html.py dist/index.html

backend/tests/test_spa.py imports `problems` so the rules are unit-tested in every backend run too.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_INLINE_SCRIPT = re.compile(r"<script\b(?![^>]*\ssrc\s*=)[^>]*>", re.IGNORECASE)
_STYLE_BLOCK = re.compile(r"<style\b", re.IGNORECASE)
_STYLE_ATTR = re.compile(r"<[^>]*\sstyle\s*=", re.IGNORECASE)
_EVENT_ATTR = re.compile(r"<[^>]*\son[a-z]+\s*=", re.IGNORECASE)


def problems(html: str) -> list[str]:
    """Return one message per CSP-blocked construct found; empty means the page is clean."""
    found = []
    if _INLINE_SCRIPT.search(html):
        found.append("inline <script> (no src) would be blocked by script-src 'self'")
    if _STYLE_BLOCK.search(html):
        found.append("<style> block would be blocked by style-src 'self'")
    if _STYLE_ATTR.search(html):
        found.append("style= attribute would be blocked by style-src 'self'")
    if _EVENT_ATTR.search(html):
        found.append("inline event handler (on...=) would be blocked by script-src 'self'")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_built_html.py <path/to/dist/index.html>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"FAIL: {path} not found (run npm run build first)", file=sys.stderr)
        return 1
    found = problems(path.read_text(encoding="utf-8"))
    for p in found:
        print(f"FAIL: {path}: {p}", file=sys.stderr)
    if not found:
        print(f"ok: {path} has no inline script, style or event handler")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
