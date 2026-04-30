"""Add evaluations table for persistent per-rule evaluation records.

Replaces audit_log JSON parsing for analytics with a proper structured table.

Revision ID: 014
Revises: 013
Create Date: 2026-04-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluations",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scope", sa.String(500), nullable=True),
        sa.Column("input_type", sa.String(20), nullable=False, server_default="code"),
        sa.Column("model_id", sa.String(100), nullable=False, server_default="unknown"),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_evaluations_created_at", "evaluations", ["created_at"])
    op.create_index(
        "ix_evaluations_verdict_created",
        "evaluations",
        ["verdict", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("evaluations")
