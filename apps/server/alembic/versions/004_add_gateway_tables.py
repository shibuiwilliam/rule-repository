"""Add gateway tables — enforcement policies and gateway evaluations.

Revision ID: 004
Revises: 003
Create Date: 2026-04-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enforcement_policies",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_source", sa.String(100), nullable=False),
        sa.Column("event_type_pattern", sa.String(255), nullable=False),
        sa.Column("rule_scope", sa.String(255), nullable=True),
        sa.Column("rule_modality_filter", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("rule_severity_min", sa.String(20), nullable=True),
        sa.Column("evaluation_mode", sa.String(20), nullable=False, server_default="'preflight'"),
        sa.Column("context_extraction_prompt", sa.Text(), nullable=True),
        sa.Column("response_actions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("on_deny", sa.String(20), nullable=False, server_default="'notify'"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "gateway_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "policy_id",
            sa.Uuid(),
            sa.ForeignKey("enforcement_policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_source", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("event_payload", JSONB(), nullable=False),
        sa.Column("normalized_context", JSONB(), nullable=False),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("rule_ids_evaluated", sa.ARRAY(sa.Uuid()), server_default="{}"),
        sa.Column("violations", JSONB(), nullable=True),
        sa.Column("actions_taken", JSONB(), nullable=False, server_default="[]"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_gateway_evaluations_policy_id", "gateway_evaluations", ["policy_id"])
    op.create_index("ix_gateway_evaluations_created_at", "gateway_evaluations", ["created_at"])


def downgrade() -> None:
    op.drop_table("gateway_evaluations")
    op.drop_table("enforcement_policies")
