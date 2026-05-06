"""Add regulatory_severity to rules.

Regulatory severity (NONE/GUIDANCE/FINE/CRIMINAL) is independent of the
operational severity (LOW/MEDIUM/HIGH/CRITICAL). It captures the penalty
band for regulatory violations and affects prioritization.

Backfill: existing rules default to NONE.

Revision ID: 025
Revises: 024
"""

import sqlalchemy as sa
from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add regulatory_severity to rules."""
    op.add_column(
        "rules",
        sa.Column("regulatory_severity", sa.String(20), nullable=False, server_default="NONE"),
    )


def downgrade() -> None:
    """Remove regulatory_severity from rules."""
    op.drop_column("rules", "regulatory_severity")
