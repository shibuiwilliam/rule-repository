"""Placeholder migration to bridge gap between 019 and 021.

The original migration 020 was lost from version control. This no-op
placeholder restores the Alembic revision chain so that subsequent
migrations (021+) can apply.

Revision ID: 020
Revises: 019
"""

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op: original migration content is unknown."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
