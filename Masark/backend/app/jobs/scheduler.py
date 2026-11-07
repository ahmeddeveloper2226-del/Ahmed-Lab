"""
Background jobs, run in-process via APScheduler:

  1. daily_sync_all_students   - once a day, re-scrapes EVERY link students saved for their
     subjects (always fresh - no cache of any kind) and adds lectures uploaded since the
     last sync. Each distinct link is scraped ONCE per run, then fanned out to every
     student who saved it.
  2. sync_stale_enrollments    - runs shortly after startup and then hourly; re-syncs any
     subject not synced in the last SCRAPER_SYNC_MAX_AGE_HOURS. This is what keeps the sync
     "daily" when the backend (e.g. a laptop) wasn't running at the cron hour.
  3. daily_notifications       - reminds every student, once a day, how many lectures are
     left this week and which lectures still need a homework status.

For anything beyond a single-instance deployment, replace APScheduler with a real task
queue (Celery/RQ): the job bodies would not need to change, only how they're triggered.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.services import firestore_service as db
from app.services import notification_service
from app.services.scraping.executor import run_scraper_call_sync
from app.services.scraping.registry import get_scraper_for_url

log = structlog.get_logger()
settings = get_settings()

scheduler = BackgroundScheduler(timezone="UTC")

# Only one sync run at a time (cron run, hourly catch-up and manual runs must not overlap).
_sync_lock = threading.Lock()


def _as_utc(value) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def apply_scraped_lectures(uid: str, enrollment: dict, lectures: list) -> int:
    """Save lectures that are NEW for this enrollment; returns how many were added.

    A lecture counts as already known if its external id (the Firestore doc id) OR its
    title exists - so a renamed lecture is never re-added, and an existing lecture's
    is_completed / homework_done are never overwritten. Nothing is ever deleted: an empty
    or partial scrape can't wipe a student's progress."""
    enrollment_id = enrollment["id"]
    if not db.get_enrollment(uid, enrollment_id):  # student deleted it while we were scraping
        return 0
    existing = db.list_lectures(uid, enrollment_id)
    known_ids = {l["id"] for l in existing}
    known_titles = {l.get("title") for l in existing}

    new_rows = []
    for lec in lectures:
        if lec.external_id in known_ids or lec.title in known_titles:
            continue
        known_ids.add(lec.external_id)
        known_titles.add(lec.title)
        new_rows.append({
            "external_id_as_doc_id": lec.external_id,
            "title": lec.title,
            "url": lec.url,
            "uploaded_on": lec.uploaded_on,
            "order": lec.order,
            "is_completed": False,
            "homework_done": None,
        })

    updates: dict = {"last_synced_at": datetime.now(timezone.utc)}
    if new_rows:
        db.bulk_upsert_lectures(uid, enrollment_id, new_rows)
        updates["total_lectures"] = len(existing) + len(new_rows)
    db.update_enrollment(uid, enrollment_id, updates)
    return len(new_rows)


def _scrape_url(pack_url: str) -> list | None:
    """Scrape one link from scratch. None = the scrape failed (as opposed to [] = nothing there)."""
    _, scraper = get_scraper_for_url(pack_url)
    try:
        return run_scraper_call_sync(scraper.list_lectures, pack_url)
    except Exception:  # noqa: BLE001
        log.warning("sync.scrape_failed", url=pack_url, exc_info=True)
        return None
    finally:
        scraper.close()


def _sync(enrollments: list[tuple[str, dict]], reason: str) -> None:
    """enrollments: [(uid, enrollment)]. Scrapes each distinct link once, fans out to all."""
    by_url: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for uid, enrollment in enrollments:
        url = enrollment.get("teacher_or_pack_url")
        if url:  # manual-mode enrollments have no link: nothing to scrape
            by_url[url].append((uid, enrollment))

    total_new = 0
    for url, owners in by_url.items():
        lectures = _scrape_url(url)
        if lectures is None:
            continue  # scrape failed: leave last_synced_at alone so the hourly job retries
        if not lectures:
            log.warning("sync.empty_result", url=url, reason=reason)
            continue  # nothing found: don't mark synced, retry later
        for uid, enrollment in owners:
            try:
                added = apply_scraped_lectures(uid, enrollment, lectures)
            except Exception:  # noqa: BLE001
                log.warning("sync.apply_failed", uid=uid, enrollment=enrollment.get("id"), exc_info=True)
                continue
            total_new += added
            log.info("sync.done", uid=uid, url=url, scraped=len(lectures), new_lectures=added)
    log.info("sync.job_end", reason=reason, links=len(by_url), new_lectures=total_new)


def _all_enrollments() -> list[tuple[str, dict]]:
    # NOTE: for real scale, page through users rather than loading them all; Firestore's
    # `.stream()` already paginates server-side and this runs off the request path.
    out = []
    for user_doc in db.get_db().collection("users").stream():
        for enrollment in db.list_enrollments(user_doc.id):
            out.append((user_doc.id, enrollment))
    return out


def daily_sync_all_students() -> None:
    if not _sync_lock.acquire(blocking=False):
        log.info("sync.skipped_already_running")
        return
    try:
        log.info("sync.job_start", reason="daily")
        _sync(_all_enrollments(), reason="daily")
    finally:
        _sync_lock.release()


def sync_stale_enrollments() -> None:
    """Catch-up: re-sync only subjects not synced within SCRAPER_SYNC_MAX_AGE_HOURS."""
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.SCRAPER_SYNC_MAX_AGE_HOURS)
        stale = [(uid, e) for uid, e in _all_enrollments()
                 if e.get("teacher_or_pack_url")
                 and (_as_utc(e.get("last_synced_at")) or datetime.min.replace(tzinfo=timezone.utc)) < cutoff]
        if stale:
            log.info("sync.job_start", reason="catch_up", stale=len(stale))
            _sync(stale, reason="catch_up")
    finally:
        _sync_lock.release()


def daily_notifications() -> None:
    log.info("notifications.job_start")
    for user_doc in db.get_db().collection("users").stream():
        uid = user_doc.id
        user = user_doc.to_dict()
        tokens = user.get("fcm_tokens", [])
        language = user.get("language", "ar")
        if not tokens:
            continue

        lectures = db.list_all_lectures_for_user(uid)
        remaining = sum(1 for l in lectures if not l.get("is_completed"))
        pending_homework = sum(
            1 for l in lectures if l.get("is_completed") and l.get("homework_done") is None
        )
        notification_service.notify_lectures_remaining(uid, tokens, remaining, language)
        notification_service.notify_homework_pending(uid, tokens, pending_homework, language)
    log.info("notifications.job_end")


def start_scheduler() -> None:
    scheduler.add_job(
        daily_sync_all_students,
        CronTrigger(hour=settings.SCRAPER_DAILY_SYNC_HOUR_UTC, minute=0),
        id="daily_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=6 * 3600,  # still run if the app was busy/asleep at the exact minute
    )
    scheduler.add_job(
        sync_stale_enrollments,
        IntervalTrigger(hours=1),
        id="sync_catch_up",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=60),  # also checks right after startup
    )
    scheduler.add_job(
        daily_notifications,
        CronTrigger(hour=settings.NOTIFICATION_DAILY_HOUR_UTC, minute=0),
        id="daily_notifications",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    log.info("scheduler.started")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)