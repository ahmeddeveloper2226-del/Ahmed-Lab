from pydantic import BaseModel, Field
from datetime import datetime


class UserProfileResponse(BaseModel):
    id: str
    full_name: str | None
    phone_number: str | None
    email: str | None
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """
    Deliberately does NOT include phone_number or email — those are only
    ever set through the verified auth flows (Firebase phone/Google/Apple,
    or the email verification endpoints in auth_router.py). Letting a user
    change them directly here would bypass verification entirely.
    """
    full_name: str = Field(..., min_length=1, max_length=100)


class AddressResponse(BaseModel):
    id: str
    label: str | None
    full_address: str
    lat: float | None
    lng: float | None
    is_default: bool

    class Config:
        from_attributes = True


class AddressCreateRequest(BaseModel):
    label: str | None = Field(None, max_length=50)
    full_address: str = Field(..., min_length=5, max_length=500)
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    is_default: bool = False


class AddressUpdateRequest(BaseModel):
    label: str | None = Field(None, max_length=50)
    full_address: str | None = Field(None, min_length=5, max_length=500)
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)