"""
Per-lecture study tools, one pair of buttons on every lecture card:

  - Notes & rules          GET/PUT  /subjects/{enrollment}/lectures/{lecture}/notes
  - "If you understood,    GET      .../explain          (saved chat + summary)
     then explain" AI      POST     .../explain          (one chat turn)
                           POST     .../explain/summary  (finish & summarize)
                           DELETE   .../explain          (start over)

Everything is saved per lecture, so the student can reopen it any time.
"""
from fastapi import APIRouter, Depends, Request

from app.core.exceptions import MasarkError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.ai import (
    LectureExplainRequest, LectureExplainResponse, LectureExplainState,
    LectureExplainSummaryResponse, LectureNotesResponse, LectureNotesUpdate,
)
from app.services import firestore_service as db
from app.services.groq_service import lecture_explain_chat, lecture_explain_summary

router = APIRouter(prefix="/subjects/{enrollment_id}/lectures/{lecture_id}", tags=["lecture-study"])

# A runaway chat would otherwise grow forever and cost tokens on every turn.
_MAX_USER_MESSAGES = 80


def _load_context(uid: str, enrollment_id: str, lecture_id: str) -> tuple[dict, dict, str]:
    """Returns (enrollment, lecture, language). 404s if either isn't the user's."""
    enrollment = db.get_enrollment(uid, enrollment_id)
    if not enrollment:
        raise NotFoundError("Subject not found")
    lecture = db.get_lecture(uid, enrollment_id, lecture_id)
    if not lecture:
        raise NotFoundError("Lecture not found")
    profile = db.get_user(uid) or {}
    return enrollment, lecture, profile.get("language", "ar")


@router.get("/notes", response_model=LectureNotesResponse)
@limiter.limit("60/minute")
def get_notes(
    enrollment_id: str, lecture_id: str, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    _load_context(user.uid, enrollment_id, lecture_id)
    return db.get_lecture_notes(user.uid, enrollment_id, lecture_id)


@router.put("/notes", response_model=LectureNotesResponse)
@limiter.limit("60/minute")
def save_notes(
    enrollment_id: str, lecture_id: str, payload: LectureNotesUpdate, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    _load_context(user.uid, enrollment_id, lecture_id)
    return db.save_lecture_notes(user.uid, enrollment_id, lecture_id, payload.notes, payload.rules)


@router.get("/explain", response_model=LectureExplainState)
@limiter.limit("60/minute")
def get_explain(
    enrollment_id: str, lecture_id: str, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    _load_context(user.uid, enrollment_id, lecture_id)
    return db.get_lecture_explain(user.uid, enrollment_id, lecture_id)


@router.post("/explain", response_model=LectureExplainResponse)
@limiter.limit("15/minute")
def explain_turn(
    enrollment_id: str, lecture_id: str, payload: LectureExplainRequest, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    enrollment, lecture, lang = _load_context(user.uid, enrollment_id, lecture_id)
    history = db.get_lecture_explain(user.uid, enrollment_id, lecture_id)["messages"]
    if sum(1 for m in history if m["role"] == "user") >= _MAX_USER_MESSAGES:
        raise MasarkError("This chat is full. Start a new one to keep going.", status_code=429)

    reply = lecture_explain_chat(
        subject_name=enrollment.get("subject_name") or enrollment.get("subject_slug", ""),
        lecture_title=lecture.get("title", ""),
        history=history,
        message=payload.message,
        lang_hint=lang,
    )
    # Save only after the AI answered, so a failed call never leaves a lone
    # user message in the history.
    db.append_lecture_explain_message(user.uid, enrollment_id, lecture_id, "user", payload.message)
    db.append_lecture_explain_message(user.uid, enrollment_id, lecture_id, "model", reply)
    return LectureExplainResponse(reply=reply)


@router.post("/explain/summary", response_model=LectureExplainSummaryResponse)
@limiter.limit("6/minute")
def explain_summary(
    enrollment_id: str, lecture_id: str, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    enrollment, lecture, lang = _load_context(user.uid, enrollment_id, lecture_id)
    history = db.get_lecture_explain(user.uid, enrollment_id, lecture_id)["messages"]
    if not any(m["role"] == "user" for m in history):
        raise MasarkError("Explain the lecture to the AI first, then ask for the summary.", status_code=422)

    summary = lecture_explain_summary(
        subject_name=enrollment.get("subject_name") or enrollment.get("subject_slug", ""),
        lecture_title=lecture.get("title", ""),
        history=history,
        lang_hint=lang,
    )
    db.save_lecture_explain_summary(user.uid, enrollment_id, lecture_id, summary)
    return LectureExplainSummaryResponse(summary=summary)


@router.delete("/explain")
@limiter.limit("20/minute")
def reset_explain(
    enrollment_id: str, lecture_id: str, request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    _load_context(user.uid, enrollment_id, lecture_id)
    db.reset_lecture_explain(user.uid, enrollment_id, lecture_id)
    return {"detail": "reset"}