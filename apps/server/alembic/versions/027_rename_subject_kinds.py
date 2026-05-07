"""Rename SubjectType values to SubjectKind (PROJECT.md alignment).

Renames stored subject type values in applicable_subject_types JSONB arrays
and evaluations.subject_type column to match PROJECT.md §5.2 naming:
  code_change → code_diff
  hr_event → event
  contract_clause → clause_set
  expense_claim → transaction
  marketing_copy → creative
  vendor_onboarding → identity
  document_revision → document

Also updates the server_default on applicable_subject_types.

Revision ID: 027
Revises: 026
"""

import sqlalchemy as sa
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None

# Mapping from old values to new values
_RENAMES = {
    "code_change": "code_diff",
    "hr_event": "event",
    "contract_clause": "clause_set",
    "expense_claim": "transaction",
    "marketing_copy": "creative",
    "vendor_onboarding": "identity",
    "document_revision": "document",
}

_REVERSE_RENAMES = {v: k for k, v in _RENAMES.items()}


def upgrade() -> None:
    """Rename subject type values in stored data."""
    conn = op.get_bind()

    # Update applicable_subject_types JSONB array on rules table
    for old_val, new_val in _RENAMES.items():
        conn.execute(
            sa.text(
                """
                UPDATE rules
                SET applicable_subject_types = (
                    SELECT jsonb_agg(
                        CASE WHEN elem::text = :old_quoted THEN :new_val::jsonb ELSE elem END
                    )
                    FROM jsonb_array_elements(applicable_subject_types) AS elem
                )
                WHERE applicable_subject_types @> :old_array::jsonb
                """
            ),
            {
                "old_quoted": f'"{old_val}"',
                "new_val": f'"{new_val}"',
                "old_array": f'["{old_val}"]',
            },
        )

    # Update subject_type column on evaluations table
    for old_val, new_val in _RENAMES.items():
        conn.execute(
            sa.text("UPDATE evaluations SET subject_type = :new WHERE subject_type = :old"),
            {"old": old_val, "new": new_val},
        )

    # Update server default
    op.alter_column(
        "rules",
        "applicable_subject_types",
        server_default='["code_diff"]',
    )


def downgrade() -> None:
    """Reverse the rename."""
    conn = op.get_bind()

    for new_val, old_val in _REVERSE_RENAMES.items():
        conn.execute(
            sa.text(
                """
                UPDATE rules
                SET applicable_subject_types = (
                    SELECT jsonb_agg(
                        CASE WHEN elem::text = :new_quoted THEN :old_val::jsonb ELSE elem END
                    )
                    FROM jsonb_array_elements(applicable_subject_types) AS elem
                )
                WHERE applicable_subject_types @> :new_array::jsonb
                """
            ),
            {
                "new_quoted": f'"{new_val}"',
                "old_val": f'"{old_val}"',
                "new_array": f'["{new_val}"]',
            },
        )

    for new_val, old_val in _REVERSE_RENAMES.items():
        conn.execute(
            sa.text("UPDATE evaluations SET subject_type = :old WHERE subject_type = :new"),
            {"old": old_val, "new": new_val},
        )

    op.alter_column(
        "rules",
        "applicable_subject_types",
        server_default='["code_change"]',
    )
