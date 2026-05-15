"""Add body JSONB column for typed rule bodies.

Per PROJECT.md §6.3 and CLAUDE.md §14.3: rules carry a kind-specific
structured body (expression, state machine, definition, etc.).

Revision ID: 039
Revises: 038
"""

import sqlalchemy as sa
from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add body JSONB column to rules table."""
    op.add_column("rules", sa.Column("body", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove body column from rules table."""
    op.drop_column("rules", "body")
