"""Add draft_rule_proposals table for correction-to-rule flywheel.

Revision ID: 016
Revises: 015
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create draft_rule_proposals table."""
    op.create_table(
        "draft_rule_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("modality", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("scope", JSONB, nullable=False, server_default="[]"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_correction_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("cluster_size", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "created_rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_draft_rule_proposals_project_id", "draft_rule_proposals", ["project_id"])
    op.create_index("ix_draft_rule_proposals_status", "draft_rule_proposals", ["status"])


def downgrade() -> None:
    """Drop draft_rule_proposals table."""
    op.drop_index("ix_draft_rule_proposals_status", table_name="draft_rule_proposals")
    op.drop_index("ix_draft_rule_proposals_project_id", table_name="draft_rule_proposals")
    op.drop_table("draft_rule_proposals")
