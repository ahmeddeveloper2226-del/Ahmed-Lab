"""
Encrypts/decrypts VendorPayoutAccount.account_number at rest — this is a
real bank account or mobile wallet number, not something that should
ever be stored or logged in plain text.

Uses Fernet (symmetric, authenticated encryption) from `cryptography`,
keyed by settings.payout_encryption_key. Deliberately fails loudly
(raises at call time, not silently) if that key isn't configured —
storing financial account numbers unencrypted because a key was
forgotten is a much worse failure than the app refusing to save one.
"""
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from ..config import settings


def _get_fernet() -> Fernet:
    if not settings.payout_encryption_key:
        raise RuntimeError(
            "PAYOUT_ENCRYPTION_KEY is not configured — refusing to store or read "
            "vendor payout account numbers unencrypted. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(settings.payout_encryption_key.encode())


def encrypt_account_number(raw_account_number: str) -> str:
    return _get_fernet().encrypt(raw_account_number.encode()).decode()


def decrypt_account_number(encrypted_account_number: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted_account_number.encode()).decode()
    except InvalidToken:
        # Either the stored value predates encryption being turned on, or
        # the encryption key was rotated without re-encrypting existing
        # rows. Either way, silently returning garbage would be worse
        # than a clear error — a masked/garbled account number is the
        # kind of bug that only gets noticed when a payout goes to the
        # wrong place.
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "تعذر قراءة بيانات الحساب البنكي — يرجى إعادة إدخالها.",
        )


def mask_account_number(raw_account_number: str) -> str:
    """For display only — never send the full decrypted number back to
    the panel, just enough to confirm which account is on file."""
    if len(raw_account_number) < 4:
        return "••••"
    return f"••••{raw_account_number[-4:]}"
