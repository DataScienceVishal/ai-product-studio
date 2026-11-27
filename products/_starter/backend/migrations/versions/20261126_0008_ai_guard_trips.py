"""persist the AI model-guard trip

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-26 23:50:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_guard_trips',
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('tripped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('model', sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint('fingerprint'),
    )


def downgrade() -> None:
    op.drop_table('ai_guard_trips')
