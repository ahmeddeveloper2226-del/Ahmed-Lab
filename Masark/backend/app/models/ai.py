from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRole(str):
    USER = "user"
    MODEL = "model"


class ChatMessage(BaseModel):
    role: str  # "user" | "model"
    content: str
    created_at: datetime | None = None


class ProcrastinationSessionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ProcrastinationSessionResponse(BaseModel):
    reply: str
    session_id: str
    suggested_actions: list[str] = Field(default_factory=list)


class SubjectQARequest(BaseModel):
    subject_slug: str
    question: str = Field(..., min_length=1, max_length=2000)


class SubjectQAResponse(BaseModel):
    answer: str
    subject_slug: str


# --- Per-lecture study tools -------------------------------------------------
class LectureNotesUpdate(BaseModel):
    notes: str = Field("", max_length=20000)
    rules: str = Field("", max_length=20000)


class LectureNotesResponse(BaseModel):
    notes: str = ""
    rules: str = ""
    updated_at: datetime | None = None


class LectureExplainRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class LectureExplainResponse(BaseModel):
    reply: str


class LectureExplainState(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    summary: str = ""
    summary_at: datetime | None = None


class LectureExplainSummaryResponse(BaseModel):
    summary: str