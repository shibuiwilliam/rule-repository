"""Add discovery tables — scans and candidates for automatic rule discovery.

Revision ID: 005
Revises: 004
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_scans",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("sources", JSONB(), nullable=False, server_default="{}"),
        sa.Column("repository", sa.String(255), nullable=True),
        sa.Column("candidates_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "discovery_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "scan_id",
            sa.Uuid(),
            sa.ForeignKey("discovery_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("modality", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("scope", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("tags", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_evidence", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "created_rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_discovery_candidates_scan_id", "discovery_candidates", ["scan_id"])
    op.create_index("ix_discovery_candidates_status", "discovery_candidates", ["status"])


def downgrade() -> None:
    op.drop_table("discovery_candidates")
    op.drop_table("discovery_scans")
