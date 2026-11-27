"""signoffs.voided_at: a reopened pack voids its sign-off but keeps the row (audit; exports reference it) (T-192)

Revision ID: 0019
Revises: 0018
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('signoffs', sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('signoffs', 'voided_at')
