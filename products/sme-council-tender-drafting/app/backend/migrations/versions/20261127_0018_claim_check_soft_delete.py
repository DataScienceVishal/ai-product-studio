"""claim check and soft delete (T-190): drafts.check_sha256/checked_at, source_documents.deleted_at

An evidence document delete keeps the row and its passages (appendix and audit), so the (tenant, sha256) uniqueness
applies to live documents only: the same file can be uploaded again after a delete.

Revision ID: 0018
Revises: 0017
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('drafts', sa.Column('check_sha256', sa.String(length=64), nullable=True))
    op.add_column('drafts', sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('source_documents', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint('uq_source_documents_tenant_sha256', 'source_documents', type_='unique')
    op.create_index('uq_source_documents_tenant_sha256', 'source_documents', ['tenant_id', 'sha256'], unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    # Soft-deleted rows may share a hash with a live one; they were deleted, so remove them before restoring the constraint.
    op.execute("DELETE FROM source_documents WHERE deleted_at IS NOT NULL")
    op.drop_index('uq_source_documents_tenant_sha256', table_name='source_documents')
    op.create_unique_constraint('uq_source_documents_tenant_sha256', 'source_documents', ['tenant_id', 'sha256'])
    op.drop_column('source_documents', 'deleted_at')
    op.drop_column('drafts', 'checked_at')
    op.drop_column('drafts', 'check_sha256')
