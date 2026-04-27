"""Add playground tables — rule test cases for the playground.

Revision ID: 008
Revises: 007
Create Date: 2026-04-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rule_test_cases",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sample_input", sa.Text(), nullable=False),
        sa.Column("input_type", sa.String(20), nullable=False, server_default="code"),
        sa.Column("expected_verdict", sa.String(30), nullable=False),
        sa.Column("last_result", sa.String(30), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("passing", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_rule_test_cases_rule_id", "rule_test_cases", ["rule_id"])


def downgrade() -> None:
    op.drop_table("rule_test_cases")
