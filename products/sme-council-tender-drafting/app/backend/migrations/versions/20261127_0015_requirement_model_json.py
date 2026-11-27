"""requirements.model_json and flags (T-188): the model's original item and the code's cross-check flags

Revision ID: 0015
Revises: 0014
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('requirements', sa.Column('model_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('requirements', sa.Column('flags', postgresql.ARRAY(sa.String(length=30)), nullable=False,
                                            server_default='{}'))


def downgrade() -> None:
    op.drop_column('requirements', 'flags')
    op.drop_column('requirements', 'model_json')
