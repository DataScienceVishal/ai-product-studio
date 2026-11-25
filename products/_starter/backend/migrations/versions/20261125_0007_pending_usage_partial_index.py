"""partial index for pending AI usage rows

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-25 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Used by the abandoned-reservation sweep and the in-flight count (both filter model = 'pending').
    op.create_index('ix_ai_usage_pending', 'ai_usage', ['tenant_id', 'created_at'], unique=False,
                    postgresql_where=sa.text("model = 'pending'"))


def downgrade() -> None:
    op.drop_index('ix_ai_usage_pending', table_name='ai_usage', postgresql_where=sa.text("model = 'pending'"))
