"""
Auth routes.

Actual sign-in (Google popup, or email/password) happens entirely on the
FRONTEND via the Firebase JS SDK — the backend never sees passwords. Once
the frontend has a Firebase ID token it calls /auth/session here to:
  - verify the token is valid,
  - create the user's Firestore profile stub on first sign-in,
  - return whether onboarding is still needed.

/auth/logout revokes the user's Firebase refresh tokens server-side, which
is the correct way to force sign-out everywhere (the frontend's local
`signOut()` alone would not do that).
"""

from fastapi import APIRouter, Depends, Request
from firebase_admin import auth as fb_auth

from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.services import firestore_service as db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session")
@limiter.limit("20/minute")
def bootstrap_session(request: Request, user: CurrentUser = Depends(get_current_user)):
    profile = db.get_user(user.uid)
    if profile is None:
        profile = db.create_or_update_user(user.uid, {
            "uid": user.uid,
            "email": user.email,
            "onboarding_completed": False,
            "theme": "light",
            "language": "ar",
            "fcm_tokens": [],
        })
    return {
        "uid": user.uid,
        "email": user.email,
        "onboarding_completed": bool(profile.get("onboarding_completed")),
        "theme": profile.get("theme", "light"),
        "language": profile.get("language", "ar"),
    }


@router.post("/logout")
@limiter.limit("20/minute")
def logout(request: Request, user: CurrentUser = Depends(get_current_user)):
    fb_auth.revoke_refresh_tokens(user.uid)
    return {"detail": "signed out everywhere"}