"""Backfill applicable_subject_types for universal default behavior.

Rules with scope containing code-specific keywords get explicit
applicable_subject_types = ['code_diff']. All others get NULL
(meaning universal — applicable to all subject types).

This eliminates the code-centric bias where rules without explicit
subject types were silently treated as code-only.

Revision ID: 032
Revises: 031
"""

from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None

# Scope keywords that indicate a code-specific rule
_CODE_SCOPE_KEYWORDS = [
    "python",
    "typescript",
    "javascript",
    "go",
    "rust",
    "java",
    "ruby",
    "sql",
    "engineering/",
    "devops",
    "ci-cd",
    "testing/",
    "api-design",
    "code",
    "frontend",
    "backend",
]


def upgrade() -> None:
    """Backfill applicable_subject_types based on scope content.

    - Rules whose scope contains code-specific keywords AND have
      NULL applicable_subject_types → set to ['code_diff'].
    - All other rules with NULL applicable_subject_types → leave as NULL
      (interpreted as universal by the rule selector).
    """
    # Build a SQL condition that checks if any scope element matches code keywords
    scope_conditions = " OR ".join(f"s ILIKE '%{kw}%'" for kw in _CODE_SCOPE_KEYWORDS)

    op.execute(f"""
        UPDATE rules
        SET applicable_subject_types = ARRAY['code_diff']::text[]
        WHERE applicable_subject_types IS NULL
          AND EXISTS (
              SELECT 1 FROM unnest(scope) AS s
              WHERE {scope_conditions}
          )
    """)


def downgrade() -> None:
    """Revert: set code_diff-only rules back to NULL."""
    op.execute("""
        UPDATE rules
        SET applicable_subject_types = NULL
        WHERE applicable_subject_types = ARRAY['code_diff']::text[]
    """)
