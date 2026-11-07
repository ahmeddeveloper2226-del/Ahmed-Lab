"""
Password hashing for Shop.password_hash — backs the store management
panel's login (see store_management_router.py). Deliberately stdlib-only
(hashlib.pbkdf2_hmac), matching the rest of this codebase's pattern of not
pulling in bcrypt/passlib for its simpler internal panels (compare
verify_admin_panel_secret's plain string comparison in dependencies.py).
PBKDF2-SHA256 with a random salt and a real iteration count is a
significant step up from that while still needing zero new dependencies.
"""
import hashlib
import hmac
import secrets

_ITERATIONS = 200_000
_ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    """Returns "salt_hex$hash_hex" — self-contained, no separate salt column needed."""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${derived.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """
    Constant-time comparison via hmac.compare_digest — a shop with no
    password_hash set yet (stored is None) always fails, rather than
    raising, so callers can treat "not configured" and "wrong password"
    identically (no password oracle either way).
    """
    if not stored or "$" not in stored:
        return False
    salt, expected_hex = stored.split("$", 1)
    try:
        derived = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    except ValueError:
        return False
    return hmac.compare_digest(derived.hex(), expected_hex)