"""Add classification column to rules, evaluations, and audit_log tables.

Phase 7 Stream C: Classification and Multi-Tenancy.

Revision ID: 029
Revises: 028
"""

import sqlalchemy as sa
from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add classification column with default 'internal'."""
    op.add_column(
        "rules",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )
    op.add_column(
        "evaluations",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )
    op.add_column(
        "audit_log",
        sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
    )


def downgrade() -> None:
    """Remove classification columns."""
    op.drop_column("audit_log", "classification")
    op.drop_column("evaluations", "classification")
    op.drop_column("rules", "classification")
