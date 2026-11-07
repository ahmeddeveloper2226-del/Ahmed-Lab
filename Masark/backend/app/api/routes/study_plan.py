"""
Weekly study plan (خطة الدراسة):

  GET    /study-plan/current          this week's plan, or null if none yet
  POST   /study-plan/generate         build (or rebuild with force=true) this week's plan
  PATCH  /study-plan/tasks/{task_id}  tick / untick one task (?is_done=true|false)

Plans live at users/{uid}/study_plans/{weekStartISO}. Weeks start on Saturday
(same convention as progress_service). Task ids are "<weekStartISO>_<n>", so the
PATCH route can find the right plan document without an extra lookup.
"""

from datetime import date, datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, Request

from app.core.config import get_settings
from app.core.exceptions import MasarkError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.study_plan import StudyPlanRegenerateRequest, WeeklyStudyPlan
from app.models.user import WeeklyAvailability
from app.services import firestore_service as db
from app.services.groq_service import generate_study_plan
from app.services.progress_service import _week_bounds

log = structlog.get_logger()
settings = get_settings()

router = APIRouter(prefix="/study-plan", tags=["study-plan"])

_MAX_PENDING_PER_SUBJECT = 15   # keeps the prompt (and the token bill) bounded
_MAX_COMPLETED_HINTS = 8
_MAX_TASKS_PER_DAY = 8


def _today() -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Africa/Cairo")).date()
    except Exception:  # tzdata missing (common on Windows) -> server-local date
        return date.today()


def _subjects_remaining(uid: str) -> list[dict]:
    enrollments = db.list_enrollments(uid)
    lectures = db.list_all_lectures_for_user(uid, enrollments)
    by_enrollment: dict[str, list[dict]] = {}
    for lec in lectures:
        by_enrollment.setdefault(lec["enrollment_id"], []).append(lec)

    out = []
    for enr in enrollments:
        lecs = sorted(by_enrollment.get(enr["id"], []), key=lambda l: l.get("order", 0))
        pending = [l for l in lecs if not l.get("is_completed")]
        if not pending:
            continue
        done = [l for l in lecs if l.get("is_completed")]
        out.append({
            "subject_slug": enr["subject_slug"],
            "subject_name": enr.get("subject_name") or enr["subject_slug"],
            "remaining": len(pending),
            "pending_lectures": [
                {"id": l["id"], "title": l.get("title", "")}
                for l in pending[:_MAX_PENDING_PER_SUBJECT]
            ],
            "completed_lecture_titles": [l.get("title", "") for l in done[-_MAX_COMPLETED_HINTS:]],
        })
    return out


def _clean_tasks(
    raw_tasks: list, subjects: list[dict], week_start: date,
    availability: WeeklyAvailability, week_start_iso: str,
) -> list[dict]:
    """The model's output is untrusted: drop anything outside the week, on an
    off day, for an unknown subject, or that reuses a lecture."""
    names = {s["subject_slug"]: s["subject_name"] for s in subjects}
    titles = {
        (s["subject_slug"], str(l["id"])): l["title"]
        for s in subjects for l in s["pending_lectures"]
    }
    week_end = week_start + timedelta(days=6)
    used: set[tuple[str, str]] = set()
    per_day: dict[str, int] = {}
    tasks: list[dict] = []

    for t in raw_tasks if isinstance(raw_tasks, list) else []:
        if not isinstance(t, dict):
            continue
        try:
            day = date.fromisoformat(str(t.get("day"))[:10])
            minutes = int(t.get("estimated_minutes") or 45)
        except (ValueError, TypeError):
            continue
        slug = t.get("subject_slug")
        if slug not in names or not (week_start <= day <= week_end):
            continue
        if day.weekday() in availability.off_days:
            continue
        if per_day.get(day.isoformat(), 0) >= _MAX_TASKS_PER_DAY:
            continue

        lecture_id = str(t["lecture_id"]) if t.get("lecture_id") is not None else None
        if lecture_id is not None:
            key = (slug, lecture_id)
            if key not in titles or key in used:
                continue  # hallucinated or duplicated lecture
            used.add(key)

        per_day[day.isoformat()] = per_day.get(day.isoformat(), 0) + 1
        tasks.append({
            "id": f"{week_start_iso}_{len(tasks)}",
            "day": day.isoformat(),
            "subject_slug": slug,
            "subject_name": names[slug],
            "lecture_id": lecture_id,
            "lecture_title": titles.get((slug, lecture_id)) if lecture_id else None,
            "estimated_minutes": max(10, min(minutes, 240)),
            "is_done": False,
            "note": (str(t["note"])[:160] if t.get("note") else None),
        })
    return tasks


@router.get("/current", response_model=WeeklyStudyPlan | None)
@limiter.limit("60/minute")
def get_current_plan(request: Request, user: CurrentUser = Depends(get_current_user)):
    week_start, _ = _week_bounds(_today())
    return db.get_study_plan(user.uid, week_start.isoformat())  # None -> JSON null


@router.post("/generate", response_model=WeeklyStudyPlan)
@limiter.limit("5/minute")
def generate_plan(
    request: Request,
    payload: StudyPlanRegenerateRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
):
    payload = payload or StudyPlanRegenerateRequest()
    today = _today()
    week_start, week_end = _week_bounds(today)
    week_start_iso = week_start.isoformat()

    if not payload.force:
        existing = db.get_study_plan(user.uid, week_start_iso)
        if existing:
            return existing

    profile = db.get_user(user.uid) or {}
    availability = WeeklyAvailability(**(profile.get("availability") or {}))
    subjects = _subjects_remaining(user.uid)
    if not subjects:
        raise MasarkError("No unfinished lectures to plan. Add a subject or sync your lectures first.", status_code=422)

    # Plan only the days that are left: starting from Saturday on a Thursday
    # would schedule work in the past.
    plan_from = max(week_start, today)

    result = generate_study_plan(
        student_name=profile.get("full_name", "student"),
        academic_level=profile.get("academic_level", "secondary"),
        subjects_remaining=subjects,
        availability=availability,
        week_start=plan_from,
        extra_notes=payload.extra_notes,
    )

    tasks = _clean_tasks(result.get("tasks"), subjects, plan_from, availability, week_start_iso)
    # _clean_tasks bounds days to plan_from..plan_from+6; clamp to the real week end.
    tasks = [t for t in tasks if date.fromisoformat(t["day"]) <= week_end]
    if not tasks:
        log.error("study_plan.no_valid_tasks", uid=user.uid)
        raise MasarkError("Could not build a valid plan right now, please retry.", status_code=503)

    plan = {
        "id": week_start_iso,
        "uid": user.uid,
        "week_start": week_start_iso,
        "week_end": week_end.isoformat(),
        "generated_at": datetime.now(timezone.utc),
        "model_used": settings.GROQ_MODEL,
        "tasks": tasks,
        "summary_ar": str(result.get("summary_ar") or "")[:300],
        "summary_en": str(result.get("summary_en") or "")[:300],
    }
    db.save_study_plan(user.uid, week_start_iso, plan)
    return plan


@router.patch("/tasks/{task_id}")
@limiter.limit("120/minute")
def toggle_task(
    task_id: str, is_done: bool, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    week_start_iso = task_id.split("_", 1)[0]
    try:
        date.fromisoformat(week_start_iso)
    except ValueError:
        raise NotFoundError("Task not found")
    plan = db.get_study_plan(user.uid, week_start_iso)
    if not plan or not any(t["id"] == task_id for t in plan.get("tasks", [])):
        raise NotFoundError("Task not found")
    db.update_study_plan_task(user.uid, week_start_iso, task_id, is_done)
    return {"id": task_id, "is_done": is_done}