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


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration support)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    """Add classification column with default 'internal'."""
    if not _column_exists("rules", "classification"):
        op.add_column(
            "rules",
            sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
        )
    if not _column_exists("evaluations", "classification"):
        op.add_column(
            "evaluations",
            sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
        )
    if not _column_exists("audit_log", "classification"):
        op.add_column(
            "audit_log",
            sa.Column("classification", sa.String(20), nullable=False, server_default="internal"),
        )


def downgrade() -> None:
    """Remove classification columns."""
    op.drop_column("audit_log", "classification")
    op.drop_column("evaluations", "classification")
    op.drop_column("rules", "classification")
