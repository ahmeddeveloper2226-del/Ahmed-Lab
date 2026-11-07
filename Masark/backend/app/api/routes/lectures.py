from fastapi import APIRouter, Depends, Request

from app.core.exceptions import NotFoundError
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.lecture import LectureUpdate, MonthBucket, OverallProgress
from app.services import firestore_service as db
from app.services.progress_service import build_home_calendar, compute_overall_progress

router = APIRouter(tags=["lectures"])


@router.get("/home/calendar", response_model=list[MonthBucket])
@limiter.limit("60/minute")
def get_home_calendar(request: Request, user: CurrentUser = Depends(get_current_user)):
    profile = db.get_user(user.uid) or {}
    return build_home_calendar(user.uid, language=profile.get("language", "ar"))


@router.get("/home/progress", response_model=OverallProgress)
@limiter.limit("60/minute")
def get_overall_progress(request: Request, user: CurrentUser = Depends(get_current_user)):
    return compute_overall_progress(user.uid)


@router.patch("/subjects/{enrollment_id}/lectures/{lecture_id}")
@limiter.limit("60/minute")
def update_lecture_status(
    enrollment_id: str,
    lecture_id: str,
    payload: LectureUpdate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    enrollment = db.get_enrollment(user.uid, enrollment_id)
    if not enrollment:
        raise NotFoundError("Subject not found")

    updates = payload.model_dump(exclude_none=True)
    db.update_lecture(user.uid, enrollment_id, lecture_id, updates)

    if "is_completed" in updates:
        lectures = db.list_lectures(user.uid, enrollment_id)
        completed = sum(1 for l in lectures if l.get("is_completed"))
        db.update_enrollment(user.uid, enrollment_id, {"completed_lectures": completed})

    return {"detail": "updated"}