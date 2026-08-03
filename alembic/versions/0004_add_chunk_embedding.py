"""add embedding vector to document chunks

Revision ID: 0004_add_chunk_embedding
Revises: 0003_create_document_chunks
Create Date: 2026-08-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.app.embedding import EMBEDDING_DIMENSION


revision: str = "0004_add_chunk_embedding"
down_revision: Union[str, Sequence[str], None] = "0003_create_document_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.execute(
        sa.text(
            "ALTER TABLE document_chunks "
            f"ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIMENSION})"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    )
