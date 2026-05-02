"""Add context column to rules table.

Context captures the surrounding document text, section headers, and broader
document information that explains why a rule was created — distinct from
rationale (intent/purpose). This enables better evaluation accuracy and
traceability back to source documents.

Revision ID: 021
Revises: 020
"""

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add context column to rules table."""
    op.add_column("rules", sa.Column("context", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    """Remove context column from rules table."""
    op.drop_column("rules", "context")
