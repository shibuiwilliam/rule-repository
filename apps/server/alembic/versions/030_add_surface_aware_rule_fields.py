"""Add surface-aware fields to rules table.

Phase 8: Surface Abstraction — adds applies_to_surfaces, norm_tier,
norm_authority, locale, statement_translations, tech_scope, org_scope.

See CLAUDE.md §14.2.4.

Revision ID: 030
Revises: 029
"""

import sqlalchemy as sa
from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add surface-aware columns to rules table."""
    # applies_to_surfaces: which surfaces this rule can be evaluated against
    op.add_column(
        "rules",
        sa.Column(
            "applies_to_surfaces",
            sa.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
    )

    # norm_tier: position in the norm-lineage hierarchy
    op.add_column(
        "rules",
        sa.Column(
            "norm_tier",
            sa.String(30),
            nullable=False,
            server_default="OPERATIONAL_RULE",
        ),
    )

    # norm_authority: citation of upstream authority
    op.add_column(
        "rules",
        sa.Column("norm_authority", sa.Text, nullable=True),
    )

    # locale: canonical locale of the rule statement
    op.add_column(
        "rules",
        sa.Column("locale", sa.String(10), nullable=False, server_default="en"),
    )

    # statement_translations: locale → translated statement
    op.add_column(
        "rules",
        sa.Column(
            "statement_translations",
            sa.JSON,
            nullable=False,
            server_default="{}",
        ),
    )

    # tech_scope: technical scope (file globs, languages, services)
    op.add_column(
        "rules",
        sa.Column(
            "tech_scope",
            sa.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
    )

    # org_scope: organizational scope (departments, roles, regions)
    op.add_column(
        "rules",
        sa.Column(
            "org_scope",
            sa.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
    )

    # Backfill: existing rules get applies_to_surfaces based on
    # applicable_subject_types. Rules with code_diff get ['code'],
    # others get ['generic'].
    op.execute("""
        UPDATE rules
        SET applies_to_surfaces = CASE
            WHEN applicable_subject_types @> ARRAY['code_diff']::text[]
            THEN ARRAY['code']::text[]
            ELSE ARRAY['generic']::text[]
        END
        WHERE applies_to_surfaces = '{}'
    """)

    # Backfill tech_scope and org_scope from legacy scope field
    # engineering/* → tech_scope, everything else → org_scope
    op.execute("""
        UPDATE rules
        SET tech_scope = (
            SELECT COALESCE(array_agg(s), ARRAY[]::text[])
            FROM unnest(scope) AS s
            WHERE s LIKE 'engineering/%'
        ),
        org_scope = (
            SELECT COALESCE(array_agg(s), ARRAY[]::text[])
            FROM unnest(scope) AS s
            WHERE s NOT LIKE 'engineering/%'
        )
        WHERE tech_scope = '{}' AND org_scope = '{}'
    """)


def downgrade() -> None:
    """Remove surface-aware columns from rules table."""
    op.drop_column("rules", "org_scope")
    op.drop_column("rules", "tech_scope")
    op.drop_column("rules", "statement_translations")
    op.drop_column("rules", "locale")
    op.drop_column("rules", "norm_authority")
    op.drop_column("rules", "norm_tier")
    op.drop_column("rules", "applies_to_surfaces")
