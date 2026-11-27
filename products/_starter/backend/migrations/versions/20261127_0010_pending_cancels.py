"""pending_cancels: durable to-do for a subscription a takeover replaced and still has to be cancelled (T-175)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-27 15:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('pending_cancels',
                    sa.Column('id', sa.Uuid(), nullable=False),
                    sa.Column('tenant_id', sa.Uuid(), nullable=True),
                    sa.Column('provider', sa.String(length=40), nullable=False),
                    sa.Column('ref', sa.String(length=255), nullable=False),
                    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('last_error', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('provider', 'ref', name='uq_pending_cancels_provider_ref'))
    op.create_index(op.f('ix_pending_cancels_tenant_id'), 'pending_cancels', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pending_cancels_tenant_id'), table_name='pending_cancels')
    op.drop_table('pending_cancels')
