"""Add following_examples and violation_examples columns to rules table.

These JSONB array columns store examples of activities that follow or violate
a rule, extracted from source documents or entered manually. Examples improve
LLM evaluation accuracy by providing concrete reference points.

Revision ID: 022
Revises: 021
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add following_examples and violation_examples to rules."""
    op.add_column("rules", sa.Column("following_examples", JSONB, nullable=False, server_default="[]"))
    op.add_column("rules", sa.Column("violation_examples", JSONB, nullable=False, server_default="[]"))


def downgrade() -> None:
    """Remove example columns from rules."""
    op.drop_column("rules", "violation_examples")
    op.drop_column("rules", "following_examples")
