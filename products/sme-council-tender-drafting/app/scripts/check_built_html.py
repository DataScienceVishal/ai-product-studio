"""Check the built frontend's index.html for anything the production CSP would block.

The app serves HTML with `script-src 'self'` and `style-src 'self'` (no 'unsafe-inline'), so an inline
<script> or <style> block, a style= attribute, an on...= handler or a javascript: URL would be silently blocked in the browser. Stdlib only, so
CI's frontend job can run it right after `npm run build` without the backend's dependencies:

    python3 ../scripts/check_built_html.py dist/index.html

backend/tests/test_spa.py imports `problems` so the rules are unit-tested in every backend run too.
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

# Script types that are data blocks, never run, so script-src does not block them inline. (An inline importmap IS
# checked against script-src, so it is not listed.)
_DATA_SCRIPT_TYPES = {"application/ld+json", "application/json"}
_URL_ATTRS = {"href", "src", "action", "formaction", "xlink:href"}


class _Scanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[str] = []

    def _add(self, msg: str) -> None:
        if msg not in self.found:
            self.found.append(msg)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = {name for name, _ in attrs}
        values: dict[str, str | None] = {}
        for name, value in attrs:
            values.setdefault(name, value)  # browsers use the first of duplicate attributes
        if tag == "script" and "src" not in names:
            if (values.get("type") or "").strip().lower() not in _DATA_SCRIPT_TYPES:
                self._add("inline <script> (no src) would be blocked by script-src 'self'")
        if tag == "style":
            self._add("<style> block would be blocked by style-src 'self'")
        if "style" in names:
            self._add("style= attribute would be blocked by style-src 'self'")
        if any(name.startswith("on") for name in names):
            self._add("inline event handler (on...=) would be blocked by script-src 'self'")
        for name, value in attrs:
            # Browsers strip leading C0 controls/spaces and drop tabs and newlines anywhere in a URL.
            cleaned = "".join(ch for ch in (value or "") if ord(ch) > 0x20 and ch != "\x7f").lower()
            if name in _URL_ATTRS and cleaned.startswith("javascript:"):
                self._add("javascript: URL would be blocked by script-src 'self'")

    handle_startendtag = handle_starttag


def problems(html: str) -> list[str]:
    """Return one message per CSP-blocked construct found; empty means the page is clean.

    Uses the stdlib HTML parser, so text inside attribute values (a meta description saying "once = fast")
    is never mistaken for an attribute.
    """
    scanner = _Scanner()
    scanner.feed(html)
    scanner.close()
    return scanner.found


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
        print(f"ok: {path} has no inline script, style, event handler or javascript: URL")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
