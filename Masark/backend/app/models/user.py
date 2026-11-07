from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class AcademicLevel(str, Enum):
    PREP = "prep"          # إعدادي
    SECONDARY = "secondary"  # ثانوي


class AcademicYear(str, Enum):
    YEAR_1 = "year_1"  # أولى
    YEAR_2 = "year_2"  # تانية
    YEAR_3 = "year_3"  # تالتة


class WeeklyAvailability(BaseModel):
    """Hours the student says they can study, per day of week (0=Mon..6=Sun),
    plus which days are completely off. Feeds the Groq study-plan prompt."""
    weekday_hours: float = Field(3, ge=0, le=16)
    weekend_hours: float = Field(5, ge=0, le=16)
    off_days: list[int] = Field(default_factory=list, description="0=Mon .. 6=Sun")


class OnboardingRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=80)
    age: int = Field(..., ge=8, le=25)
    phone_number: str = Field(..., min_length=8, max_length=20)
    academic_level: AcademicLevel
    academic_year: AcademicYear
    availability: WeeklyAvailability = WeeklyAvailability()

    @field_validator("phone_number")
    @classmethod
    def egyptian_phone(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit() or ch == "+")
        if len(digits) < 8:
            raise ValueError("Phone number looks too short")
        return digits


class UserProfile(BaseModel):
    uid: str
    full_name: str
    email: EmailStr | None = None
    photo_url: str | None = None
    age: int
    phone_number: str
    academic_level: AcademicLevel
    academic_year: AcademicYear
    availability: WeeklyAvailability
    theme: str = "light"        # "light" | "dark"
    language: str = "ar"        # "ar" | "en"
    fcm_tokens: list[str] = Field(default_factory=list)
    onboarding_completed: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    """Every field optional — students can edit their profile later."""
    full_name: str | None = Field(None, min_length=2, max_length=80)
    age: int | None = Field(None, ge=8, le=25)
    phone_number: str | None = None
    academic_level: AcademicLevel | None = None
    academic_year: AcademicYear | None = None
    availability: WeeklyAvailability | None = None
    theme: str | None = None
    language: str | None = None