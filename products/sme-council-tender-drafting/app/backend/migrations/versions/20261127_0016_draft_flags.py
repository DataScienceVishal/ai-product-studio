"""drafts.outside_ids and flags (T-189): citations outside the retrieved set, and what the code did to the length

Revision ID: 0016
Revises: 0015
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0016'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('drafts', sa.Column('outside_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'))
    op.add_column('drafts', sa.Column('flags', postgresql.ARRAY(sa.String(length=30)), nullable=False,
                                      server_default='{}'))


def downgrade() -> None:
    op.drop_column('drafts', 'flags')
    op.drop_column('drafts', 'outside_ids')
