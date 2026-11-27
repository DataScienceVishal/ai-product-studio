"""The backend serves the built frontend from one origin (T-16)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.spa import CLIENT_ROUTES, HTML_CSP

INDEX = ('<!doctype html><html><head><script type="module" crossorigin src="/assets/index-abc123.js"></script>'
         '<link rel="stylesheet" href="/assets/index-abc123.css"></head><body><div id="root"></div></body></html>')


@pytest.fixture
def dist(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(INDEX)
    (root / "assets" / "index-abc123.js").write_text("console.log(1)")
    (root / "assets" / "index-abc123.css").write_text("body{}")
    (tmp_path / "secret.txt").write_text("top secret")  # outside dist, must never be served
    (root / "secret-in-root.txt").write_text("not an asset")
    return root


@pytest.fixture
def web(settings, dist):
    settings.frontend_dist = str(dist)
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.mark.parametrize("path", sorted(CLIENT_ROUTES) + ["/verify-email?token=abc", "/verify-email/"])
def test_client_routes_fall_back_to_index(web, path):
    r = web.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text == INDEX
    assert r.headers["cache-control"] == "no-cache"


def test_head_falls_back_without_a_body(web):
    r = web.head("/verify-email")
    assert r.status_code == 200 and r.content == b"" and r.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/some/deep/client/route", "/favicon.ico", "/robots.txt", "/API/vehicle", "/nope"])
def test_unknown_paths_are_404_with_the_app_html(web, path):
    r = web.get(path)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html") and r.text == INDEX
    assert r.headers["cache-control"] == "no-cache"
    assert web.head(path).status_code == 404


@pytest.mark.parametrize("path", ["/", "/verify-email", "/some/unknown", "/billing/done"])
def test_head_matches_get_headers_without_a_body(web, path):
    g, h = web.get(path), web.head(path)
    assert h.status_code == g.status_code and h.content == b""
    assert h.headers["content-length"] == str(len(INDEX.encode())) == g.headers["content-length"]
    for name in ("content-type", "cache-control", "content-security-policy"):
        assert h.headers[name] == g.headers[name]


@pytest.mark.parametrize("path", ["/assets", "/assets/", "/assets/missing.js"])
@pytest.mark.parametrize("method", ["get", "head"])
def test_assets_without_a_file_is_404_not_a_redirect(web, path, method):
    r = getattr(web, method)(path, follow_redirects=False)
    assert r.status_code == 404
    assert "location" not in r.headers


def test_assets_are_immutable(web):
    r = web.get("/assets/index-abc123.js")
    assert r.status_code == 200 and r.text == "console.log(1)"
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert web.get("/assets/index-abc123.css").headers["cache-control"] == "public, max-age=31536000, immutable"


def test_missing_asset_is_a_404_not_the_app(web):
    r = web.get("/assets/index-zzz.js")
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    assert "immutable" not in r.headers["cache-control"]


def test_html_has_a_csp_without_inline_script(web):
    r = web.get("/login")
    csp = r.headers["content-security-policy"]
    assert csp == HTML_CSP
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "<script>" not in r.text and "onclick" not in r.text  # the page itself has no inline script
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"


def _built_html_checker():
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "scripts" / "check_built_html.py"
    spec = importlib.util.spec_from_file_location("check_built_html", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("html", [
    '<!doctype html><html><head><script type="module" crossorigin src="/assets/index-abc.js"></script>'
    '<link rel="stylesheet" crossorigin href="/assets/index-abc.css"></head><body><div id="root"></div></body></html>',
    '<script src="/a.js" ></script><SCRIPT SRC="/b.js"></SCRIPT>',
    # text inside attribute values is not an attribute (T-98)
    '<meta name="description" content="loads once = fast, style = plain"><title>a onclick=b</title>',
    '<script type="application/ld+json">{"@type": "Organization"}</script>',
    '<a href="/javascript:notes">x</a>',
])
def test_built_html_checker_passes_a_clean_vite_page(html):
    assert _built_html_checker().problems(html) == []


@pytest.mark.parametrize("html", [
    "<script>alert(1)</script>",
    '<script type="module">import "/x.js"</script>',
    "<SCRIPT>x()</SCRIPT>",
    '<script data-src="/x.js">x()</script>',
    "<style>body{}</style>",
    '<div style="color:red"></div>',
    "<DIV STYLE='x'></DIV>",
    '<button onclick="x()">',
    '<body onload="x()">',
    '<script type="importmap">{"imports": {}}</script>',
    '<a href="javascript:alert(1)">x</a>',
    '<a HREF=" JavaScript:alert(1)">x</a>',
    '<a href="java\tscript:alert(1)">x</a>',
    '<img src="x" ONERROR="x()" />',
    '<form action="javascript:x()"></form>',
    '<script type="module" type="application/json">x()</script>',  # the first duplicate attribute wins
    '<a href="\x01javascript:x()">x</a>',
])
def test_built_html_checker_catches_csp_blocked_markup(html):
    assert _built_html_checker().problems(html)


def test_the_real_vite_build_has_no_inline_script():
    # CI's frontend job runs scripts/check_built_html.py right after `npm run build` (T-97), so this local
    # check skipping in the backend job no longer leaves the build unchecked. REQUIRE_FRONTEND_BUILD=1 makes a
    # missing build a failure instead of a skip.
    import os
    built = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "index.html"
    if not built.exists():
        if os.environ.get("REQUIRE_FRONTEND_BUILD") == "1":
            pytest.fail(f"{built} missing: run npm run build first")
        pytest.skip("frontend not built (CI checks the build in the frontend job)")
    assert _built_html_checker().problems(built.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", ["/api/nope", "/api/", "/api", "/api/vehicle/x/y/z"])
def test_unknown_api_paths_stay_json_404(web, path):
    r = web.get(path)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["error"] == "not_found"
    assert r.headers["cache-control"] == "no-store"


def test_unknown_api_post_is_still_404_and_wrong_method_still_405(web):
    r = web.post("/api/nope", headers={"x-requested-with": "t"})
    assert r.status_code == 404 and r.json()["error"] == "not_found"
    assert web.post("/healthz").status_code == 405
    assert web.post("/login", headers={"x-requested-with": "t"}).status_code == 404  # only GET gets the app


def test_probes_and_api_unchanged(web):
    live = web.get("/livez")
    assert live.status_code == 200 and live.json()["status"] == "ok" and live.headers["cache-control"] == "no-store"
    health = web.get("/healthz")
    assert health.status_code == 200 and health.json()["db"] == "ok"
    assert "content-security-policy" not in health.headers or health.headers["content-security-policy"] != HTML_CSP
    assert web.get("/api/vehicle").status_code == 401


@pytest.mark.parametrize("path", [
    "/assets/../secret-in-root.txt", "/assets/%2e%2e/secret-in-root.txt", "/assets/..%2fsecret-in-root.txt",
    "/assets/%2e%2e%2f%2e%2e%2fsecret.txt", "/assets/....//secret.txt", "/assets//etc/passwd",
    "/assets/..%5csecret-in-root.txt", "/%2e%2e/secret.txt", "/secret-in-root.txt", "/../secret.txt",
])
def test_no_path_traversal(web, path):
    r = web.get(path)
    assert "top secret" not in r.text and "not an asset" not in r.text and "root:" not in r.text
    assert r.status_code in (200, 400, 404)
    if r.status_code == 200:  # the only 200 allowed is the app's own HTML
        assert r.text == INDEX


def test_api_only_when_there_is_no_build(settings, tmp_path):
    for value in ("", str(tmp_path / "missing"), str(tmp_path)):
        settings.frontend_dist = value
        with TestClient(create_app(settings)) as client:
            r = client.get("/login")
            assert r.status_code == 404 and r.json()["error"] == "not_found"
            assert client.get("/livez").status_code == 200


def _own_header_routes(app):
    from fastapi.responses import JSONResponse
    own = {"Cache-Control": "public, max-age=999", "Content-Security-Policy": "default-src *"}
    app.add_api_route("/api/_own", lambda: JSONResponse({"ok": 1}, headers=own), methods=["GET"])
    app.add_api_route("/hook/_own", lambda: JSONResponse({"ok": 1}, headers=own), methods=["GET"])


def test_api_and_other_routes_cannot_keep_their_own_cache_or_csp(settings, dist):
    """M7: only the SPA module's own responses keep Cache-Control/CSP; /api and any other route get the defaults."""
    settings.frontend_dist = str(dist)
    settings.env = "prod"
    app = create_app(settings)
    _own_header_routes(app)
    with TestClient(app) as client:
        for path in ("/api/_own", "/hook/_own"):
            r = client.get(path)
            assert r.status_code == 200
            assert r.headers["cache-control"] == "no-store", path
            assert r.headers["content-security-policy"] != "default-src *", path
        assert client.get("/login").headers["content-security-policy"] == HTML_CSP
        assert "immutable" in client.get("/assets/index-abc123.js").headers["cache-control"]


def test_assets_do_not_follow_symlinks(web, dist, tmp_path):
    """M8: a symlink inside assets/ must not expose a file (or directory) outside it."""
    (dist / "assets" / "leak.txt").symlink_to(tmp_path / "secret.txt")
    (dist / "assets" / "leakdir").symlink_to(tmp_path, target_is_directory=True)
    for path in ("/assets/leak.txt", "/assets/leakdir/secret.txt"):
        r = web.get(path)
        assert r.status_code == 404 and "top secret" not in r.text, path


# A compared value must end the operand: `path === "/a" + "/sub"` or `ROUTES.a.toLowerCase()` is not the route "/a".
_END = r"""(?=\s*(?:\)|&&|\|\||\?\?|\?|;|:|,|\}|$))"""
_ROUTE = re.compile(r"""\bpath\s*===\s*(["'`])(/[^"'`$]*)\1""" + _END, re.MULTILINE)
# "/x" === path (literal first)
_ROUTE_REVERSED = re.compile(r"""(?<![\w$.)\]+])(["'`])(/[^"'`$]*)\1\s*===\s*path\b(?!\s*[.\[(])""")
# path === ROUTES.x / ROUTES["x"], either order: a member of a constant object literal in the same source
_MEMBER = r"""([A-Za-z_$][\w$]*)\s*(?:\.\s*([A-Za-z_$][\w$]*)|\[\s*(["'`])([^"'`$]+)\3\s*\])"""
_ROUTE_MEMBER = re.compile(rf"""\bpath\s*===\s*{_MEMBER}{_END}|(?<![\w$.)\]+]){_MEMBER}\s*===\s*path\b(?!\s*[.\[(])""", re.MULTILINE)
# PAGES[path]: object-lookup routing; the keys of the object literal are the routes
_LOOKUP = re.compile(r"""(?<![\w$.])([A-Za-z_$][\w$]*)\s*\[\s*path\s*\]""")
_OBJECT_START = re.compile(r"""\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::(?:[^=;]|=>)+)?=\s*\{""")
_ROUTE_KEY_ENTRY = re.compile(r"""^\s*(["'`])(/[^"'`$]*)\1\s*:""")
_ANY_ROUTE_KEY = re.compile(r"""(["'`])/[^"'`$]*\1\s*:""")
_STR_ENTRY = re.compile(r"""^\s*(?:([A-Za-z_$][\w$]*)|(["'`])([^"'`$]+)\2)\s*:\s*(["'`])([^"'`$]*)\4\s*$""")
# Other ways to compare the path would hide a route from the sync test: path.startsWith(..), path !== .., /re/.test(path),
# SET.has(path), or a non-literal the scanner could not resolve to a string above...
# `PUBLIC.has(path)` (exactly that name) is the app's sign-in check, not routing, so it is the one allowed membership test.
_PUBLIC_CHECK = re.compile(r"""(?<![\w$.])PUBLIC\s*\.\s*has\s*\(\s*path\s*\)""")
_OTHER = re.compile(
    r"""\bpath\s*(?:!==?|==(?!=))|\bpath\s*\.\s*\w+\s*\(|\bswitch\s*\(\s*path\s*\)"""
    r"""|\.\s*(?:test|includes|has|indexOf|get)\s*\(\s*path\s*\)|\bpath\s+in\b"""
    r"""|\bpath\s*===\s*[A-Za-z_$"'`]|[A-Za-z_$][\w$.]*\s*\[\s*path\s*\]|(?:!==?|(?<![=!])==(?!=))\s*path\b"""
    r"""|[A-Za-z_$)\]"'`][\w$.]*\s*===\s*path\b""")


def _strip_comments(src: str) -> tuple[str, list[str]]:
    """Remove // and /* */ comments (not inside strings; '" strings end at a newline, so JSX text apostrophes can't run on).

    Also returns what it is unsure about, which the scanner reports as unreadable: an unterminated /* (the rest of the file
    would vanish), and a comment marker that is not first on its line (`http://x` or `a // b` in JSX text, a regex
    like /a\\//) when the text it removes contains `path`, since that may be code, not a comment."""
    out, problems, i, quote = [], [], 0, ""
    while i < len(src):
        c, two = src[i], src[i:i + 2]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < len(src):
                out.append(src[i + 1])
                i += 1
            elif c == quote or (c == "\n" and quote != "`"):
                quote = ""
        elif two in ("//", "/*"):
            if two == "//":
                end = src.find("\n", i)
                end = len(src) if end < 0 else end
            else:
                close = src.find("*/", i + 2)
                if close < 0:
                    problems.append("unterminated /*")
                    end = len(src)
                else:
                    end = close + 2
            removed = src[i:end]
            if src[src.rfind("\n", 0, i) + 1:i].strip() and re.search(r"\bpath\b", removed):
                problems.append(f"comment marker inside code: {removed[:30]!r}")
            if two == "/*":
                out.append(" ")
            i = end
            continue
        else:
            out.append(c)
            if c in "\"'`":
                quote = c
        i += 1
    return "".join(out), problems


def _split_top_level(text: str) -> tuple[list[str], bool]:
    """Split on commas that are not inside brackets, braces, parentheses or strings.

    The flag is True if a ' or " string was closed by a newline instead of its own quote: that is always a misread
    (an apostrophe in JSX text), and it may have hidden a comma, so the entries cannot be trusted. It is also True if
    a second count, with quotes ignored altogether, finds a different number of entries: two apostrophes on one line
    can pair up as a "string" and swallow a non-route entry without ever hitting a newline."""
    parts, depth, quote, start, i, misread = [], 0, "", 0, 0, False
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = ""
            elif c == "\n" and quote != "`":
                quote, misread = "", True
        elif c in "\"'`":
            quote = c
        elif c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
        i += 1
    parts.append(text[start:])
    entries = [p for p in parts if p.strip()]
    return entries, misread or _count_ignoring_quotes(text) != len(entries)


def _count_ignoring_quotes(text: str) -> int:
    """Top-level entries counting only brackets and commas. Differs from the quote-aware count when a quote pairs up wrong."""
    depth, commas, last_comma, i = 0, 0, -1, 0
    for i, c in enumerate(text):
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == "," and depth == 0:
            if text[last_comma + 1:i].strip():
                commas += 1
            last_comma = i
    return commas + (1 if text[last_comma + 1:].strip() else 0)


def _object_literals(src: str) -> dict[str, tuple[list[str], str, bool]]:
    """name -> top-level entries of its `const NAME = { ... }` literal. A name declared twice, or assigned to anywhere
    (`NAME[k] = v`, `NAME.k = v`, `NAME = ..`, Object.assign), is left out: its routes can't be known from one literal."""
    out: dict[str, tuple[list[str], str, bool]] = {}
    declarations = _OBJECT_START.sub(" ", src)  # the literal's own `NAME = {` is not an assignment
    for m in _OBJECT_START.finditer(src):
        name = m.group(1)
        depth, i, quote = 1, m.end(), ""
        while i < len(src) and depth:
            c = src[i]
            if quote:
                if c == "\\":
                    i += 1
                elif c == quote or (c == "\n" and quote != "`"):
                    quote = ""
            elif c in "\"'`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        if depth:
            continue
        n = re.escape(name)
        twice = len(re.findall(rf"\b(?:const|let|var)\s+{n}\b", src)) > 1
        assigned = re.search(rf"(?<![\w$.]){n}\s*(?:\.\s*[\w$]+|\[[^\]]*\])*\s*(?:\*\*|\?\?|\|\||&&|<<|>>>?|[-+*/%&|^])?=(?![=>])", declarations) \
            or re.search(rf"Object\s*\.\s*assign\s*\(\s*{n}\b", src)
        if not twice and not assigned:
            body = src[m.end():i - 1]
            entries, misread = _split_top_level(body)
            out[name] = (entries, body, misread)
    return out


def scan_routes(src: str) -> tuple[set[str], list[str]]:
    """Literal routes the source compares `path` with, and the comparisons the scanner cannot read.

    Reads `path === "/x"`, `"/x" === path`, `path === ROUTES.x` (or `ROUTES["x"]`, either order) and `PAGES[path]`, resolving
    ROUTES and PAGES from a single, never-reassigned `const NAME = { ... }` literal in the same source. A PAGES literal is read
    only if EVERY top-level entry is a quoted "/route": key (no spread, computed key, method or bare key). Whatever it cannot
    resolve is returned as unreadable."""
    src, problems = _strip_comments(src)
    objects = _object_literals(src)
    found: set[str] = set()

    def literal(m: re.Match) -> str:
        if m.string[:m.start()].rstrip()[-1:] in ("+", "-", "*", "/", "%", "."):  # `"/a" + "/sub" === path`: not the literal alone
            return m.group(0)
        found.add(m.group(2))
        return " "

    def member(m: re.Match) -> str:
        left = m.group(1) is not None  # `path === NAME.key` fills groups 1-4, `NAME.key === path` groups 5-8
        name, key = (m.group(1), m.group(2) or m.group(4)) if left else (m.group(5), m.group(6) or m.group(8))
        values = {}
        for entry in objects.get(name, ([], "", False))[0]:
            e = _STR_ENTRY.match(entry)
            if e:
                values[e.group(1) or e.group(3)] = e.group(5)
        if values.get(key, "").startswith("/"):
            found.add(values[key])
            return " "  # resolved: hide it from the unreadable check
        return m.group(0)

    def lookup(m: re.Match) -> str:
        entries, body, misread = objects.get(m.group(1), ([], "", False))
        keys = [_ROUTE_KEY_ENTRY.match(e) for e in entries]
        # every `"/route":` in the object's whole text must be a top-level entry, or entries were merged by a misread string
        if keys and all(keys) and not misread and len(_ANY_ROUTE_KEY.findall(body)) == len(entries):
            found.update(k.group(2) for k in keys)
            return " "
        return m.group(0)

    rest = _ROUTE.sub(literal, src)
    rest = _ROUTE_REVERSED.sub(literal, rest)
    rest = _ROUTE_MEMBER.sub(member, rest)
    rest = _LOOKUP.sub(lookup, rest)
    rest = _PUBLIC_CHECK.sub(" ", rest)
    return found, problems + [m.group(0) for m in _OTHER.finditer(rest)]


def test_route_scanner_accepts_any_quote_style_and_flags_other_comparisons():
    assert scan_routes("path === \"/a\" || path === '/b' || path === `/c`") == ({"/a", "/b", "/c"}, [])
    for bad in ("path.startsWith('/x')", "path !== '/x'", "path == '/x'", "switch (path) {", "/x/.test(path)", "ROUTES.includes(path)",
                "ROUTES_SET.has(path)", "LIST.indexOf(path)"):
        assert _OTHER.search(bad), bad
    assert scan_routes('PUBLIC.has(path) && path === "/x"') == ({"/x"}, [])  # the sign-in check is not routing


def test_route_scanner_reads_or_flags_the_other_ways_to_write_a_route():
    assert scan_routes("""if ("/x" === path) a(); if ('/y' === path || path === "/z") b();""") == ({"/x", "/y", "/z"}, [])
    assert scan_routes("if (path === '/a') a();") == ({"/a"}, [])
    for unreadable in ("if (path === ROUTES.billing) a();", "if (ROUTES.billing === path) a();", "return PAGES[path];",
                       "const P = pages.main[path];", "if (x === path) a();", "if (x !== path) a();",
                       "if (\"/x\" !== path) a();", "if (\"/x\" == path) a();", "if (x != path) a();"):
        found, other = scan_routes(unreadable)
        assert other and not found, unreadable  # no ROUTES/PAGES literal in the source: flagged, never silently ignored


def test_route_scanner_resolves_a_literal_on_the_left():
    assert scan_routes("""if ("/x" === path) return <X />;""") == ({"/x"}, [])
    assert scan_routes("""if (`/y` === path || '/z' === path) return null;""") == ({"/y", "/z"}, [])
    assert scan_routes("""if ("/x" !== path) return null;""")[1]  # a different operator is still unreadable


@pytest.mark.parametrize("expr", [
    'path === "/a" + "/sub"', 'path === "/a".toLowerCase()', '"/a" + "/sub" === path', 'path === ROUTES.a + "/sub"',
    "path === ROUTES.a.toLowerCase()", 'ROUTES.a.toLowerCase() === path', 'path === ROUTES["a"] + x',
])
def test_route_scanner_does_not_resolve_a_value_that_is_more_than_the_literal(expr):
    found, other = scan_routes(f'const ROUTES = {{ a: "/a" }};\nif ({expr}) go();')
    assert other and not found, expr


def test_route_scanner_resolves_constant_object_members():
    src = """
    const ROUTES = { billing: "/billing", "team-page": '/team', settings: `/settings`, label: "not a route" } as const;
    if (path === ROUTES.billing) a();
    if (ROUTES.settings === path) b();
    if (path === ROUTES["team-page"]) c();
    """
    assert scan_routes(src) == ({"/billing", "/settings", "/team"}, [])
    # a member the object lacks, an unknown object and a non-route value stay unreadable
    for bad in ("if (path === ROUTES.nope) a();", "if (path === OTHER.billing) a();", "if (path === ROUTES.label) a();"):
        found, other = scan_routes(src + bad)
        assert other and found == {"/billing", "/settings", "/team"}, bad
    found, other = scan_routes("const ROUTES = { a: base + '/a' };\nif (path === ROUTES.a) x();")  # computed: not a literal
    assert other and not found
    found, other = scan_routes('const ROUTES = { x: { a: "/a" } };\nif (path === ROUTES.a) x();')  # nested, not top-level
    assert other and not found
    found, other = scan_routes('const ROUTES = { a: "/a" };\nROUTES.a = "/b";\nif (path === ROUTES.a) x();')  # reassigned
    assert other and not found


def test_route_scanner_resolves_object_lookup_routing():
    src = """
    const PAGES: Record<string, () => JSX.Element> = {
      "/billing": () => <Billing me={me} />,
      '/team': () => <Team />,
      "/a/b": Nested,
    };
    return PAGES[path]?.() ?? <NotFound />;
    """
    assert scan_routes(src) == ({"/billing", "/team", "/a/b"}, [])
    found, other = scan_routes("const PAGES = { home: A };\nreturn PAGES[path];")  # keys are not routes
    assert other and not found
    found, other = scan_routes("return PAGES[path];")  # no literal to resolve
    assert other and not found
    found, other = scan_routes('const PAGES = { "/a": { "/b": B } };\nreturn PAGES[path];')  # a nested route-keyed object: unsure
    assert other and not found


@pytest.mark.parametrize("literal", [
    'const PAGES = { "/a": A, /* more */ [ROUTES.b]: B };',                 # computed key
    'const PAGES = { "/a": A, [`/${x}`]: B };',                             # computed template key
    'const PAGES = { ...MORE, "/a": A };',                                  # spread
    'const PAGES = { "/a": A, "/b"() { return B; } };',                     # method shorthand
    'const PAGES = { "/a": A, b };',                                        # shorthand property
    'const PAGES = { "/a": A, home: B };',                                  # bare key
    'const PAGES = { "/a": A };\nPAGES["/b"] = B;',                         # added later
    'const PAGES = { "/a": A };\nPAGES.x = B;',
    'const PAGES = { "/a": A };\nObject.assign(PAGES, MORE);',
    'const PAGES = { "/a": A };\nfunction f() { const PAGES = { "/b": B }; }',  # declared twice
    'let PAGES = { "/a": A };\nPAGES = { "/b": B };',                       # reassigned
    'const PAGES = {};',                                                    # nothing to read
])
def test_route_scanner_flags_an_object_lookup_it_cannot_read_completely(literal):
    _found, other = scan_routes(literal + "\nreturn PAGES[path];")
    assert other, literal  # unreadable, so the sync test fails instead of passing with a route missing


@pytest.mark.parametrize("literal", [
    'const PAGES = {\n "/a": A, // home\n "/b": B };',      # comment after an entry
    'const PAGES = { // pages\n "/a": A,\n "/b": B };',     # comment before the first entry
    'const PAGES = { "/a": A, /* x, y */ "/b": B, // end\n};',
])
def test_route_scanner_reads_a_lookup_object_with_comments(literal):
    assert scan_routes(literal + "\nreturn PAGES[path];") == ({"/a", "/b"}, [])


@pytest.mark.parametrize("source", [
    'const PAGES = {\n "/a": () => <p>Don\'t</p>,\n "/b": () => <p>It\'s</p>,\n "/c": C };\nreturn PAGES[path];',
    'if (x) return <p>see http://x</p>; if (path === "/b") go();',
    'if (/a\\//.test(x) || path === "/b") go();',
    'const p = s.replace(/\\/*$/, "");\nif (path === "/b") go();',
])
def test_route_scanner_flags_quote_and_comment_lookalikes_instead_of_dropping_routes(source):
    _found, other = scan_routes(source)
    assert other, source


def test_route_scanner_jsx_apostrophe_on_an_entry_line_is_flagged_not_misread():
    """The apostrophe hides that line's comma from the splitter; the route-key count notices and the lookup is unreadable."""
    src = 'const PAGES = {\n "/a": () => <p>Don\'t</p>,\n "/b": () => <p>Fine</p> };\nreturn PAGES[path];'
    found, other = scan_routes(src)
    assert other and not found


@pytest.mark.parametrize("name", ["MY_PUBLIC", "NOTPUBLIC", "x.PUBLIC", "PUBLIC2"])
def test_route_scanner_only_the_exact_public_set_is_allowed_to_test_the_path(name):
    assert scan_routes(f"if ({name}.has(path)) go();")[1], name
    assert scan_routes("if (PUBLIC.has(path)) go();") == (set(), [])


@pytest.mark.parametrize("expr", ["PAGES.get(path)", "path in PAGES", "ROUTES.indexOf(path)"])
def test_route_scanner_flags_map_and_in_routing(expr):
    assert scan_routes(f"if ({expr}) go();")[1], expr


@pytest.mark.parametrize("swallowed", [
    "...MORE,",                  # spread
    "[ROUTES.b]: B,",            # computed key
    "home: H,",                  # bare key
    "...MORE, // more pages",
])
def test_route_scanner_apostrophe_line_hiding_a_non_route_entry_is_flagged(swallowed):
    """An apostrophe in JSX text closes at the newline (a misread) and hides that line's comma, so the next entry merges
    into it. The route-key count cannot see a non-route entry, so the misread itself makes the lookup unreadable."""
    src = f'const PAGES = {{\n "/a": () => <p>Don\'t</p>,\n {swallowed}\n "/c": C }};\nreturn PAGES[path];'
    found, other = scan_routes(src)
    assert other and not found, src


def test_route_scanner_flags_a_mid_line_double_slash_in_jsx_text():
    assert scan_routes('return <p>a // b</p>; if (path === "/b") go();')[1]
    assert scan_routes('if (path === "/b") go(); // path === "/old" is gone') [1]  # removed text mentions path: unsure


# Known limitation: an alias (`const R = ROUTES; R.a = "/z"`) is not tracked, so ROUTES.a still resolves to its literal.


def test_route_scanner_comments_do_not_hide_or_invent_routes():
    src = '''
    // if (path === "/old") go();
    /* if (path === "/older") go(); */
    const URL = "https://example.test/x"; // a // inside a string is not a comment
    if (path === "/live") go(); // trailing
    '''
    assert scan_routes(src) == ({"/live"}, [])


_GUARD_LINES = {
    "/zero": 'if (path === "/zero") return <Zero />;',
    "/left": 'if ("/left" === path) return <Left />;',
    "/one": "if (path === ROUTES.one) return <One />;",
    "/two": "return PAGES[path];",
}
_GUARD_SRC = 'const ROUTES = { one: "/one" };\nconst PAGES = { "/two": Two };\n'


def test_route_scanner_regression_guard_on_a_synthetic_app():
    """If the scanner stops seeing any one form, this fails."""
    found, other = scan_routes(_GUARD_SRC + "\n".join(_GUARD_LINES.values()))
    assert other == [] and found == set(_GUARD_LINES)


@pytest.mark.parametrize("route", sorted(_GUARD_LINES))
def test_route_scanner_each_form_contributes_exactly_its_own_route(route):
    lines = [line for r, line in _GUARD_LINES.items() if r != route]
    found, other = scan_routes(_GUARD_SRC + "\n".join(lines))
    assert other == [] and found == set(_GUARD_LINES) - {route}


def test_client_routes_match_the_frontend_router():
    """A new page in App.tsx must be added to CLIENT_ROUTES (or a refresh on it would 404)."""
    from app.spa import CLIENT_ROUTES
    app_tsx = Path(__file__).resolve().parents[2] / "frontend" / "src" / "App.tsx"
    src = app_tsx.read_text()  # missing file: fail, not skip
    found, other = scan_routes(src)
    found |= {"/"}
    assert not other, (f"App.tsx compares the path in a way this test cannot read ({other}). Use path === '/route', or look for "
                       "the usual causes of a misread: an apostrophe in JSX text inside a PAGES object (write &apos; or move "
                       "the text out), a // or /* comment marker mid-line in code or JSX text, or a ROUTES/PAGES object that "
                       "is spread, computed, assigned to later or declared twice.")
    assert found == set(CLIENT_ROUTES)


@pytest.mark.parametrize("path", ["/assets", "/assets/", "/assets/missing.js"])
@pytest.mark.parametrize("method", ["get", "head"])
def test_assets_without_an_assets_folder_is_404_not_a_redirect(settings, tmp_path, path, method):
    bare = tmp_path / "bare-dist"
    bare.mkdir()
    (bare / "index.html").write_text(INDEX)
    settings.frontend_dist = str(bare)
    with TestClient(create_app(settings)) as client:
        r = getattr(client, method)(path, follow_redirects=False)
    assert r.status_code == 404 and "location" not in r.headers


def test_one_line_pages_object_with_paired_apostrophes_is_unreadable():
    """F1: two apostrophes on one line pair up as a string and hide a spread between them. Must not pass silently."""
    src = '''const PAGES = { "/a": () => <p>Don't</p>, ...MORE, [X]: () => <p>It's</p>, "/c": C };
    return PAGES[path];'''
    found, other = scan_routes(src)
    assert other and not found, (
        "PAGES was read as complete, or its routes were found. It should be unreadable here. If this fails on a different "
        "source, a possible cause is a comma inside a quoted string in a PAGES entry (e.g. title=\"Hi, there\"), which "
        "the quote-ignoring comma count also reports as unreadable.")
    # the same object without the apostrophes is read normally
    ok = 'const PAGES = { "/a": A, "/c": C };\nreturn PAGES[path];'
    assert scan_routes(ok) == ({"/a", "/c"}, [])
