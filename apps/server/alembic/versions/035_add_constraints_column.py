"""Add constraints column to rules table.

Proposal 9 (Hybrid Evaluation Architecture): stores structured deterministic
constraints as a JSONB array on each rule.  When present, the deterministic
evaluator runs *before* the LLM, potentially skipping the LLM call entirely.

Revision ID: 035
Revises: 034
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add constraints JSONB column to rules table."""
    op.add_column(
        "rules",
        sa.Column(
            "constraints",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """Remove constraints column."""
    op.drop_column("rules", "constraints")
