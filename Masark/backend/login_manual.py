"""python login_manual.py <platform>  -> opens a VISIBLE browser on the login page.
Log in by hand (solve any captcha), then close the window. The session is saved in
SCRAPER_PROFILE_DIR and reused by the scraper - no password needed in .env."""
import sys
from scrapling.fetchers import StealthySession
from app.core.config import get_settings
from app.services.scraping.platform_auth import LOGIN_SPECS

spec = LOGIN_SPECS[sys.argv[1]]
with StealthySession(headless=False, user_data_dir=get_settings().SCRAPER_PROFILE_DIR, timeout=600_000) as s:
    s.fetch(spec.login_url, page_action=lambda page: (input("Log in in the browser, then press Enter here... "), page)[1])
