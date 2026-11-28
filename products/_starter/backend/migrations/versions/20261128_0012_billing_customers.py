"""billing_customers: every provider customer a tenant has had, so account deletion removes them all (T-181)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-28 10:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('billing_customers',
                    sa.Column('id', sa.Uuid(), nullable=False),
                    sa.Column('tenant_id', sa.Uuid(), nullable=False),
                    sa.Column('provider', sa.String(length=40), nullable=False),
                    sa.Column('customer_ref', sa.String(length=255), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('provider', 'customer_ref', name='uq_billing_customers_provider_ref'))
    op.create_index(op.f('ix_billing_customers_tenant_id'), 'billing_customers', ['tenant_id'], unique=False)
    # Existing subscriptions already know their one customer.
    op.execute("INSERT INTO billing_customers (id, tenant_id, provider, customer_ref, created_at) "
               "SELECT gen_random_uuid(), tenant_id, provider, provider_customer, now() FROM subscriptions "
               "WHERE provider_customer IS NOT NULL AND tenant_id IS NOT NULL ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_index(op.f('ix_billing_customers_tenant_id'), table_name='billing_customers')
    op.drop_table('billing_customers')
