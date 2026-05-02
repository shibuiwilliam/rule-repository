"""Add marketplace tables: rule_packages, package_rules, package_subscriptions, composition_conflicts.

Phase 6c: Rule Marketplace & Interoperability.

Revision ID: 020
Revises: 019
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create marketplace tables."""
    # -- rule_packages --
    op.create_table(
        "rule_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("publisher_id", sa.String(255), nullable=False, server_default="system"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("license", sa.String(100), nullable=False, server_default="MIT"),
        sa.Column("homepage", sa.String(500), nullable=True),
        sa.Column("changelog", JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("adoption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", "publisher_id", name="uq_package_name_version_publisher"),
    )

    # -- package_rules --
    op.create_table(
        "package_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("rule_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("package_rule_id", sa.String(100), nullable=False),
        sa.Column("test_cases", JSONB, nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_package_rules_package_id", "package_rules", ["package_id"])
    op.create_index("ix_package_rules_rule_id", "package_rules", ["rule_id"])

    # -- package_subscriptions --
    op.create_table(
        "package_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("rule_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_constraint", sa.String(50), nullable=False, server_default="*"),
        sa.Column("auto_update", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("composition_policy", JSONB, nullable=False, server_default="{}"),
        sa.Column("installed_version", sa.String(50), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_package_subscriptions_project_id", "package_subscriptions", ["project_id"])
    op.create_index("ix_package_subscriptions_package_id", "package_subscriptions", ["package_id"])

    # -- composition_conflicts --
    op.create_table(
        "composition_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_a_id", sa.Uuid(), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_b_id", sa.Uuid(), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("package_a_id", sa.Uuid(), sa.ForeignKey("rule_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("package_b_id", sa.Uuid(), sa.ForeignKey("rule_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conflict_type", sa.String(30), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("resolution", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_composition_conflicts_project_id", "composition_conflicts", ["project_id"])


def downgrade() -> None:
    """Drop marketplace tables."""
    op.drop_index("ix_composition_conflicts_project_id", table_name="composition_conflicts")
    op.drop_table("composition_conflicts")

    op.drop_index("ix_package_subscriptions_package_id", table_name="package_subscriptions")
    op.drop_index("ix_package_subscriptions_project_id", table_name="package_subscriptions")
    op.drop_table("package_subscriptions")

    op.drop_index("ix_package_rules_rule_id", table_name="package_rules")
    op.drop_index("ix_package_rules_package_id", table_name="package_rules")
    op.drop_table("package_rules")

    op.drop_table("rule_packages")
