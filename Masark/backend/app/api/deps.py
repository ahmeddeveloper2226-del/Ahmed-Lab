"""Shared FastAPI dependencies beyond auth (see core/security.py)."""
from __future__ import annotations

from fastapi import Depends, HTTPException

from app.core.security import CurrentUser, get_current_user
from app.services import firestore_service as db


async def require_onboarded_user(user: CurrentUser = Depends(get_current_user)) -> tuple[CurrentUser, dict]:
    """Use on any route that needs a fully onboarded profile (i.e. almost
    everything except /users/me/onboarding itself)."""
    profile = db.get_user(user.uid)
    if not profile or not profile.get("onboarding_completed"):
        raise HTTPException(status_code=428, detail="Onboarding not completed")
    return user, profile
