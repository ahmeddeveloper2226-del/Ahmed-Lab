"""widen vendor_payout_accounts.account_number for encrypted storage

Revision ID: R8g2c5e9f1b4
Revises: Q7f1b4d8e0a3
Create Date: 2026-08-13

account_number now stores a Fernet-encrypted ciphertext (see
app/services/payout_encryption.py), which is meaningfully longer than a
raw IBAN/wallet number — String() defaults to a driver-dependent bounded
length that's too small for that. Switched to unbounded Text.
"""
from alembic import op
import sqlalchemy as sa

revision = "R8g2c5e9f1b4"
down_revision = "Q7f1b4d8e0a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "vendor_payout_accounts",
        "account_number",
        type_=sa.Text(),
        existing_type=sa.String(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "vendor_payout_accounts",
        "account_number",
        type_=sa.String(),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
