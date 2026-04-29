"""Add content_text column to documents for full-text search.

Revision ID: 011
Revises: 010
Create Date: 2026-04-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_text", sa.Text(), nullable=True))
    # GIN index for PostgreSQL full-text search on filename + content_text
    op.execute(
        """
        CREATE INDEX ix_documents_fulltext
        ON documents
        USING GIN (to_tsvector('english', coalesce(filename, '') || ' ' || coalesce(content_text, '')))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_fulltext")
    op.drop_column("documents", "content_text")
