"""Add federation tables — cross-project rule federation.

Revision ID: 007
Revises: 006
Create Date: 2026-04-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rule_federations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("rule_federations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_scope", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_rule_federations_parent_id", "rule_federations", ["parent_id"])
    op.create_index("ix_rule_federations_level", "rule_federations", ["level"])

    op.create_table(
        "rule_federation_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "federation_id",
            sa.Uuid(),
            sa.ForeignKey("rule_federations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "override_parent_rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_federation_memberships_federation_id",
        "rule_federation_memberships",
        ["federation_id"],
    )
    op.create_unique_constraint(
        "uq_rule_federation_membership",
        "rule_federation_memberships",
        ["rule_id", "federation_id"],
    )


def downgrade() -> None:
    op.drop_table("rule_federation_memberships")
    op.drop_table("rule_federations")
