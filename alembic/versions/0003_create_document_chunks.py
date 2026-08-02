"""create document chunks table

Revision ID: 0003_create_document_chunks
Revises: 0002_create_document_pages
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_create_document_chunks"
down_revision: Union[str, Sequence[str], None] = "0002_create_document_pages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "page_number > 0",
            name="ck_document_chunks_page_number_positive",
        ),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name="ck_document_chunks_index_non_negative",
        ),
        sa.CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_document_chunks_content_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk_index",
        ),
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
