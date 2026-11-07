import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .logging_config import configure_logging
from .rate_limiter import limiter
from .redis_client import check_redis_connection
from .elasticsearch_client import check_elasticsearch_connection
from .rabbitmq_client import connect_rabbitmq, close_rabbitmq
from .services.search_service import ensure_products_index_exists

from .routers import (
    auth_router,
    cart_router,
    categories_router,
    checkout_router,
    orders_router,
    payment_webhook_router,
    products_router,
    profile_router,
    search_router,
    shops_router,
    store_panel_router,
)
# Uncomment as you build them:
from .routers import (
    tracking_ws_router, driver_router, store_panel_router,
    driver_auth_router, admin_router, chat_router, call_router, realtime_ws_router,
    store_management_router, prescriptions_router, ai_assistant_router,
    shopping_list_router, meal_builder_router, medication_router, reviews_router,
)

configure_logging()


import logging

startup_logger = logging.getLogger("wasla.startup")


async def _retry_startup_check(name: str, check_fn, max_attempts: int = 5, base_delay: float = 2.0):
    """
    Retries a startup dependency check with exponential backoff, instead of
    crashing the whole server on the first failure. This matters concretely
    because Docker containers (especially Elasticsearch, which is slow to
    boot) can report as "running" before they're actually ready to accept
    connections — a fresh `docker compose up -d` followed immediately by
    starting this server is a completely normal sequence that used to fail
    outright. Real infrastructure has this kind of startup lag; a
    production server should tolerate it, not treat it as fatal.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            await check_fn()
            startup_logger.info(f"{name} connection OK (attempt {attempt}/{max_attempts})")
            return
        except Exception as e:
            if attempt == max_attempts:
                startup_logger.error(
                    f"{name} connection FAILED after {max_attempts} attempts: {e}"
                )
                raise
            delay = base_delay * attempt
            startup_logger.warning(
                f"{name} not ready yet (attempt {attempt}/{max_attempts}): {e}. "
                f"Retrying in {delay:.0f}s..."
            )
            await asyncio.sleep(delay)


_WEAK_ADMIN_SECRETS = {"2211", "admin", "password", "123456", ""}


def _guard_production_secrets() -> None:
    """
    Refuses to start in production with known-unsafe defaults. This is a
    deliberate hard failure (not a warning) because these specific
    settings gate real admin/store access — a silent misconfiguration
    here means anyone can reach the admin or store-management panels.
    """
    if settings.environment != "production":
        return
    problems = []
    if settings.admin_panel_secret in _WEAK_ADMIN_SECRETS:
        problems.append(
            "ADMIN_PANEL_SECRET is unset or a known weak default — set a long, "
            "random value in .env before deploying."
        )
    if not settings.anthropic_api_key:
        # Not fatal on its own (the /ai/chat endpoint already degrades
        # gracefully), but worth surfacing loudly since this project's
        # config previously shipped a real key hardcoded as a fallback.
        startup_logger.warning(
            "ANTHROPIC_API_KEY is not set — /ai/chat will return 503 until it is."
        )
    if problems:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration:\n- "
            + "\n- ".join(problems)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _guard_production_secrets()
    await _retry_startup_check("Redis", check_redis_connection)
    await _retry_startup_check("Elasticsearch", check_elasticsearch_connection)
    await ensure_products_index_exists()
    await _retry_startup_check("RabbitMQ", connect_rabbitmq)

    # Diagnostic added while chasing a route that showed correctly in
    # /docs and in the source file, yet 404'd on real requests. This
    # prints EVERY route FastAPI actually has registered, straight from
    # app.routes at the moment the server starts serving — the one
    # source of truth /docs, grep, and file contents can all disagree
    # with if something is stale or duplicated. Look specifically for
    # more than one line containing the same path, or its total absence
    # despite being in the file.
    startup_logger.info("Registered routes (%d total):", len(app.routes))
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if path is not None:
            startup_logger.info("  %s %s", sorted(methods) if methods else "MOUNT", path)

    yield
    await close_rabbitmq()


app = FastAPI(title="Wasla Backend", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.environment == "production":
    allowed_origins = ["https://yourdomain.com", "https://store.yourdomain.com", "https://admin.yourdomain.com"]
else:
    allowed_origins = ["http://localhost:3000", "http://localhost:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """
    Baseline security headers for every response. None of these replace
    proper auth/validation elsewhere — they reduce the blast radius of
    classes of browser-side attacks (clickjacking on the admin/store
    panels, MIME sniffing, leaking full referrer URLs which may contain
    tokens in query strings for the WS endpoints).
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )

    # Every response from this API is either dynamic JSON or a redirect —
    # nothing here should ever be cached by the browser. Without this,
    # a GET request that ever returns a 404/error (e.g. hit once before
    # a route existed, or during a deploy) can get cached by the browser
    # and keep being served from disk cache indefinitely — invisible to
    # every server-side fix, restart, or rebuild, since the browser never
    # re-asks the server. This happened in practice with the branches
    # endpoint: the code and route were correct on every check, but an
    # early cached 404 kept being served client-side regardless. Static
    # files (the HTML panels themselves, served below via StaticFiles)
    # are a separate path and unaffected by this — only API responses
    # going through this middleware get the no-store treatment.
    response.headers["Cache-Control"] = "no-store"

    return response

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(profile_router.router, prefix="/me", tags=["profile"])
app.include_router(categories_router.router, prefix="/categories", tags=["categories"])
app.include_router(shops_router.router, tags=["shops"])
app.include_router(products_router.router, tags=["products"])
app.include_router(search_router.router, prefix="/search", tags=["search"])
app.include_router(cart_router.router, prefix="/cart", tags=["cart"])
app.include_router(checkout_router.router, prefix="/checkout", tags=["checkout"])
app.include_router(payment_webhook_router.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(orders_router.router, prefix="/orders", tags=["orders"])
app.include_router(tracking_ws_router.router, tags=["tracking"])
app.include_router(driver_router.router, prefix="/driver", tags=["driver"])
app.include_router(driver_auth_router.router, prefix="/driver/auth", tags=["driver-auth"])
app.include_router(admin_router.router, prefix="/admin", tags=["admin"])
app.include_router(store_panel_router.router, prefix="/store", tags=["store-panel"])
app.include_router(store_management_router.router, prefix="/store-management", tags=["store-management"])
app.include_router(prescriptions_router.router, tags=["prescriptions"])
app.include_router(ai_assistant_router.router, prefix="/ai", tags=["ai-assistant"])
app.include_router(shopping_list_router.router, prefix="/shopping-lists", tags=["shopping-lists"])
app.include_router(meal_builder_router.router, tags=["meal-builder"])
app.include_router(medication_router.router, prefix="/medications", tags=["medications"])
app.include_router(reviews_router.router, tags=["reviews"])
app.include_router(chat_router.router, prefix="/chat", tags=["chat"])
app.include_router(call_router.router, prefix="/calls", tags=["calls"])
app.include_router(realtime_ws_router.router, tags=["realtime"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serves admin_panel/index.html at http://localhost:8000/admin-panel/ —
# same origin as the API itself, so this needs no CORS entry and no
# separate server to run. Mounted last, after every API route, so it can
# never shadow a real endpoint.
#
# Paths come from settings (see config.py) instead of being hardcoded —
# the previous hardcoded `E:\...` paths only worked on one Windows dev
# machine and would break outright on the Linux droplet this now deploys
# to. Defaults point at panels/ in the repo root, which is where the
# Dockerfile copies these HTML files to (see docker-compose.yml / Dockerfile).
app.mount("/admin-panel", StaticFiles(directory=settings.admin_panel_dir, html=True), name="admin-panel")

# Same pattern for the store panel (add/edit stores and their products) —
# see store_panel/index.html. Uses the exact same simple password.
app.mount("/store-panel", StaticFiles(directory=settings.store_panel_dir, html=True), name="store-panel")

# New, separate panel: a shop owner logs in with just their shop_id + the
# password set on their shop (see AdminShopCreateRequest.password /
# store_management_router.py) — no Firebase account needed — and sees
# their own incoming orders. Same "one FastAPI process, no second server"
# pattern as the two mounts above.
app.mount(
    "/store-management-panel",
    StaticFiles(directory=settings.store_management_panel_dir, html=True),
    name="store-management-panel",
)