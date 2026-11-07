"""
Discovery routes used during onboarding / when adding a subject in المواد.

/lectures-by-url is the primary route: the student pastes a direct link to a
pack (or to whatever page lists the lectures) and we hand that exact URL to
the Scrapling-based scraper for that platform (or the generic Scrapling
scraper for unknown domains) - no platform picker, no browsing step.

The older /subjects/{slug}/packs discovery route is left in place for API
completeness / a future "browse" feature; the frontend no longer calls it.
"""

import hashlib

import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.subject import PlatformInfo, PlatformKey, TeacherOrPack
from app.services import firestore_service as db
from app.services.scraping import handoff
from app.services.scraping.executor import run_scraper_call
from app.services.scraping.registry import (
    PLATFORM_CATALOG,
    URL_LECTURES_CACHE_NS,
    get_scraper,
    get_scraper_for_url,
)

log = structlog.get_logger()
settings = get_settings()
router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformInfo])
@limiter.limit("60/minute")
def list_platforms(request: Request):
    return PLATFORM_CATALOG


@router.get("/lectures-by-url")
@limiter.limit("10/minute")
async def lectures_by_url(
    request: Request,
    url: str = Query(..., description="Direct link to a pack, or to whatever page lists the lectures"),
    user: CurrentUser = Depends(get_current_user),
):
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=422, detail="Enter a valid link starting with http:// or https://")

    # Every request scrapes the page from scratch. The Firestore scrape cache is only
    # touched when SCRAPER_USE_CACHE=true in .env (off by default).
    cache_key = hashlib.sha256(url.encode()).hexdigest()
    if settings.SCRAPER_USE_CACHE:
        cached = db.get_cached_catalog(URL_LECTURES_CACHE_NS, cache_key)
        if cached and cached.get("items"):
            return cached

    platform, scraper = get_scraper_for_url(url)
    try:
        lectures = await run_scraper_call(scraper.list_lectures, url)
    except Exception as exc:  # noqa: BLE001
        log.error("platforms.lectures_by_url_failed", url=url,
                  error_type=type(exc).__name__, error=repr(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="Could not read that page right now") from exc
    finally:
        scraper.close()

    handoff.put(user.uid, url, lectures)  # lets "Add subject" skip a second scrape
    platform_info = next((p for p in PLATFORM_CATALOG if p.key == platform), None) if platform else None
    result = {
        "items": [l.model_dump() for l in lectures],
        "detected_platform": platform.value if platform else None,
        "detected_platform_name": platform_info.name_en if platform_info else None,
    }
    if lectures and settings.SCRAPER_USE_CACHE:  # never cache an empty answer
        db.set_cached_catalog(URL_LECTURES_CACHE_NS, cache_key, result)
    return result


@router.get("/{platform}/subjects/{subject_slug}/packs")
@limiter.limit("20/minute")
async def list_packs_or_teachers(
    request: Request,
    platform: PlatformKey,
    subject_slug: str,
    academic_year: str | None = Query(None, description="Student's chosen year, e.g. 'year_3'"),
    teacher_url: str | None = Query(
        None,
        description=(
            "Pass the url of a 'teacher'-kind item returned from a prior call "
            "to this same endpoint to drill down into THAT teacher's own packs "
            "for this subject/year, instead of listing every teacher/pack on "
            "the platform again."
        ),
    ),
):
    # Cache key includes year + which teacher (if any) we're scoped to, so
    # a query for a bare subject and a query for one teacher's packs never
    # collide, and different years for the same subject don't either.
    cache_key = f"{subject_slug}:{academic_year or 'any'}:packs:{teacher_url or 'all'}"
    cached = db.get_cached_catalog(platform.value, cache_key)
    if cached and cached.get("items"):
        return cached["items"]

    scraper = get_scraper(platform)
    try:
        if teacher_url:
            items = await run_scraper_call(
                scraper.list_packs_for_teacher, teacher_url, subject_slug, academic_year
            )
        else:
            items = await run_scraper_call(
                scraper.list_packs_or_teachers, subject_slug, academic_year
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not reach {platform.value}") from exc
    finally:
        scraper.close()

    serialized = [item.model_dump() for item in items]
    db.set_cached_catalog(platform.value, cache_key, {"items": serialized})
    return serialized


@router.get("/{platform}/lectures")
@limiter.limit("20/minute")
async def preview_lectures(
    request: Request,
    platform: PlatformKey,
    pack_or_teacher_url: str = Query(..., description="URL returned by /packs above"),
):
    scraper = get_scraper(platform)
    try:
        lectures = await run_scraper_call(scraper.list_lectures, pack_or_teacher_url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Could not reach {platform.value}") from exc
    finally:
        scraper.close()
    return [l.model_dump() for l in lectures]


@router.post("/suggest")
@limiter.limit("5/minute")
def suggest_platform(request: Request, name: str, url: str | None = None):
    """Lets a student recommend a platform we don't support yet."""
    db.get_db().collection("platform_suggestions").add({
        "name": name, "url": url,
    })
    return {"detail": "thanks, we'll take a look"}