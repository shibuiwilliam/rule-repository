"""Add agent governance tables: profiles, exception requests, negotiations, sessions.

Phase 6b: Autonomous Agent Governance Loop (PROJECT_ENHANCE.md §Enhancement 2).

Revision ID: 019
Revises: 018
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent governance tables."""
    # -- agent_profiles --
    op.create_table(
        "agent_profiles",
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("capabilities", JSONB, nullable=False, server_default="[]"),
        sa.Column("trust_level", sa.String(20), nullable=False, server_default="untrusted"),
        sa.Column("compliance_rate_30d", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("violation_patterns", JSONB, nullable=False, server_default="{}"),
        sa.Column("strength_areas", JSONB, nullable=False, server_default="[]"),
        sa.Column("weakness_areas", JSONB, nullable=False, server_default="[]"),
        sa.Column("can_propose_rules", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_vote_on_proposals", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_auto_fix_severity", sa.String(20), nullable=False, server_default="none"),
        sa.Column("personalized_rule_weights", JSONB, nullable=False, server_default="{}"),
        sa.Column("suppressed_rule_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("mastery_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("agent_id"),
    )

    # -- agent_exception_requests --
    op.create_table(
        "agent_exception_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "agent_id", sa.String(255), sa.ForeignKey("agent_profiles.agent_id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("proposed_exception", sa.Text(), nullable=False),
        sa.Column("evidence", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_exception_requests_agent_id", "agent_exception_requests", ["agent_id"])
    op.create_index("ix_agent_exception_requests_rule_id", "agent_exception_requests", ["rule_id"])

    # -- agent_negotiations --
    op.create_table(
        "agent_negotiations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "agent_id", sa.String(255), sa.ForeignKey("agent_profiles.agent_id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_verdict", sa.String(30), nullable=False),
        sa.Column("counter_argument", sa.Text(), nullable=False),
        sa.Column("proposed_action", sa.String(30), nullable=False),
        sa.Column("resolution", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_negotiations_agent_id", "agent_negotiations", ["agent_id"])
    op.create_index("ix_agent_negotiations_rule_id", "agent_negotiations", ["rule_id"])

    # -- governance_sessions --
    op.create_table(
        "governance_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("context_ref", sa.String(500), nullable=False, server_default=""),
        sa.Column("agent_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("shared_verdicts", JSONB, nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop agent governance tables."""
    op.drop_table("governance_sessions")

    op.drop_index("ix_agent_negotiations_rule_id", table_name="agent_negotiations")
    op.drop_index("ix_agent_negotiations_agent_id", table_name="agent_negotiations")
    op.drop_table("agent_negotiations")

    op.drop_index("ix_agent_exception_requests_rule_id", table_name="agent_exception_requests")
    op.drop_index("ix_agent_exception_requests_agent_id", table_name="agent_exception_requests")
    op.drop_table("agent_exception_requests")

    op.drop_table("agent_profiles")
