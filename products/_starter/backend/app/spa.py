"""Serves the built React app from the same origin as /api (ADR 0002, decision 2).

Enabled only when FRONTEND_DIST names a folder holding index.html; otherwise the app is API-only (dev,
tests, the e2e script, where Vite serves the frontend and proxies /api).

- /assets/* is Vite's hashed output: cacheable for a year. StaticFiles refuses paths outside the folder.
- Any other GET or HEAD that matches no route falls back to index.html (client-side routes such as
  /verify-email) with no-cache and the HTML CSP. It is done from the 404 handler so a wrong method on a real
  route still answers 405 and unknown /api paths still answer the JSON 404.
- The fallback never opens a file named by the request, so there is no path to traverse.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

log = logging.getLogger("app.spa")

# SECURITY.md I4 / ADR 0002. No inline script or style: the Vite build emits only <script src> and <link>.
HTML_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
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

    def fallback(request: Request) -> Response | None:
        if request.method not in ("GET", "HEAD") or _is_reserved(request.url.path):
            return None
        request.scope[OWN_HEADERS] = True
        headers = {"Cache-Control": "no-cache", "Content-Security-Policy": HTML_CSP}
        return Response(b"" if request.method == "HEAD" else html, media_type="text/html", headers=headers)

    app.state.spa_fallback = fallback
    log.info("serving the built frontend", extra={"dist": str(root)})
    return True
