"""Probes: /livez for liveness (no DB), /healthz for readiness and the Docker HEALTHCHECK (checks the DB)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .. import __version__

log = logging.getLogger("app.health")
router = APIRouter(tags=["health"])


@router.get("/livez")
def livez():
    """Liveness: the process is up. No database, so a busy pool never gets the replica restarted."""
    return {"status": "ok", "version": __version__}


@router.get("/healthz")
def healthz(request: Request):
    try:
        with request.app.state.db.engine.connect() as conn:
            conn.execute(text("select 1"))
        db_state = "ok"
    except SQLAlchemyError:
        log.exception("health check: database unreachable")
        db_state = "down"
    status = 200 if db_state == "ok" else 503
    return JSONResponse({"status": "ok" if status == 200 else "degraded", "db": db_state, "version": __version__},
                        status_code=status)
