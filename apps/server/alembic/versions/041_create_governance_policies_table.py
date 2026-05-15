"""Create governance_policies table for ABAC.

Per PROJECT.md §6.9 and CLAUDE.md §14.10: attribute-based access
control policies with domain x action x principal resolution.

Revision ID: 041
Revises: 040
"""

import sqlalchemy as sa
from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create governance_policies table."""
    op.create_table(
        "governance_policies",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain", sa.String(100), nullable=True),
        sa.Column("org_unit", sa.String(255), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("principals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("effect", sa.String(10), nullable=False, server_default="allow"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_governance_policies_domain", "governance_policies", ["domain"])
    op.create_index("ix_governance_policies_action", "governance_policies", ["action"])


def downgrade() -> None:
    """Drop governance_policies table."""
    op.drop_table("governance_policies")
