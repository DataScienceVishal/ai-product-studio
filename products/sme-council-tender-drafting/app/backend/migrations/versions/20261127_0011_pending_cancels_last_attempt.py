"""pending_cancels.last_attempt_at: when the last cancel attempt ran, for the sweep's backoff and operator triage (T-176)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-27 18:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pending_cancels', sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('pending_cancels', 'last_attempt_at')
