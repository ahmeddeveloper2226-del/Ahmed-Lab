from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class StudyPlanTask(BaseModel):
    id: str
    day: date
    subject_slug: str
    subject_name: str
    lecture_id: str | None = None
    lecture_title: str | None = None
    estimated_minutes: int
    is_done: bool = False
    note: str | None = None  # short AI rationale, e.g. "exam-heavy subject, prioritized"


class WeeklyStudyPlan(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    uid: str
    week_start: date
    week_end: date
    generated_at: datetime
    model_used: str
    tasks: list[StudyPlanTask]
    summary_ar: str
    summary_en: str


class StudyPlanRegenerateRequest(BaseModel):
    force: bool = False
    extra_notes: str | None = Field(None, max_length=500)
