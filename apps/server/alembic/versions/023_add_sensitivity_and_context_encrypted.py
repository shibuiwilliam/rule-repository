"""Add sensitivity field to rules and context_encrypted to evaluations.

Rule.sensitivity (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) drives LLM provider
routing and log retention policy. RESTRICTED rules are not sent to external LLMs.

EvaluationRecordModel.context_encrypted stores the evaluation context as
AES-GCM encrypted bytes, replacing plaintext context storage for PII safety.

Backfill: existing rules default to INTERNAL; existing evaluations have
context_encrypted=NULL (only new evaluations populate it).

Revision ID: 023
Revises: 022
"""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add sensitivity to rules and context_encrypted to evaluations."""
    op.add_column(
        "rules",
        sa.Column("sensitivity", sa.String(20), nullable=False, server_default="INTERNAL"),
    )
    op.add_column(
        "evaluations",
        sa.Column("context_encrypted", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    """Remove sensitivity and context_encrypted columns."""
    op.drop_column("evaluations", "context_encrypted")
    op.drop_column("rules", "sensitivity")
