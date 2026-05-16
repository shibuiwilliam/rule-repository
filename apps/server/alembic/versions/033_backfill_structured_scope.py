"""Backfill structured_scope from legacy scope strings.

Normalizes existing flat scope values into the structured_scope JSONB
column so that multi-axis scope filtering works for all rules.

Heuristic: the first scope segment is treated as ``domain``, and any
second segment becomes ``subject_type``.  For example
``["engineering", "python"]`` → ``{"path": "engineering/python",
"dimensions": {"domain": "engineering", "subject_type": "python"}}``.

Rules that already have a non-empty structured_scope are skipped.

Revision ID: 033
Revises: 032
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column exists (idempotent migration support)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    """Add structured_scope column and backfill from legacy scope."""
    # Step 1: Create the column if it doesn't exist
    if not _column_exists("rules", "structured_scope"):
        op.add_column(
            "rules",
            sa.Column(
                "structured_scope",
                JSONB(),
                nullable=True,
                server_default='{"path": "", "dimensions": {}}',
            ),
        )

    # Step 2: Backfill from the legacy scope JSONB array.
    # scope is JSONB (an array of strings), NOT a Postgres text[].
    # Use jsonb_array_elements_text to iterate.
    op.execute("""
        UPDATE rules
        SET structured_scope = jsonb_build_object(
            'path', (
                SELECT string_agg(elem, '/')
                FROM jsonb_array_elements_text(scope) AS elem
            ),
            'dimensions', CASE
                WHEN jsonb_array_length(scope) >= 2
                THEN jsonb_build_object(
                    'domain', scope->>0,
                    'subject_type', scope->>1
                )
                WHEN jsonb_array_length(scope) = 1
                THEN jsonb_build_object(
                    'domain', scope->>0
                )
                ELSE '{}'::jsonb
            END
        )
        WHERE (structured_scope IS NULL
               OR structured_scope = '{"path": "", "dimensions": {}}'::jsonb)
          AND scope IS NOT NULL
          AND jsonb_typeof(scope) = 'array'
          AND jsonb_array_length(scope) > 0
    """)


def downgrade() -> None:
    """Revert structured_scope to the empty default."""
    op.execute("""
        UPDATE rules
        SET structured_scope = '{"path": "", "dimensions": {}}'::jsonb
        WHERE structured_scope IS NOT NULL
          AND structured_scope != '{"path": "", "dimensions": {}}'::jsonb
    """)
