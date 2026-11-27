"""requirements: unique (tenant_id, pack_id, seq) (T-198 F7). Renumbers any existing duplicates first.

Revision ID: 0017
Revises: 0016
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0017'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only rows that share a seq within a pack move: they are numbered after the pack's current maximum.
    op.execute("""
        UPDATE requirements r SET seq = m.mx + d.rn
        FROM (SELECT id, row_number() OVER (PARTITION BY tenant_id, pack_id ORDER BY id) AS rn
              FROM (SELECT id, tenant_id, pack_id, row_number() OVER (PARTITION BY tenant_id, pack_id, seq
                                                                                  ORDER BY id) AS dup
                    FROM requirements) x WHERE dup > 1) d
        JOIN (SELECT tenant_id, pack_id, max(seq) AS mx FROM requirements GROUP BY tenant_id, pack_id) m
          ON TRUE
        WHERE r.id = d.id AND m.tenant_id = r.tenant_id AND m.pack_id = r.pack_id
    """)
    op.create_unique_constraint('uq_requirements_pack_seq', 'requirements', ['tenant_id', 'pack_id', 'seq'])


def downgrade() -> None:
    op.drop_constraint('uq_requirements_pack_seq', 'requirements', type_='unique')
