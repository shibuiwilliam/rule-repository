"""Add applicable_subject_types, jurisdiction, legal_force, review_cadence to rules.

Phase 7b: These fields enable subject-aware rule selection and multi-domain
rule management. Existing rules are backfilled with sensible defaults.

Revision ID: 026
Revises: 025
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add subject and jurisdiction fields to rules."""
    # applicable_subject_types: which subject types this rule applies to
    op.add_column(
        "rules",
        sa.Column(
            "applicable_subject_types",
            JSONB,
            nullable=False,
            server_default='["code_change"]',
        ),
    )

    # jurisdiction: geographic/legal jurisdiction (e.g., "jp", "us", "eu", "global")
    op.add_column(
        "rules",
        sa.Column("jurisdiction", sa.String(50), nullable=False, server_default="global"),
    )

    # legal_force: statutory, regulatory, contractual, policy, guideline
    op.add_column(
        "rules",
        sa.Column("legal_force", sa.String(20), nullable=False, server_default="policy"),
    )

    # review_cadence: how often this rule should be reviewed (e.g., "annual", "quarterly")
    op.add_column(
        "rules",
        sa.Column("review_cadence", sa.String(20), nullable=True),
    )

    # subject_type on evaluations: records what type of subject was evaluated
    op.add_column(
        "evaluations",
        sa.Column("subject_type", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    """Remove subject and jurisdiction fields."""
    op.drop_column("evaluations", "subject_type")
    op.drop_column("rules", "review_cadence")
    op.drop_column("rules", "legal_force")
    op.drop_column("rules", "jurisdiction")
    op.drop_column("rules", "applicable_subject_types")
