"""Add rule kind column for evaluation strategy dispatch.

Adds the ``kind`` column to the ``rules`` table with a default of
``'normative'`` so all existing rules continue to use LLM-as-Judge
evaluation without migration issues.

See IMPROVEMENT.md Proposal 3 for the rationale.

Revision ID: 034
Revises: 033
"""

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "rules",
        sa.Column("kind", sa.String(20), nullable=False, server_default="normative"),
    )
    op.create_index("ix_rules_kind", "rules", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_rules_kind", table_name="rules")
    op.drop_column("rules", "kind")
