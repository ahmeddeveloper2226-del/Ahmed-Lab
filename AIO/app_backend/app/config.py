from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:password@postgres:5432/app_db"

    redis_url: str = "redis://redis:6379/0"

    elasticsearch_url: str = "http://elasticsearch:9200"

    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"


    # Firebase Admin (path to the service account JSON you download from Firebase Console)
    firebase_credentials_path: str = "firebase-service-account.json"

    # Found in Firebase Console -> Project Settings -> General -> Web API Key.
    # ONLY used by scripts/get_test_token.py for local testing — never used
    # by the running server itself, so this being present doesn't grant any
    # extra runtime access.
    firebase_web_api_key: str = "AIzaSyCgDoIqi5OgjHAoWLS8v1vimHuVc8kxaSI"

    # SMTP — used to send real verification code emails. Gmail example:
    # smtp_host=smtp.gmail.com, smtp_port=587, smtp_username=your@gmail.com,
    # smtp_password=<a 16-character Gmail APP PASSWORD, not your real
    # Gmail password — generate one at myaccount.google.com/apppasswords>.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    sender_name: str = "Wasla"

    # Wasla's cut of every order — 15% per the business model discussed.
    # Stored here (not hardcoded in order_service.py) so it can be changed
    # in one place; note that changing this does NOT retroactively affect
    # historical orders, since commission_amount is stored per-order at
    # creation time, not recomputed from this setting later.
    commission_rate: float = 0.15

    # Driver nearest-orders matching (see driver_router.py).
    # Radius (km) within which orders are shown to a driver at all.
    driver_search_radius_km: float = 15.0
    # A driver holding an active order may accept ANOTHER order only if its
    # shop is within this distance (km) of every one of their other active
    # orders' shops — keeps a multi-order run to genuinely nearby pickups
    # instead of zig-zagging across the city.
    driver_cluster_distance_km: float = 3.0
    # Hard cap on how many orders a single driver can hold at once, even if
    # they're all clustered close together.
    driver_max_concurrent_orders: int = 3

    # --- Zone-based delivery grouping (see geo_utils.cluster_shops_by_zone
    # and workers/driver_assignment_worker.py) -----------------------------
    # Shop-orders from the same checkout within this distance (km) of each
    # other are chained into one delivery zone and offered together to a
    # single driver. Shops farther apart than this end up in separate zones,
    # each getting its own driver.
    delivery_zone_radius_km: float = 5.0
    # How long (seconds) a driver has to accept an offered delivery group
    # before the assignment worker's sweep reclaims it and offers the
    # next-nearest driver instead.
    driver_offer_timeout_seconds: int = 20

    # --- AIO delivery pricing / ETA (see services/delivery_service.py) ---
    # Fallback average city speed (km/h) used ONLY when no real routing
    # provider is configured (routing_provider="haversine") — deliberately
    # conservative for Cairo traffic rather than optimistic, since ETA
    # promises that run late erode trust faster than ones that run early.
    fallback_avg_speed_kmh: float = 18.0
    # Fixed minutes added to every ETA for parking/finding-the-door/traffic-
    # light variance not captured by route time itself.
    delivery_safety_buffer_minutes: int = 7
    # Minutes a driver is assumed to need to reach ANY branch from wherever
    # they currently are queued, when no driver is pre-assigned yet (used
    # for the customer-facing pre-checkout ETA estimate only).
    assumed_driver_to_branch_minutes: int = 8

    # Delivery fee formula: base + (per_km * road_distance_km), floored at
    # minimum_delivery_fee. Kept as flat settings (not a pricing engine) —
    # swap for a real rules engine later without changing callers, since
    # everything routes through delivery_service.calculate_delivery_fee().
    base_delivery_fee: float = 15.0
    per_km_delivery_fee: float = 2.5
    minimum_delivery_fee: float = 20.0

    # Which routing backend estimate_route() uses. "haversine" (default) is
    # the straight-line-with-a-road-factor fallback that needs no API key;
    # set to "google" or "osrm" once a routing provider is wired up and
    # this becomes the actual road-network calculation the spec calls for.
    routing_provider: str = "haversine"
    # Straight-line distances are multiplied by this factor to approximate
    # real road distance when routing_provider="haversine" — Cairo's street
    # grid isn't direct, so a pure straight line under-counts actual travel.
    haversine_road_factor: float = 1.35

    # Simple shared-password gate for the local admin panel (index.html) —
    # deliberately NOT Firebase auth. This is appropriate for a single-admin,
    # local-only tool; it is NOT appropriate once the admin panel is exposed
    # on the public internet to multiple people — at that point this should
    # go back to real per-person authentication. Override via the
    # ADMIN_PANEL_SECRET environment variable before deploying anywhere.
    admin_panel_secret: str = ""

    # --- Realtime chat/calls/location -----------------------------------
    # Local disk path for voice-message audio storage. See
    # services/chat_service.py's module docstring for why this is local
    # disk rather than cloud storage for now.
    media_storage_path: str = "media"

    # Free public STUN server — good enough to negotiate connections when
    # both peers aren't behind restrictive/symmetric NAT. Google's public
    # STUN server, widely used for this exact purpose.
    stun_server_url: str = "stun:stun.l.google.com:19302"

    # TURN is the fallback for when STUN alone can't establish a direct
    # connection (common on mobile carrier networks with carrier-grade
    # NAT, or symmetric NAT on either side) — WebRTC calls WILL fail for a
    # meaningful fraction of real users without one. These are left empty
    # by default because a real TURN server (e.g. self-hosted coturn, or a
    # managed service like Twilio Network Traversal / Xirsys / Cloudflare
    # Calls) needs to be provisioned separately — this project doesn't
    # have one configured. GET /calls/ice-servers omits the TURN entry
    # entirely when these are blank, rather than returning broken
    # credentials.
    turn_server_url: str = ""
    turn_username: str = ""
    turn_credential: str = ""

    # Paymob
    paymob_api_key: str = ""
    paymob_integration_id: str = ""
    paymob_iframe_id: str = ""
    paymob_hmac_secret: str = ""

    # AI shopping assistant (see app/services/ai_assistant_service.py) —
    # get a key at https://console.anthropic.com. Left blank by default;
    # the /ai/chat endpoint returns a clear 503 rather than crashing if
    # this isn't set, so a fresh deployment without it configured yet
    # doesn't take the rest of the API down.
    anthropic_api_key: str = ""
    # Haiku, not Sonnet — this task (parse an order, call a search tool,
    # ask for clarification, call add_to_cart) doesn't need Sonnet-level
    # reasoning, and Haiku costs a fraction per token. Bump back to
    # 'claude-sonnet-4-5' via env if you find Haiku genuinely getting
    # orders wrong in practice — quality first, but it's worth trying the
    # cheap tier before assuming you need the expensive one.
    ai_assistant_model: str = "claude-haiku-4-5-20251001"
    # Hard per-user daily cap — see ai_assistant_service.py's usage check.
    # This is the real protection against a runaway bill (a bug that loops,
    # one abusive account, a bot) — not something a smaller model fixes.
    ai_assistant_daily_message_limit: int = 60

    # Encrypts vendor bank/wallet account numbers at rest (see
    # services/payout_encryption.py) — this is real financial data, not
    # something that should ever sit in Postgres as plain text. Generate
    # one PER ENVIRONMENT with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Losing/rotating this key makes every already-saved payout account
    # number permanently undecryptable — back it up like a database
    # password, not like a regular env var. Empty in dev by default;
    # payout_encryption.py refuses to start up without a real one set.
    payout_encryption_key: str = ""

    # Static HTML panel directories. Defaults are relative to the repo root
    # (what the Dockerfile copies them to — see docker-compose.yml) so the
    # same settings work unchanged in the container. Override via .env for
    # local Windows/Mac dev if you keep these panel files somewhere else
    # (e.g. admin_panel_dir=E:\add_driver like the previous hardcoded path).
    admin_panel_dir: str = "panels/admin_panel"
    store_panel_dir: str = "panels/store_panel"
    store_management_panel_dir: str = "panels/store_management_panel"




# Import this single instance everywhere instead of re-reading env vars per file.
settings = Settings()
