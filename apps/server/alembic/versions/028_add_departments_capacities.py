"""Add departments, capacity_assignments, and rule_ownerships tables.

Phase 7 Stream B: Department and Capacity Model.

Revision ID: 028
Revises: 027
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create department and capacity tables."""
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("parent_id", sa.Uuid, sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("head_user_id", sa.String(255), nullable=False, server_default=""),
        sa.Column("cost_center", sa.String(100), nullable=True),
        sa.Column("locale", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "capacity_assignments",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "department_id",
            sa.Uuid,
            sa.ForeignKey("departments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("capacity", sa.String(20), nullable=False),
        sa.Column("rule_filter", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "rule_ownerships",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "rule_id",
            sa.Uuid,
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "owner_department_id",
            sa.Uuid,
            sa.ForeignKey("departments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("delegated_to", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop department and capacity tables."""
    op.drop_table("rule_ownerships")
    op.drop_table("capacity_assignments")
    op.drop_table("departments")
