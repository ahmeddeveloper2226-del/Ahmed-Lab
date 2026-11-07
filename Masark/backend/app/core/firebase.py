"""
Firebase Admin SDK bootstrap.

Provides a single, lazily-initialized Firestore client and exposes the
Firebase Auth admin module for verifying ID tokens issued to the frontend
(both Google sign-in and email/password go through Firebase Auth, so the
backend only ever has to verify one kind of token).
"""
from __future__ import annotations

import structlog
import firebase_admin
from firebase_admin import credentials, auth, firestore

from app.core.config import get_settings

log = structlog.get_logger()

_app: firebase_admin.App | None = None
_db: firestore.Client | None = None


def init_firebase() -> firebase_admin.App:
    global _app
    if _app is not None:
        return _app

    settings = get_settings()
    try:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _app = firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
        log.info("firebase.initialized", project=settings.FIREBASE_PROJECT_ID)
    except FileNotFoundError:
        log.error(
            "firebase.credentials_missing",
            path=settings.FIREBASE_CREDENTIALS_PATH,
            hint="Download the service-account JSON from Firebase Console > "
            "Project Settings > Service Accounts and place it at that path "
            "(or point FIREBASE_CREDENTIALS_PATH at it). Never commit it.",
        )
        raise
    return _app


def get_db() -> firestore.Client:
    global _db
    if _db is None:
        init_firebase()
        _db = firestore.client()
    return _db


def verify_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token sent by the frontend. Raises
    firebase_admin.auth exceptions on failure (invalid, expired, revoked)."""
    init_firebase()
    return auth.verify_id_token(id_token, check_revoked=True)


auth_admin = auth
