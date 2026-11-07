from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceMode(str, Enum):
    PLATFORM = "platform"  # fetched from one of the 6 partner platforms
    MANUAL = "manual"      # student enters lectures/dates by hand


class PlatformKey(str, Enum):
    BASSTHALK = "bassthalk"
    CSA = "csa"
    SMART_ACADEMY = "smart_academy"
    EDNUVA = "ednuva"
    EDUACT = "eduact"
    FULLMARK = "fullmark"


class PlatformInfo(BaseModel):
    key: PlatformKey
    name_ar: str
    name_en: str
    base_url: str
    logo_url: str | None = None


class TeacherOrPack(BaseModel):
    """A pack or a teacher page found on a partner platform for a subject."""
    id: str
    name: str
    subject_slug: str
    platform: PlatformKey
    url: str
    thumbnail_url: str | None = None
    kind: str = Field("pack", description="'pack' or 'teacher'")


class ManualLectureInput(BaseModel):
    title: str
    uploaded_on: datetime | None = None
    order: int = 0


class SubjectEnrollmentRequest(BaseModel):
    """What the client sends while a student is adding one subject during
    onboarding or later from المواد."""
    subject_name: str
    subject_slug: str
    source_mode: SourceMode
    platform: PlatformKey | None = None
    teacher_or_pack_id: str | None = None
    teacher_or_pack_url: str | None = None
    manual_lectures: list[ManualLectureInput] = Field(default_factory=list)
    # Lecture ids/titles the student says they *already* finished before
    # joining Masark, so progress starts correct instead of at zero.
    already_completed_lecture_ids: list[str] = Field(default_factory=list)


class SubjectEnrollment(BaseModel):
    id: str
    uid: str
    subject_name: str
    subject_slug: str
    source_mode: SourceMode
    platform: PlatformKey | None = None
    teacher_or_pack_id: str | None = None
    teacher_or_pack_url: str | None = None
    total_lectures: int = 0
    completed_lectures: int = 0
    color_accent: str = "#2DD4BF"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_synced_at: datetime | None = None

    @property
    def progress_percent(self) -> float:
        if self.total_lectures == 0:
            return 0.0
        return round(100 * self.completed_lectures / self.total_lectures, 1)
