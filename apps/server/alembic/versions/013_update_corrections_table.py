"""Add missing columns to corrections table and fix column types.

Revision ID: 013
Revises: 012
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing columns
    op.add_column(
        "corrections",
        sa.Column("delta_summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "corrections",
        sa.Column("affected_functions", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "corrections",
        sa.Column("lines_added", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "corrections",
        sa.Column("lines_removed", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "corrections",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Add project_id if not already present (migration 012 may have added it)
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'corrections' AND column_name = 'project_id'"
        )
    )
    if result.fetchone() is None:
        # Get default project ID
        default_project = conn.execute(sa.text("SELECT id FROM projects ORDER BY created_at LIMIT 1")).fetchone()
        default_id = str(default_project[0]) if default_project else None

        op.add_column(
            "corrections",
            sa.Column("project_id", sa.Uuid(), nullable=True),
        )
        if default_id:
            op.execute(f"UPDATE corrections SET project_id = '{default_id}'")
        op.create_foreign_key(
            "fk_corrections_project_id",
            "corrections",
            "projects",
            ["project_id"],
            ["id"],
        )
        op.create_index("ix_corrections_project_id", "corrections", ["project_id"])

    # Convert ARRAY columns to JSONB — must drop default first, alter type, then re-add default
    array_cols = {
        "file_paths": "text[]",
        "evaluation_ids": "uuid[]",
        "matched_rule_ids": "uuid[]",
    }
    for col, arr_type in array_cols.items():
        op.execute(f"ALTER TABLE corrections ALTER COLUMN {col} DROP DEFAULT")
        op.execute(
            f"ALTER TABLE corrections ALTER COLUMN {col} TYPE jsonb "
            f"USING to_jsonb(COALESCE({col}, ARRAY[]::{arr_type}))"
        )
        op.execute(f"ALTER TABLE corrections ALTER COLUMN {col} SET DEFAULT '[]'::jsonb")


def downgrade() -> None:
    op.drop_column("corrections", "updated_at")
    op.drop_column("corrections", "lines_removed")
    op.drop_column("corrections", "lines_added")
    op.drop_column("corrections", "affected_functions")
    op.drop_column("corrections", "delta_summary")
