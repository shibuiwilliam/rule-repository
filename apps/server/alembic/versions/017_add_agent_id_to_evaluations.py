"""Add agent_id to evaluations table for per-agent performance tracking.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add agent_id column and index to evaluations."""
    op.add_column("evaluations", sa.Column("agent_id", sa.String(100), nullable=True))
    op.create_index("ix_evaluations_agent_id", "evaluations", ["agent_id"])


def downgrade() -> None:
    """Remove agent_id from evaluations."""
    op.drop_index("ix_evaluations_agent_id", table_name="evaluations")
    op.drop_column("evaluations", "agent_id")
