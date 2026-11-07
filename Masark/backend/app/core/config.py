"""
Central application configuration.

Everything that differs between environments (dev/staging/prod) or that is
secret lives here and is loaded from environment variables / a local .env
file. NOTHING secret is ever hardcoded in source. See backend/.env.example
for the full list of variables you need to set.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    APP_NAME: str = "Masark API"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(..., description="Used for signing internal tokens/cookies")

    # --- CORS ---
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # --- Firebase ---
    # Path to the service-account JSON (mounted as a secret file in prod,
    # local file in dev). Never commit this file.
    FIREBASE_CREDENTIALS_PATH: str = "./secrets/firebase-service-account.json"
    FIREBASE_PROJECT_ID: str = "masark-38cee"
    FIREBASE_WEB_API_KEY: str = ""  # used only for email/password REST auth calls

    # --- Groq AI ---
    # All three AI features (study plan, تراكم chat, subject Q&A) run on
    # Groq's OpenAI-compatible chat.completions endpoint. GROQ_MODEL_PRO is
    # reserved for a heavier model if one feature ever needs more headroom
    # than gpt-oss-20b gives it — both currently point at the same model.
    # If Groq deprecates a model line, list what your key currently has
    # access to with:
    #   from groq import Groq; c = Groq(api_key=...)
    #   for m in c.models.list().data: print(m.id)
    GROQ_API_KEY: str = Field(..., description="Rotate immediately if ever exposed")
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_MODEL_PRO: str = "openai/gpt-oss-20b"

    # --- Rate limiting ---
    RATE_LIMIT_STORAGE_URI: str = "memory://"  # use redis://host:6379 in production
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AI: str = "10/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # --- Scraping ---
    # No SCRAPER_USER_AGENT setting anymore - Scrapling's fetchers generate
    # (and keep up to date) a real, matching browser User-Agent themselves
    # via `impersonate`/`stealthy_headers` (see scrapling_pool.py), which is
    # more convincing than one hardcoded string could ever stay.
    SCRAPER_REQUEST_TIMEOUT_SECONDS: int = 20
    SCRAPER_MAX_CONCURRENCY: int = 4
    SCRAPER_DAILY_SYNC_HOUR_UTC: int = 1  # 3 AM Cairo time (UTC+2)
    PLAYWRIGHT_HEADLESS: bool = True
    # Persistent browser profile: cookies/localStorage survive restarts, so a
    # login done once (manually or by the login flow) is reused afterwards.
    SCRAPER_PROFILE_DIR: str = "./.scraper_profile"
    # False = every request scrapes the platform from scratch (nothing is read from
    # or written to the Firestore scrape cache). Set True only to save scrape time.
    SCRAPER_USE_CACHE: bool = False
    # Wipe the browser's own HTTP/service-worker cache (NOT cookies/logins) every time the
    # scraping browser starts, and send no-cache headers on every request.
    SCRAPER_CLEAR_BROWSER_CACHE: bool = True

    # --- Daily lecture sync ---
    # Runs regardless of ENVIRONMENT (it used to be skipped in "development").
    SCHEDULER_ENABLED: bool = True
    # An enrollment whose last sync is older than this is re-scraped by the hourly
    # catch-up job - so "daily" still happens if the PC was off at the cron hour.
    SCRAPER_SYNC_MAX_AGE_HOURS: int = 23

    # --- Platform accounts (YOUR account, used to read packs/lectures) ---
    # Leave blank for platforms you don't need. Never commit real values.
    BASSTHALK_EMAIL: str = ""   # phone number also works here
    BASSTHALK_PHONE: str = ""   # or put it here (takes priority)
    BASSTHALK_PASSWORD: str = ""
    FULLMARK_EMAIL: str = ""   # phone number also works here
    FULLMARK_PHONE: str = ""   # or put it here (takes priority)
    FULLMARK_PASSWORD: str = ""
    SMART_ACADEMY_EMAIL: str = ""   # phone number also works here
    SMART_ACADEMY_PHONE: str = ""   # or put it here (takes priority)
    SMART_ACADEMY_PASSWORD: str = ""
    EDNUVA_EMAIL: str = ""   # phone number also works here
    EDNUVA_PHONE: str = ""   # or put it here (takes priority)
    EDNUVA_PASSWORD: str = ""
    EDUACT_EMAIL: str = ""   # phone number also works here
    EDUACT_PHONE: str = ""   # or put it here (takes priority)
    EDUACT_PASSWORD: str = ""
    CSA_EMAIL: str = ""   # phone number also works here
    CSA_PHONE: str = ""   # or put it here (takes priority)
    CSA_PASSWORD: str = ""

    # --- Notifications ---
    NOTIFICATION_DAILY_HOUR_UTC: int = 16  # 6 PM Cairo time
    FCM_ENABLED: bool = True

    # --- Timezone ---
    APP_TIMEZONE: str = "Africa/Cairo"

    @field_validator("SECRET_KEY", "GROQ_API_KEY")
    @classmethod
    def not_placeholder(cls, v: str) -> str:
        if not v or v.startswith("REPLACE_"):
            raise ValueError(
                "A required secret is missing or still a placeholder. "
                "Set it in backend/.env (see .env.example)."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()