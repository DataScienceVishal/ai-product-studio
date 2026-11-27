"""requirements.source_document_id: refuse deleting a cited document, and index it (T-197)

Revision ID: 0014
Revises: 0013

The composite FK was ON DELETE CASCADE, so deleting one tender PDF silently wiped its requirements, drafts and
claims. It is now NO ACTION: the delete is refused while requirements cite the document. NO ACTION rather than
RESTRICT because RESTRICT is checked immediately, before the other cascade paths have run, so deleting a pack or a
tenant (which cascades to both source_documents and requirements) could fail on ordering. NO ACTION is checked at the
end of the statement, when the requirements are already gone, so pack and tenant deletes still work.
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = ['tenant_id', 'source_document_id']
_REF = ['source_documents.tenant_id', 'source_documents.id']


def upgrade() -> None:
    op.drop_constraint('fk_requirements_document', 'requirements', type_='foreignkey')
    op.create_foreign_key('fk_requirements_document', 'requirements', 'source_documents', _COLS,
                          ['tenant_id', 'id'], ondelete='NO ACTION')
    op.create_index('ix_requirements_tenant_source_document', 'requirements', _COLS)


def downgrade() -> None:
    op.drop_index('ix_requirements_tenant_source_document', table_name='requirements')
    op.drop_constraint('fk_requirements_document', 'requirements', type_='foreignkey')
    op.create_foreign_key('fk_requirements_document', 'requirements', 'source_documents', _COLS,
                          ['tenant_id', 'id'], ondelete='CASCADE')
