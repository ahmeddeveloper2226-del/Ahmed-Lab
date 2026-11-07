"""
One-off script — run this manually, once, to make your own account an admin.

WHAT THIS DOES:
Firebase lets you attach small pieces of extra data ("custom claims") to a
user's account, which then show up inside their ID token every time they log
in. Your `dependencies.py` checks for a claim called `role` equal to
`"admin"` before allowing access to admin-only endpoints like
`POST /categories/`. This script is what actually SETS that claim on a real
account — nothing else in the app does this automatically, on purpose,
since granting admin access should never happen silently through normal
signup.

HOW TO RUN IT:
1. Make sure you've already signed up / logged into the app at least once
   with the phone number you want to make an admin — the account must
   already exist in Firebase before you can tag it.
2. Find that user's Firebase UID: open Firebase Console -> Authentication ->
   Users tab -> find the row with your phone number -> copy the "User UID"
   column value.
3. Run this script from your project root:
       python scripts/make_admin.py <paste-the-uid-here>
4. Log out and log back in on your actual phone/app afterward — the OLD
   token you already have does NOT contain the new claim. Custom claims
   only appear in a token generated AFTER the claim was set, so a fresh
   login is required for the change to actually take effect.
"""
import sys

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

from app.config import settings


def make_admin(uid: str) -> None:
    firebase_admin.initialize_app(credentials.Certificate(settings.firebase_credentials_path))

    firebase_auth.set_custom_user_claims(uid, {"role": "admin"})

    # Read the user back immediately, purely to confirm the claim actually
    # stuck — this is a genuine confirmation, not just "the call didn't crash".
    user_record = firebase_auth.get_user(uid)
    print(f"Done. {user_record.phone_number or user_record.email} is now an admin.")
    print(f"Current custom claims: {user_record.custom_claims}")
    print("Remember: log out and log back in on the app for this to take effect.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/make_admin.py <firebase-uid>")
        sys.exit(1)

    make_admin(sys.argv[1])