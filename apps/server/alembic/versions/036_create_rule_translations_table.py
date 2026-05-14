"""Create rule_translations table for multilingual rule linking.

Stores translation relationships between rules in different languages,
with equivalence scores from periodic verification runs.

See IMPROVEMENT.md Proposal 8.

Revision ID: 036
Revises: 035
"""

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        "rule_translations",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "source_rule_id",
            sa.Uuid,
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_rule_id",
            sa.Uuid,
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("target_language", sa.String(10), nullable=False),
        sa.Column("equivalence_score", sa.Float, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(100), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_rule_id", "target_rule_id", name="uq_rule_translation_pair"),
    )


def downgrade() -> None:
    op.drop_table("rule_translations")
