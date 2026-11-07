"""add chat_messages table

Revision ID: c1d4e8f2a6b9
Revises: b3e7f1a9c5d2
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d4e8f2a6b9'
down_revision: Union[str, Sequence[str], None] = 'b3e7f1a9c5d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    message_type_enum = sa.Enum('text', 'voice', 'system', name='messagetype')
    message_status_enum = sa.Enum('sent', 'delivered', 'read', name='messagestatus')

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('sender_id', sa.String(), nullable=True),
        sa.Column('receiver_id', sa.String(), nullable=False),
        sa.Column('message_type', message_type_enum, nullable=False),
        sa.Column('status', message_status_enum, nullable=False),
        sa.Column('content', sa.String(), nullable=True),
        sa.Column('audio_path', sa.String(), nullable=True),
        sa.Column('audio_duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_messages_order_id', 'chat_messages', ['order_id'])
    op.create_index('ix_chat_messages_created_at', 'chat_messages', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_chat_messages_created_at', table_name='chat_messages')
    op.drop_index('ix_chat_messages_order_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    sa.Enum(name='messagetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='messagestatus').drop(op.get_bind(), checkfirst=True)