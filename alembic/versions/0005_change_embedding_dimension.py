"""change chunk embedding dimension from 8 to 1536

Revision ID: 0005_change_embedding_dimension
Revises: 0004_add_chunk_embedding
Create Date: 2026-08-05

Downgrade intentionally clears embeddings before changing the dimension.
Vector values cannot be safely converted between these dimensions.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_change_embedding_dimension"
down_revision: Union[str, Sequence[str], None] = "0004_add_chunk_embedding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE document_chunks SET embedding = NULL "
            "WHERE embedding IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE document_chunks "
            "ALTER COLUMN embedding TYPE vector(1536) "
            "USING NULL::vector(1536)"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE document_chunks SET embedding = NULL "
            "WHERE embedding IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE document_chunks "
            "ALTER COLUMN embedding TYPE vector(8) "
            "USING NULL::vector(8)"
        )
    )
