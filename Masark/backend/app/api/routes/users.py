from fastapi import APIRouter, Depends, Request

from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.models.user import OnboardingRequest, UserProfile, UserProfileUpdate
from app.services import firestore_service as db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
@limiter.limit("60/minute")
def get_me(request: Request, user: CurrentUser = Depends(get_current_user)):
    profile = db.get_user(user.uid) or {}
    return UserProfile(
        uid=user.uid,
        email=user.email,
        full_name=profile.get("full_name", ""),
        photo_url=profile.get("photo_url"),
        age=profile.get("age", 0),
        phone_number=profile.get("phone_number", ""),
        academic_level=profile.get("academic_level", "secondary"),
        academic_year=profile.get("academic_year", "year_1"),
        availability=profile.get("availability", {}),
        theme=profile.get("theme", "light"),
        language=profile.get("language", "ar"),
        fcm_tokens=profile.get("fcm_tokens", []),
        onboarding_completed=profile.get("onboarding_completed", False),
        created_at=profile.get("created_at"),
        updated_at=profile.get("updated_at"),
    )


@router.post("/me/onboarding")
@limiter.limit("10/minute")
def complete_onboarding(
    payload: OnboardingRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    data = payload.model_dump()
    data["onboarding_completed"] = True
    data["email"] = user.email
    db.create_or_update_user(user.uid, data)
    return {"detail": "onboarding saved"}


@router.patch("/me")
@limiter.limit("30/minute")
def update_profile(
    payload: UserProfileUpdate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if updates:
        db.create_or_update_user(user.uid, updates)
    return {"detail": "profile updated"}


@router.post("/me/fcm-token")
@limiter.limit("10/minute")
def register_fcm_token(
    request: Request,
    token: str,
    user: CurrentUser = Depends(get_current_user),
):
    db.add_fcm_token(user.uid, token)
    return {"detail": "token registered"}