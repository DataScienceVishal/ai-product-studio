"""One error shape for the whole API: {"error": code, "message": friendly text, "request_id": id}."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logs import request_id_var


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers


def body(code: str, message: str) -> dict:
    return {"error": code, "message": message, "request_id": request_id_var.get()}


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(body(exc.code, exc.message), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and (spa := getattr(request.app.state, "spa_fallback", None)):
            page = spa(request)  # client-side routes (/verify-email, ...) get the app's HTML
            if page is not None:
                return page
        code = {401: "not_signed_in", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}.get(
            exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(body(code, message), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = [{"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "problem": e.get("msg", "")}
                  for e in exc.errors()]
        payload = body("invalid_input", "Some fields need fixing.") | {"fields": fields}
        return JSONResponse(payload, status_code=422)
