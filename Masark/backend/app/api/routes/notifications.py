"""Manual trigger for admins/testing + the FCM token registration lives in
users.py since it's part of the profile. This route is for ops visibility."""

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.jobs.scheduler import daily_notifications, daily_sync_all_students

router = APIRouter(prefix="/admin/jobs", tags=["admin"])
settings = get_settings()


@router.post("/run-sync")
@limiter.limit("2/hour")
def trigger_sync(request: Request, admin_key: str):
    if admin_key != settings.SECRET_KEY:
        return {"detail": "forbidden"}
    daily_sync_all_students()
    return {"detail": "sync triggered"}


@router.post("/run-notifications")
@limiter.limit("2/hour")
def trigger_notifications(request: Request, admin_key: str):
    if admin_key != settings.SECRET_KEY:
        return {"detail": "forbidden"}
    daily_notifications()
    return {"detail": "notifications triggered"}