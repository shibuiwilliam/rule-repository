"""Add feedback tables — corrections and clarity_score for correction feedback loop.

Revision ID: 006
Revises: 005
Create Date: 2026-04-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "corrections",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("original_diff", sa.Text(), nullable=False),
        sa.Column("corrected_diff", sa.Text(), nullable=False),
        sa.Column("file_paths", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("repository", sa.String(255), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("evaluation_ids", sa.ARRAY(sa.Uuid()), server_default="{}"),
        sa.Column("analysis_type", sa.String(30), nullable=True),
        sa.Column("matched_rule_ids", sa.ARRAY(sa.Uuid()), server_default="{}"),
        sa.Column("candidate_statement", sa.Text(), nullable=True),
        sa.Column("candidate_modality", sa.String(20), nullable=True),
        sa.Column("candidate_severity", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "created_rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_corrections_status", "corrections", ["status"])
    op.create_index("ix_corrections_created_at", "corrections", ["created_at"])

    # Add clarity_score to rules table
    op.add_column("rules", sa.Column("clarity_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("rules", "clarity_score")
    op.drop_table("corrections")
