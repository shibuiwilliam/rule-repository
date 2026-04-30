"""Add maturity_level and accuracy tracking to rules table.

Revision ID: 015
Revises: 014
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add maturity_level, false_positive_count, true_positive_count to rules."""
    op.add_column(
        "rules",
        sa.Column("maturity_level", sa.String(20), nullable=False, server_default="experimental"),
    )
    op.add_column(
        "rules",
        sa.Column("false_positive_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "rules",
        sa.Column("true_positive_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Backfill: existing APPROVED/EFFECTIVE rules are already proven (they were enforcing)
    op.execute(sa.text("UPDATE rules SET maturity_level = 'proven' WHERE status IN ('APPROVED', 'EFFECTIVE')"))


def downgrade() -> None:
    """Remove maturity columns."""
    op.drop_column("rules", "true_positive_count")
    op.drop_column("rules", "false_positive_count")
    op.drop_column("rules", "maturity_level")
