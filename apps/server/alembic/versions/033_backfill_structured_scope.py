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

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Backfill structured_scope from legacy scope column."""
    # Only update rows whose structured_scope is the empty default
    op.execute("""
        UPDATE rules
        SET structured_scope = jsonb_build_object(
            'path', array_to_string(scope, '/'),
            'dimensions', CASE
                WHEN array_length(scope, 1) >= 2
                THEN jsonb_build_object(
                    'domain', scope[1],
                    'subject_type', scope[2]
                )
                WHEN array_length(scope, 1) = 1
                THEN jsonb_build_object(
                    'domain', scope[1]
                )
                ELSE '{}'::jsonb
            END
        )
        WHERE (structured_scope IS NULL
               OR structured_scope = '{"path": "", "dimensions": {}}'::jsonb)
          AND scope IS NOT NULL
          AND array_length(scope, 1) > 0
    """)


def downgrade() -> None:
    """Revert structured_scope to the empty default."""
    op.execute("""
        UPDATE rules
        SET structured_scope = '{"path": "", "dimensions": {}}'::jsonb
        WHERE structured_scope IS NOT NULL
          AND structured_scope != '{"path": "", "dimensions": {}}'::jsonb
    """)
