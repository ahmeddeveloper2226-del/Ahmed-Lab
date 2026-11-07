"""
AI routes for المواد tab's two assistants:
  - /ai/procrastination : "تراكم" coach, remembers past sessions
  - /ai/subject-qa      : per-subject Q&A tutor
Both are rate-limited more strictly than normal CRUD routes since every
call costs a Groq API call.
"""

from fastapi import APIRouter, Depends, Request

from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.ai import (
    ProcrastinationSessionRequest, ProcrastinationSessionResponse,
    SubjectQARequest, SubjectQAResponse,
)
from app.services import firestore_service as db
from app.services.groq_service import procrastination_chat, subject_qa

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/procrastination", response_model=ProcrastinationSessionResponse)
@limiter.limit("10/minute")
def procrastination_endpoint(
    payload: ProcrastinationSessionRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    history = db.get_procrastination_history(user.uid)
    reply, suggestions = procrastination_chat(history=history, message=payload.message)

    db.append_procrastination_message(user.uid, "user", payload.message)
    db.append_procrastination_message(user.uid, "model", reply)

    return ProcrastinationSessionResponse(reply=reply, session_id=user.uid, suggested_actions=suggestions)


@router.post("/subject-qa", response_model=SubjectQAResponse)
@limiter.limit("15/minute")
def subject_qa_endpoint(
    payload: SubjectQARequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    enrollments = {e["subject_slug"]: e for e in db.list_enrollments(user.uid)}
    subject_name = enrollments.get(payload.subject_slug, {}).get("subject_name", payload.subject_slug)

    history = db.get_subject_qa_history(user.uid, payload.subject_slug)
    answer = subject_qa(subject_name=subject_name, history=history, question=payload.question)

    db.append_subject_qa_message(user.uid, payload.subject_slug, "user", payload.question)
    db.append_subject_qa_message(user.uid, payload.subject_slug, "model", answer)

    return SubjectQAResponse(answer=answer, subject_slug=payload.subject_slug)