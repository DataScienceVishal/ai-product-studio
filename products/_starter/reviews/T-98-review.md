# Review: p/_starter/T-98 (commit 208961a)

Reviewer: reviewer agent, 2026-11-25
Scope: `git diff main...p/_starter/T-98`. Two files: `scripts/check_built_html.py`, `backend/tests/test_spa.py`.

## Summary

The built-HTML CSP checker now uses stdlib `html.parser` in place of regexes. It flags inline scripts (except JSON data blocks), `<style>` blocks, `style=` attributes, `on*` handlers and `javascript:` URLs in href/src/action/formaction/xlink:href. This fixes the T-97 S1 false positive, where text inside attribute values was read as attributes. It is still stdlib-only. `str | None` and `list[...]` annotations are fine because of `from __future__ import annotations`, and they would work at runtime on 3.10+ anyway.

## Evidence

- `pytest tests/test_spa.py`: **135 passed** in 4.08s (venv python, `-o addopts="" -p no:warnings`).
- `python3 scripts/check_built_html.py frontend/dist/index.html` gives `ok`, rc=0 (Python 3.11.18 here; CI uses 3.12).
- Lead's full run: 668 passed, 0 skipped, with REQUIRE_FRONTEND_BUILD=1. Not re-run here because it was not needed for a change to one script.
- Probe script with 26 edge cases. Results below.

| Case | Flagged | Correct? |
|---|---|---|
| Uppercase `<SCRIPT>` / `ONCLICK` (the parser lowercases names) | yes | yes |
| `type=" Application/LD+JSON "` | no | yes (browser strips whitespace and treats it as a data block) |
| `type="application/json; charset=utf-8"` | yes | false positive, but safe (it is a data block in the browser) |
| `type=""`, `speculationrules`, `importmap` | yes | yes |
| `&#106;avascript:`, `javascript&colon;`, `java&Tab;script:` (attribute values are always unescaped) | yes | yes |
| Unquoted `href= javascript:x()` | yes | yes |
| `<svg><script>`, `<svg><a xlink:href="javascript:">` | yes | yes |
| `<template>` contents | yes | yes |
| `<script src=..>"<style>"</script>` (script content is CDATA) | no | yes |
| `<a title="<script>">`, HTML comments | no | yes |
| Unclosed tag at EOF `<div style="x"` | no | yes (browsers drop a tag cut off at EOF) |
| `<script>` with no closing tag | yes | yes |
| `<script type="module" type="application/json">` | **no** | **false negative**: the browser uses the first attribute, `dict(attrs)` keeps the last |
| `<iframe srcdoc="&lt;script&gt;...">` | no | false negative (srcdoc inherits the parent CSP; content is not scanned) |
| `<object data="javascript:">` | no | false negative (`data` is not in `_URL_ATTRS`) |
| `href="\x01javascript:"` (leading C0 control) | no | false negative (URL parsing strips C0 controls; `str.split()` does not) |
| SVG `<animate attributeName="href" to="javascript:">`, meta refresh to `javascript:` | no | false negative (niche; modern browsers block meta-refresh `javascript:`) |

**Importmap claim verified.** In the HTML spec's "prepare the script element" algorithm, a script whose type is not classic, module, importmap or speculationrules returns early as a data block. That happens before the "Should element's inline behavior be blocked by CSP?" check. Inline import maps and speculation rules reach that check, so `script-src 'self'` blocks them. Keeping importmap flagged is correct.

## Critical issues

None. The checker is a build-output tripwire for Vite's `index.html`, not a sanitizer for untrusted HTML. None of the false negatives above can come from a Vite build of this starter, and every case that matters for Vite output is handled correctly.

## Suggestions (non-blocking, could be a follow-up task)

1. **Duplicate `type` (`check_built_html.py`, `handle_starttag`, `values = dict(attrs)`):** browsers honour the first occurrence of an attribute, but `dict` keeps the last. Build `values` from the first occurrence: `for n, v in attrs: values.setdefault(n, v)`. This closes the `type="module" type="application/json"` false negative.
2. **srcdoc:** if an `iframe` has `srcdoc`, recursively run `problems(value)` on it and add the results (the value is already entity-decoded).
3. **URL attribute coverage:** add `data` (object), and consider `formaction` on `input` (already covered by name), `ping`, `poster`. Strip C0 controls as well as whitespace: `"".join(c for c in value if c > " ")`.
4. **Docs and messages:** the module docstring and the `ok:` message in `main` still list only "inline script, style or event handler". Mention `javascript:` URLs.
5. **Tests:** add a pass case for `type=" application/ld+json "` (whitespace and case) and a fail case for entity-encoded `&#106;avascript:`, so the decoding behaviour is pinned.

## Verdict

**PASS**
