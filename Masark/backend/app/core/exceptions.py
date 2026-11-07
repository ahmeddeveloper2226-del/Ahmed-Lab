"""Domain exceptions mapped to clean HTTP responses (never leak internals)."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class MasarkError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(MasarkError):
    status_code = 404


class ConflictError(MasarkError):
    status_code = 409


class ScraperUnavailableError(MasarkError):
    status_code = 502


class AIServiceError(MasarkError):
    status_code = 503


async def masark_error_handler(request: Request, exc: MasarkError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
