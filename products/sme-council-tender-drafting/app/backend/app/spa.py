"""Serves the built React app from the same origin as /api (ADR 0002, decision 2).

Enabled only when FRONTEND_DIST names a folder holding index.html; otherwise the app is API-only (dev,
tests, the e2e script, where Vite serves the frontend and proxies /api).

- /assets/* is Vite's hashed output: cacheable for a year. StaticFiles refuses paths outside the folder.
- A GET or HEAD that matches no route and is one of the client routes (CLIENT_ROUTES, mirroring the router in
  frontend/src/App.tsx) falls back to index.html with no-cache and the HTML CSP. Any other unknown path gets
  the same HTML with status 404, so crawlers and monitors see a real 404 (the app shows its "Page not found" view
  for them). It is done from the 404 handler so a wrong method on a real route still answers 405 and unknown /api
  paths still answer the JSON 404. HEAD carries the same headers as GET (including Content-Length), no body.
- /assets and /assets/ with no file answer 404 directly (no redirect).
- The fallback never opens a file named by the request, so there is no path to traverse.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

log = logging.getLogger("app.spa")

# SECURITY.md I4 / ADR 0002. No inline script or style: the Vite build emits only <script src> and <link>.
HTML_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
# Keep in step with the path checks in frontend/src/App.tsx. Anything else is a 404 (with the app's HTML).
CLIENT_ROUTES = frozenset({
    "/", "/login", "/signup", "/forgot-password", "/reset-password", "/accept-invite", "/verify-email",
    "/privacy", "/terms", "/help", "/billing", "/billing/done", "/billing/mock-checkout", "/billing/mock-portal", "/settings", "/team",
})
IMMUTABLE = "public, max-age=31536000, immutable"
OWN_HEADERS = "spa.own_headers"  # scope key: set only by responses this module produced; RequestContext honours it


class ImmutableStatic(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = IMMUTABLE
            scope[OWN_HEADERS] = True
        return response


def _is_reserved(path: str) -> bool:
    return path == "/api" or path.startswith("/api/") or path == "/assets" or path.startswith("/assets/")


def install(app: FastAPI, dist: str) -> bool:
    """Mount the built frontend if `dist/index.html` exists. Returns whether it is being served."""
    root = Path(dist) if dist else None
    index = root / "index.html" if root else None
    if not root or not index or not index.is_file():
        if dist:
            log.warning("FRONTEND_DIST has no index.html; serving the API only", extra={"dist": dist})
        return False
    html = index.read_bytes()
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", ImmutableStatic(directory=assets), name="assets")

    async def no_asset(request: Request) -> Response:
        raise StarletteHTTPException(404)  # /assets itself is not a file: 404 here, not a 307 to /assets/

    for asset_path in ("/assets", "/assets/"):  # both spellings: no redirect_slashes 307 when there is no assets/ folder
        app.add_route(asset_path, no_asset, methods=["GET", "HEAD"], include_in_schema=False)

    def fallback(request: Request) -> Response | None:
        if request.method not in ("GET", "HEAD") or _is_reserved(request.url.path):
            return None
        request.scope[OWN_HEADERS] = True
        headers = {"Cache-Control": "no-cache", "Content-Security-Policy": HTML_CSP}
        known = (request.url.path.rstrip("/") or "/") in CLIENT_ROUTES
        page = Response(html, status_code=200 if known else 404, media_type="text/html", headers=headers)
        if request.method == "HEAD":  # same headers as GET, Content-Length of the GET body, no body
            page.body = b""
        return page

    app.state.spa_fallback = fallback
    log.info("serving the built frontend", extra={"dist": str(root)})
    return True
