"""
One-off script — generates a REAL Firebase ID token you can paste into
FastAPI's /docs "Authorize" button, without needing to actually receive an
SMS or run the Flutter app at all.

HOW THIS WORKS:
Firebase phone/Google/Apple sign-in normally happens client-side (inside a
real app, on a real device) because it needs things like reCAPTCHA/device
attestation that don't make sense to replicate from a bare script. Instead,
this script uses a technique built for exactly this situation — backend
testing:

1. Uses the Firebase ADMIN SDK (server-side, already set up in this
   project) to mint a "custom token" for a made-up test user ID. This is a
   privileged, admin-only operation — nothing a real client can do.
2. Exchanges that custom token for a real ID token via Firebase's public
   REST API (`signInWithCustomToken`) — the same kind of token a real
   logged-in user's phone/Google/Apple sign-in would produce.
3. Prints that ID token, which you paste into /docs's Authorize button.

HONEST LIMITATION: because this bypasses the phone OTP flow entirely
(rather than actually verifying a phone number), the resulting token does
NOT carry a `phone_number` claim the way a real phone sign-in token would.
This is fine for testing /me, /me/addresses, /categories, etc. — but if you
specifically want to test that /auth/session correctly pulls a phone number
out of the token (the fix we made earlier), that part still needs a real
test via the actual Flutter app with the +201234567890 / 123456 test number
you set up in Firebase Console. This script covers everything else.

SETUP REQUIRED BEFORE RUNNING:
1. Firebase Console -> Project Settings -> General tab -> find "Web API Key"
   under your app's config, copy it.
2. Add it to your .env file:
       FIREBASE_WEB_API_KEY=your-copied-key-here
3. pip install requests (if not already installed)

USAGE:
    python scripts/get_test_token.py
    python scripts/get_test_token.py my-custom-test-uid
"""
import sys

import firebase_admin
import requests
from firebase_admin import credentials
from firebase_admin import auth as firebase_auth

from app.config import settings


def get_test_id_token(test_uid: str) -> str:
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(settings.firebase_credentials_path))

    if not settings.firebase_web_api_key:
        raise RuntimeError(
            "FIREBASE_WEB_API_KEY is not set in your .env file. "
            "Get it from Firebase Console -> Project Settings -> General -> Web API Key."
        )

    custom_token = firebase_auth.create_custom_token(test_uid)

    response = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={settings.firebase_web_api_key}",
        json={
            "token": custom_token.decode("utf-8"),
            "returnSecureToken": True,
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"Firebase REST API call failed: {response.status_code} {response.text}")

    return response.json()["idToken"]


if __name__ == "__main__":
    test_uid = sys.argv[1] if len(sys.argv) > 1 else "test-user-001"

    id_token = get_test_id_token(test_uid)

    print(f"\nGenerated a real Firebase ID token for uid='{test_uid}':\n")
    print(id_token)
    print(
        "\nPaste this into FastAPI's /docs 'Authorize' button "
        "(just the token itself, no need to type 'Bearer ').\n"
        "Note: this token has no phone_number claim (see script docstring for why)."
    )