"""The backend serves the built frontend from one origin (T-16)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.spa import HTML_CSP

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


@pytest.mark.parametrize("path", ["/", "/login", "/verify-email?token=abc", "/reset-password", "/accept-invite",
                                  "/billing/done", "/billing/mock-checkout", "/settings", "/team", "/verify-email/"])
def test_client_routes_fall_back_to_index(web, path):
    r = web.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text == INDEX
    assert r.headers["cache-control"] == "no-cache"


def test_head_falls_back_without_a_body(web):
    r = web.head("/verify-email")
    assert r.status_code == 200 and r.content == b"" and r.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/some/deep/client/route", "/favicon.ico", "/robots.txt", "/API/notes", "/nope"])
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


def test_the_real_vite_build_has_no_inline_script():
    import pathlib
    import re
    built = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist" / "index.html"
    if not built.exists():
        pytest.skip("frontend not built")
    html = built.read_text()
    assert not re.search(r"<script(?![^>]*\ssrc=)", html), "inline script would be blocked by the CSP"
    assert "<style" not in html and not re.search(r"\sstyle=", html)


@pytest.mark.parametrize("path", ["/api/nope", "/api/", "/api", "/api/notes/x/y/z"])
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
    assert web.get("/api/notes").status_code == 401


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
