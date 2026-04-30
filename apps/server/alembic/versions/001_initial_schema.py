"""Initial schema — rules, revisions, relationships, audit log, documents, extractions, api_keys.

Revision ID: 001
Revises: None
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum types
    modality_enum = sa.Enum("MUST", "MUST_NOT", "SHOULD", "MAY", "INFO", name="modality_enum")
    severity_enum = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="severity_enum")
    rule_status_enum = sa.Enum(
        "DRAFT",
        "REVIEW",
        "APPROVED",
        "EFFECTIVE",
        "SUPERSEDED",
        "RETIRED",
        name="rule_status_enum",
    )
    relationship_type_enum = sa.Enum(
        "REFINES",
        "OVERRIDES",
        "CONFLICTS_WITH",
        "DEPENDS_ON",
        "DERIVES_FROM",
        "SUCCEEDS",
        name="relationship_type_enum",
    )
    role_enum = sa.Enum("OWNER", "APPROVER", "READER", name="role_enum")

    # --- rules ---
    op.create_table(
        "rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("modality", modality_enum, nullable=False, server_default="MUST"),
        sa.Column("severity", severity_enum, nullable=False, server_default="MEDIUM"),
        sa.Column("status", rule_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("source_refs", JSONB(), nullable=False, server_default="[]"),
        sa.Column("scope", JSONB(), nullable=False, server_default="[]"),
        sa.Column("tags", JSONB(), nullable=False, server_default="[]"),
        sa.Column("preconditions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("exceptions", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "governance",
            JSONB(),
            nullable=False,
            server_default='{"owner": "system", "approvers": []}',
        ),
        sa.Column(
            "effective_period",
            JSONB(),
            nullable=False,
            server_default='{"valid_from": null, "valid_until": null}',
        ),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- rule_revisions ---
    op.create_table(
        "rule_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("modality", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("scope", JSONB(), nullable=False, server_default="[]"),
        sa.Column("tags", JSONB(), nullable=False, server_default="[]"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("changed_by", sa.String(255), nullable=False, server_default="system"),
        sa.Column("change_note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- rule_relationships ---
    op.create_table(
        "rule_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_id",
            sa.Uuid(),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("relationship_type", relationship_type_enum, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(255), nullable=False, server_default="system"),
    )

    # --- audit_log ---
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("actor", sa.String(255), nullable=False, server_default="system"),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False, index=True),
        sa.Column("details", JSONB(), nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("entry_hash", sa.String(64), nullable=False, unique=True),
    )

    # Append-only trigger for audit_log
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are prohibited';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_mutation();
    """)

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("uploaded_by", sa.String(255), nullable=False, server_default="system"),
    )

    # --- extractions ---
    op.create_table(
        "extractions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("candidates", JSONB(), nullable=False, server_default="[]"),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- api_keys ---
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="READER"),
        sa.Column("scopes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("extractions")
    op.drop_table("documents")
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_mutation()")
    op.drop_table("audit_log")
    op.drop_table("rule_relationships")
    op.drop_table("rule_revisions")
    op.drop_table("rules")
    op.execute("DROP TYPE IF EXISTS modality_enum")
    op.execute("DROP TYPE IF EXISTS severity_enum")
    op.execute("DROP TYPE IF EXISTS rule_status_enum")
    op.execute("DROP TYPE IF EXISTS relationship_type_enum")
    op.execute("DROP TYPE IF EXISTS role_enum")
