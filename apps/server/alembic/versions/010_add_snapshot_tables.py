"""Add rule_set_snapshots and rule_set_deployments tables.

Revision ID: 010
Revises: 009
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rule_set_snapshots",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "scope_filter",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("rule_snapshot", JSONB(), nullable=False),
        sa.Column("rule_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=False,
            server_default="system",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "rule_set_deployments",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("rule_set_snapshots.id"),
            nullable=False,
        ),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "deployed_by",
            sa.String(255),
            nullable=False,
            server_default="system",
        ),
        sa.Column(
            "deployed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_rule_set_deployments_env_active",
        "rule_set_deployments",
        ["environment", "active"],
    )


def downgrade() -> None:
    op.drop_index("ix_rule_set_deployments_env_active", table_name="rule_set_deployments")
    op.drop_table("rule_set_deployments")
    op.drop_table("rule_set_snapshots")
