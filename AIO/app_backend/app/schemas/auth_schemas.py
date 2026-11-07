from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserSessionResponse(BaseModel):
    """
    Returned after a successful login (any provider — phone, Google, Apple).
    This is the ONLY place a client learns their own account state, so it
    intentionally includes email_verified — the app uses this to decide
    whether to prompt the user to add/verify an email next.
    """
    id: str
    phone_number: str | None
    email: str | None
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SendEmailCodeRequest(BaseModel):
    email: EmailStr


class SendEmailCodeResponse(BaseModel):
    message: str
    expires_in_seconds: int


class VerifyEmailCodeRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyEmailCodeResponse(BaseModel):
    email: str
    email_verified: bool