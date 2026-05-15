"""Add language column for multilingual rule support.

Per PROJECT.md §6.8 and CLAUDE.md §14.8: rules carry an explicit
language field (ISO 639-1, default 'en').

Revision ID: 040
Revises: 039
"""

import sqlalchemy as sa
from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add language column to rules table."""
    op.add_column("rules", sa.Column("language", sa.String(10), nullable=False, server_default="en"))


def downgrade() -> None:
    """Remove language column from rules table."""
    op.drop_column("rules", "language")
