"""FastAPI middleware for request timing, CORS, and safe error responses."""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.utils.config import get_logger

logger = get_logger(__name__)


def configure_middleware(
    app: FastAPI,
    allowed_origins: list[str] | None = None,
) -> None:
    """Attach CORS, structured request logging/timing, and safe 500 error handling."""
    origins = (
        allowed_origins
        if allowed_origins is not None
        else [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8501",
        ]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Process-Time-Ms"],
    )

    @app.middleware("http")
    async def request_timing_middleware(request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        logger.info(
            "%s %s -> %d (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error processing %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error while processing prediction request."},
        )
