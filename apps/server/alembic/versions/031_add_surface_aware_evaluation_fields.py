"""Add surface-aware fields to evaluations table.

Phase 8: Surface Abstraction — adds surface, actor_kind, actor_identifier,
locale to evaluations.

See CLAUDE.md §14.2.4.

Revision ID: 031
Revises: 030
"""

import sqlalchemy as sa
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add surface and actor fields to evaluations table."""
    # surface: which surface was evaluated
    op.add_column(
        "evaluations",
        sa.Column(
            "surface",
            sa.String(30),
            nullable=False,
            server_default="code",
        ),
    )

    # actor_kind: human, system, or agent
    op.add_column(
        "evaluations",
        sa.Column(
            "actor_kind",
            sa.String(20),
            nullable=False,
            server_default="system",
        ),
    )

    # actor_identifier: stable identifier for the actor
    op.add_column(
        "evaluations",
        sa.Column("actor_identifier", sa.Text, nullable=True),
    )

    # locale: locale of the evaluated subject
    op.add_column(
        "evaluations",
        sa.Column(
            "locale",
            sa.String(10),
            nullable=False,
            server_default="en",
        ),
    )

    # Backfill: existing evaluations get surface='code',
    # actor_kind='agent' where agent_id is set, else 'system'
    op.execute("""
        UPDATE evaluations
        SET surface = COALESCE(input_type, 'code'),
            actor_kind = CASE
                WHEN agent_id IS NOT NULL THEN 'agent'
                ELSE 'system'
            END,
            actor_identifier = agent_id
        WHERE surface = 'code' AND actor_kind = 'system'
    """)

    # Index for surface-based queries
    op.create_index(
        "ix_evaluations_surface",
        "evaluations",
        ["surface"],
    )


def downgrade() -> None:
    """Remove surface-aware columns from evaluations table."""
    op.drop_index("ix_evaluations_surface", table_name="evaluations")
    op.drop_column("evaluations", "locale")
    op.drop_column("evaluations", "actor_identifier")
    op.drop_column("evaluations", "actor_kind")
    op.drop_column("evaluations", "surface")
