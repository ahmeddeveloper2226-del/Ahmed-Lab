from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import ai, auth, lecture_study, lectures, notifications, platforms, study_plan, subjects, users
from app.core.config import get_settings
from app.core.exceptions import MasarkError, masark_error_handler
from app.core.firebase import init_firebase
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.services.scraping.scrapling_pool import shutdown_scrapling

settings = get_settings()
configure_logging(debug=settings.DEBUG)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    if settings.SCHEDULER_ENABLED:
        start_scheduler()
    log.info("app.startup", environment=settings.ENVIRONMENT)
    yield
    if settings.SCHEDULER_ENABLED:
        stop_scheduler()
    shutdown_scrapling()
    log.info("app.shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Compress responses (the Geography map data file is ~1 MB of JSON; gzip makes it ~370 KB)
app.add_middleware(GZipMiddleware, minimum_size=1024)

# --- Security middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.masark.app", "masark.app"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Domain error handling ---
app.add_exception_handler(MasarkError, masark_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request", "errors": exc.errors()},
    )


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


# --- Routers ---
prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(platforms.router, prefix=prefix)
app.include_router(subjects.router, prefix=prefix)
app.include_router(lectures.router, prefix=prefix)
app.include_router(lecture_study.router, prefix=prefix)
app.include_router(study_plan.router, prefix=prefix)
app.include_router(ai.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)

# --- Serve the frontend from the same process/port ---
# Lets `uvicorn app.main:app --port 8000` alone serve the whole app
# (http://127.0.0.1:8000/login.html etc.) instead of needing a second
# `python -m http.server` for the frontend. Mounted LAST and at "/" so it
# only ever catches requests that didn't match an API route above (Starlette
# checks routes in registration order - /health and everything under
# API_V1_PREFIX were already registered and always win first).
#
# Only mounts if the frontend/ folder is actually present next to backend/
# - it deliberately won't exist inside the backend's own Docker image (see
# Dockerfile, which only COPYs `app`), so production deployments that serve
# the frontend separately (Firebase Hosting, Netlify, etc., per the README)
# are unaffected; this only activates for local same-repo dev.
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
    log.info("frontend.mounted", path=str(_frontend_dir))
else:
    log.info("frontend.not_mounted", looked_in=str(_frontend_dir))