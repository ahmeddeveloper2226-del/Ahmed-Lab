from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class Lecture(BaseModel):
    id: str
    enrollment_id: str
    uid: str
    subject_slug: str
    title: str
    lecture_url: str | None = None  # deep link back to the source platform
    uploaded_on: date | None = None  # date scraped/entered; drives week bucketing
    order: int = 0
    is_completed: bool = False
    homework_done: bool | None = None  # None = no homework tracked yet for this lecture
    completed_at: datetime | None = None
    created_at: datetime | None = None
    has_notes: bool = False  # student wrote notes/rules for this lecture
    has_explain: bool = False  # student has an explain-to-AI chat for this lecture


class LectureUpdate(BaseModel):
    is_completed: bool | None = None
    homework_done: bool | None = None


class WeekBucket(BaseModel):
    """One week inside a month, in the home tab's drill-down table."""
    week_index: int  # 1-based within the month
    start_date: date
    end_date: date
    subjects: dict[str, list[Lecture]] = Field(default_factory=dict)  # subject_slug -> lectures


class MonthBucket(BaseModel):
    month_key: str  # "2026-09"
    label_ar: str
    label_en: str
    weeks: list[WeekBucket]
    total_lectures: int
    completed_lectures: int


class SubjectProgress(BaseModel):
    subject_slug: str
    subject_name: str
    color_accent: str
    total: int
    completed: int
    remaining: int
    percent: float
    status: str  # "on_track" (>=50%) | "behind" (<50%) -> drives green/red chart


class OverallProgress(BaseModel):
    total: int
    completed: int
    remaining: int
    percent: float
    status: str
    subjects: list[SubjectProgress]