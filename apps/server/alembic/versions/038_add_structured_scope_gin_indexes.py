"""Add GIN indexes on structured_scope JSONB for query performance.

IMPROVEMENT.md §5.2 Proposal 2 calls for GIN indexes on
``structured_scope -> 'dimensions' -> 'domain'`` and
``structured_scope -> 'dimensions' -> 'subject_type'`` to accelerate
multi-axis scope filtering in rule_selector.py.

Also adds a general GIN index on the full ``structured_scope`` column
for containment queries.

Revision ID: 038
Revises: 037
"""

from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GIN indexes on structured_scope for efficient JSONB querying."""
    # Full JSONB GIN index for containment queries (@> operator)
    op.execute("CREATE INDEX IF NOT EXISTS ix_rules_structured_scope_gin ON rules USING GIN (structured_scope)")

    # Expression indexes on the primary scope axes for equality lookups
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rules_scope_domain ON rules ((structured_scope -> 'dimensions' ->> 'domain'))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rules_scope_subject_type "
        "ON rules ((structured_scope -> 'dimensions' ->> 'subject_type'))"
    )


def downgrade() -> None:
    """Remove structured_scope indexes."""
    op.execute("DROP INDEX IF EXISTS ix_rules_scope_subject_type")
    op.execute("DROP INDEX IF EXISTS ix_rules_scope_domain")
    op.execute("DROP INDEX IF EXISTS ix_rules_structured_scope_gin")
