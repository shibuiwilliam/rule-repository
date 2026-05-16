"""Add applies_to JSONB column to rules table.

The ORM model defines an ``applies_to`` column (RR-003: Formal applicability)
that was never added by a migration. This adds it so the schema matches.

Revision ID: 042
Revises: 041
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _column_exists("rules", "applies_to"):
        op.add_column(
            "rules",
            sa.Column(
                "applies_to",
                JSONB(),
                nullable=False,
                server_default=(
                    '{"artifact_types": ["code_diff"], "artifact_schema_ref": null, "triggering_events": []}'
                ),
            ),
        )


def downgrade() -> None:
    op.drop_column("rules", "applies_to")
