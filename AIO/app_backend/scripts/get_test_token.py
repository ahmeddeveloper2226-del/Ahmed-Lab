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
        timeout=15,
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
