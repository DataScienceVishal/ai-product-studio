"""index invitations(email): accepting an invite revokes other tenants' pending invites for that address

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-27 12:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_invitations_email'), 'invitations', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invitations_email'), table_name='invitations')
