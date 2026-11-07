"""python probe_login.py <platform>
Opens the platform's REAL login page in the same browser the scraper uses and
prints every input/button it finds (name, id, placeholder...). Also saves
dumps/<platform>_login.html. This is how the login form gets verified."""
import json, os, sys
from app.services.scraping.platform_auth import LOGIN_SPECS, form_inventory
from app.services.scraping.scrapling_pool import fetch_page, shutdown_scrapling

key = sys.argv[1]
os.makedirs("dumps", exist_ok=True)
page, _ = fetch_page(LOGIN_SPECS[key].login_url, force_browser=True, settle_ms=4000)
open(f"dumps/{key}_login.html", "wb").write(page.body or b"")
inv = form_inventory(page)
json.dump(inv, open(f"dumps/{key}_login_form.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("url:", page.url)
for i in inv: print(i)
shutdown_scrapling()
