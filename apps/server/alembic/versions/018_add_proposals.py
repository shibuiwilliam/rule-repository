"""Add proposals, proposal_comments, and notifications tables for collaborative governance.

Phase 6a: Collaborative Governance Workflow (PROJECT_ENHANCE.md §Enhancement 1).

Revision ID: 018
Revises: 017
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create proposals, proposal_comments, and notifications tables."""
    # -- proposals --
    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("proposal_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("author_id", sa.String(255), nullable=False, server_default="system"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("change_spec", JSONB, nullable=False, server_default="{}"),
        sa.Column("target_rule_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("conflict_analysis", JSONB, nullable=True),
        sa.Column("impact_preview", JSONB, nullable=True),
        sa.Column("required_approvers", JSONB, nullable=False, server_default="[]"),
        sa.Column("approval_votes", JSONB, nullable=False, server_default="[]"),
        sa.Column("enacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposals_project_id", "proposals", ["project_id"])
    op.create_index("ix_proposals_status", "proposals", ["status"])
    op.create_index("ix_proposals_author_id", "proposals", ["author_id"])

    # -- proposal_comments --
    op.create_table(
        "proposal_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.String(255), nullable=False, server_default="system"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("comment_type", sa.String(20), nullable=False, server_default="comment"),
        sa.Column("suggestion_spec", JSONB, nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposal_comments_proposal_id", "proposal_comments", ["proposal_id"])

    # -- notifications --
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("proposals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_proposal_id", "notifications", ["proposal_id"])


def downgrade() -> None:
    """Drop notifications, proposal_comments, and proposals tables."""
    op.drop_index("ix_notifications_proposal_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_proposal_comments_proposal_id", table_name="proposal_comments")
    op.drop_table("proposal_comments")

    op.drop_index("ix_proposals_author_id", table_name="proposals")
    op.drop_index("ix_proposals_status", table_name="proposals")
    op.drop_index("ix_proposals_project_id", table_name="proposals")
    op.drop_table("proposals")
