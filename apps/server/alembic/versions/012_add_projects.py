"""Add projects table and project_id FK to resource tables.

Revision ID: 012
Revises: 011
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"

# Tables that get a project_id column
TABLES_WITH_PROJECT_ID = [
    "rules",
    "documents",
    "discovery_scans",
    "corrections",
    "rule_set_snapshots",
    "enforcement_policies",
    "alerts",
]


def upgrade() -> None:
    """Create projects table, add project_id FK to resource tables."""
    # 1. Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Insert the default project for existing data
    op.execute(
        sa.text(
            f"INSERT INTO projects (id, name, description) VALUES "
            f"('{DEFAULT_PROJECT_ID}'::uuid, 'Default Project', 'Auto-created for pre-existing data')"
        )
    )

    # 3. Add project_id as NULLABLE first, backfill, then set NOT NULL
    for table in TABLES_WITH_PROJECT_ID:
        op.add_column(table, sa.Column("project_id", sa.Uuid(), nullable=True))

        # Backfill
        op.execute(sa.text(f"UPDATE {table} SET project_id = '{DEFAULT_PROJECT_ID}'::uuid WHERE project_id IS NULL"))

        # Set NOT NULL
        op.alter_column(table, "project_id", nullable=False)

        # Add FK constraint
        op.create_foreign_key(
            f"fk_{table}_project_id",
            table,
            "projects",
            ["project_id"],
            ["id"],
        )

        # Add index
        op.create_index(f"ix_{table}_project_id", table, ["project_id"])


def downgrade() -> None:
    """Remove project_id columns and projects table."""
    for table in reversed(TABLES_WITH_PROJECT_ID):
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_constraint(f"fk_{table}_project_id", table, type_="foreignkey")
        op.drop_column(table, "project_id")

    op.drop_table("projects")
