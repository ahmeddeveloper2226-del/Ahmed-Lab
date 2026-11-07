"""ONE command that gathers what's needed to finish the scrapers.

1. Fill backend/dump_urls.txt - one line per page:
       <platform> <link> [click=<visible text to click after load>]
2. Run:  python collect_all.py
3. Send masark_dumps.zip (created in the backend folder).

For each line it logs in (credentials from .env), opens the link, optionally
clicks a tab/button by its text, and saves: the page HTML, every API (XHR/fetch)
response the page loaded, and the login result. Platforms:
bassthalk fullmark smart_academy ednuva eduact csa
"""
import json, os, shutil
from app.services.scraping.platform_auth import LAST_RESULT, LOGIN_SPECS, ensure_login, form_inventory
from app.services.scraping.scrapling_pool import fetch_page, shutdown_scrapling

import shutil as _shutil
if os.path.isdir("dumps"):
    _shutil.rmtree("dumps")  # start clean every run - a stale mix caused confusion last time
os.makedirs("dumps", exist_ok=True)
counts: dict[str, int] = {}
report: dict[str, str] = {}
logged: set[str] = set()

for line in open("dump_urls.txt", encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    parts = line.split()
    key, url = parts[0], parts[1]
    click = next((p[6:].replace("_", " ") for p in parts[2:] if p.startswith("click=")), None)
    counts[key] = counts.get(key, 0) + 1
    tag = f"{key}_{counts[key]}"
    print(f"\n=== {tag}: {url} ===")
    try:
        if key not in logged:
            lp, _ = fetch_page(LOGIN_SPECS[key].login_url, force_browser=True, settle_ms=4000)
            json.dump(form_inventory(lp), open(f"dumps/{key}_login_form.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            ensure_login(key, force=True)
            ok, msg = LAST_RESULT.get(key, (False, "no attempt (credentials missing in .env?)"))
            report[key] = f"{'OK' if ok else 'FAILED'}: {msg}"
            print("LOGIN", report[key])
            logged.add(key)

        def action(page, _click=click):
            page.wait_for_timeout(3000)
            if _click:
                try:
                    page.get_by_text(_click, exact=False).first.click(timeout=8000)
                    page.wait_for_timeout(4000)
                except Exception as e:  # noqa: BLE001
                    print("  click failed:", repr(e)[:120])
            page.wait_for_timeout(2000)
            return page

        page, _ = fetch_page(url, force_browser=True, settle_ms=3000, page_action=action)
        open(f"dumps/{tag}.html", "wb").write(page.body or b"")
        xhr = [{"url": r.url, "status": r.status, "body": (r.body or b"").decode("utf-8", "ignore")[:40000]}
               for r in (getattr(page, "captured_xhr", None) or [])]
        json.dump(xhr, open(f"dumps/{tag}_xhr.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("final url:", page.url, "| title:", page.css("title::text").get(), "| api responses:", len(xhr))
    except Exception as exc:  # noqa: BLE001
        print("FAILED:", repr(exc))
        report.setdefault(key, f"ERROR: {exc!r}")

json.dump(report, open("dumps/login_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
shutdown_scrapling()
shutil.make_archive("masark_dumps", "zip", "dumps")
print("\nLogin report:", json.dumps(report, ensure_ascii=False, indent=1))
print("Done -> send masark_dumps.zip")