import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.subject import SourceMode, SubjectEnrollmentRequest
from app.services import firestore_service as db
from app.services.scraping.executor import run_scraper_call
from app.services.scraping import handoff
from app.services.scraping.models import ScrapedLecture
from app.services.scraping.registry import URL_LECTURES_CACHE_NS, get_scraper, get_scraper_for_url

settings = get_settings()
router = APIRouter(prefix="/subjects", tags=["subjects"])


def _create_subject(uid: str, enrollment: dict, lecture_rows: list[dict]) -> dict:
    """All the blocking Firestore writes for a new subject (runs in a worker thread)."""
    enrollment_id = db.create_enrollment(uid, enrollment)
    if lecture_rows:
        try:
            db.bulk_upsert_lectures(uid, enrollment_id, lecture_rows)
        except Exception:
            db.delete_enrollment(uid, enrollment_id)  # never leave an empty subject behind
            raise
        completed = sum(1 for r in lecture_rows if r.get("is_completed"))
        db.update_enrollment(uid, enrollment_id, {
            "total_lectures": len(lecture_rows),
            "completed_lectures": completed,
            "last_synced_at": datetime.now(timezone.utc),
        })
    return {"id": enrollment_id, "lectures_found": len(lecture_rows)}


@router.get("")
@limiter.limit("60/minute")
def list_my_subjects(request: Request, user: CurrentUser = Depends(get_current_user)):
    return db.list_enrollments(user.uid)


@router.post("")
@limiter.limit("20/minute")
async def add_subject(
    payload: SubjectEnrollmentRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    lecture_rows: list[dict] = []
    detected_platform = payload.platform  # may already be set by an older client; re-detect below if not

    if payload.source_mode == SourceMode.MANUAL:
        for i, lec in enumerate(payload.manual_lectures):
            lecture_rows.append({
                "title": lec.title,
                "url": None,
                "uploaded_on": lec.uploaded_on,
                "order": lec.order or i,
                "is_completed": False,
                "homework_done": None,
            })
    elif payload.teacher_or_pack_url:
        # Platform is auto-detected from the pasted link's domain - the
        # student never has to pick one (see registry.get_scraper_for_url).
        # An unrecognized domain still works: it just runs the agent
        # without a platform-specific hint.
        if detected_platform is None:
            detected_platform, scraper = get_scraper_for_url(payload.teacher_or_pack_url)
        else:
            scraper = get_scraper(detected_platform)
        # Always scrape fresh - never reuse the preview's result. (Only when
        # SCRAPER_USE_CACHE=true do we read the Firestore scrape cache.)
        # The lectures the student just previewed (scraped fresh seconds ago, in RAM only,
        # one use, 15 min max) - makes "Add" instant instead of scraping a second time.
        scraped = handoff.take(user.uid, payload.teacher_or_pack_url)
        cached = None
        if scraped is None and settings.SCRAPER_USE_CACHE:
            cache_key = hashlib.sha256(payload.teacher_or_pack_url.encode()).hexdigest()
            cached = db.get_cached_catalog(URL_LECTURES_CACHE_NS, cache_key)
        if scraped is not None:
            pass
        elif cached and cached.get("items"):
            scraped = [ScrapedLecture(**i) for i in cached["items"]]
        else:
            try:
                scraped = await run_scraper_call(scraper.list_lectures, payload.teacher_or_pack_url)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=502, detail="Could not fetch lectures right now") from exc
            finally:
                scraper.close()
        if not scraped:
            raise HTTPException(status_code=422, detail="No lectures were found at that link")
        for lec in scraped:
            lecture_rows.append({
                "external_id_as_doc_id": lec.external_id,
                "title": lec.title,
                "url": lec.url,
                "uploaded_on": lec.uploaded_on,
                "order": lec.order,
                "is_completed": lec.external_id in payload.already_completed_lecture_ids,
                "homework_done": None,
            })

    enrollment = {
        "uid": user.uid,
        "subject_name": payload.subject_name,
        "subject_slug": payload.subject_slug,
        "source_mode": payload.source_mode.value,
        "platform": detected_platform.value if detected_platform else None,
        "teacher_or_pack_id": payload.teacher_or_pack_id,
        "teacher_or_pack_url": payload.teacher_or_pack_url,
        "total_lectures": 0,
        "completed_lectures": 0,
    }
    return await run_in_threadpool(_create_subject, user.uid, enrollment, lecture_rows)


@router.delete("/{enrollment_id}")
@limiter.limit("20/minute")
def remove_subject(
    enrollment_id: str, request: Request, user: CurrentUser = Depends(get_current_user)
):
    if not db.get_enrollment(user.uid, enrollment_id):
        raise NotFoundError("Subject not found")
    db.delete_enrollment(user.uid, enrollment_id)
    return {"detail": "removed"}

@router.post("/{enrollment_id}/sync")
@limiter.limit("6/minute")
async def sync_subject_now(
    enrollment_id: str, request: Request, user: CurrentUser = Depends(get_current_user)
):
    """Re-scrape this subject's saved link right now (fresh, no cache) and add any
    lectures that were uploaded since the last sync. Same logic as the daily job."""
    from app.jobs.scheduler import apply_scraped_lectures  # local import: avoids a cycle at startup

    enrollment = await run_in_threadpool(db.get_enrollment, user.uid, enrollment_id)
    if not enrollment:
        raise NotFoundError("Subject not found")
    url = enrollment.get("teacher_or_pack_url")
    if not url:
        raise HTTPException(status_code=422, detail="This subject has no link to sync")
    _, scraper = get_scraper_for_url(url)
    try:
        lectures = await run_scraper_call(scraper.list_lectures, url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Could not fetch lectures right now") from exc
    finally:
        scraper.close()
    added = await run_in_threadpool(apply_scraped_lectures, user.uid, enrollment, lectures)
    return {"new_lectures": added, "scraped": len(lectures)}