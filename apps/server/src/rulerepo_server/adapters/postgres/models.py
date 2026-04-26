"""SQLAlchemy ORM models — the physical database schema.

These map 1:1 to PostgreSQL tables and drive Alembic migrations.
Complex nested fields (source_refs, governance, etc.) are stored as JSONB.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class RuleModel(Base):
    """Persistent representation of a Rule."""

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(
        Enum("MUST", "MUST_NOT", "SHOULD", "MAY", "INFO", name="modality_enum"),
        nullable=False,
        default="MUST",
    )
    severity: Mapped[str] = mapped_column(
        Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="severity_enum"),
        nullable=False,
        default="MEDIUM",
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "DRAFT",
            "REVIEW",
            "APPROVED",
            "EFFECTIVE",
            "SUPERSEDED",
            "RETIRED",
            name="rule_status_enum",
        ),
        nullable=False,
        default="DRAFT",
    )

    # JSONB fields for complex nested data
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    scope: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preconditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exceptions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    governance: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {"owner": "system", "approvers": []}
    )
    effective_period: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {"valid_from": None, "valid_until": None}
    )

    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Embedding stored as float array (for pgvector compatibility later)
    embedding: Mapped[list | None] = mapped_column(ARRAY(Float), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    revisions: Mapped[list["RuleRevisionModel"]] = relationship(
        back_populates="rule", order_by="RuleRevisionModel.revision_number"
    )


class RuleRevisionModel(Base):
    """Immutable snapshot of a rule at each change."""

    __tablename__ = "rule_revisions"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Snapshot
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Change metadata
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    change_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    rule: Mapped["RuleModel"] = relationship(back_populates="revisions")


class RuleRelationshipModel(Base):
    """Directed edge between two rules — also projected to Neo4j."""

    __tablename__ = "rule_relationships"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        Enum(
            "REFINES",
            "OVERRIDES",
            "CONFLICTS_WITH",
            "DEPENDS_ON",
            "DERIVES_FROM",
            "SUCCEEDS",
            name="relationship_type_enum",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")


class AuditLogModel(Base):
    """Append-only audit log with hash-chain integrity.

    A database trigger prevents UPDATE and DELETE on this table.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class DocumentModel(Base):
    """Record of an uploaded document for rule extraction."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")


class ExtractionModel(Base):
    """Record of an extraction run against a document."""

    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidates: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApiKeyModel(Base):
    """API key for authentication and RBAC."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("OWNER", "APPROVER", "READER", name="role_enum"),
        nullable=False,
        default="READER",
    )
    scopes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LLMCacheModel(Base):
    """Cached LLM responses keyed by hash(inputs + model + prompt_version).

    Per CLAUDE.md §9.5: invalidated on rule revision.
    """

    __tablename__ = "llm_cache"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    inputs_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Enhancement 2: Gateway
# ---------------------------------------------------------------------------


class EnforcementPolicyModel(Base):
    """Defines when and how rules are automatically enforced via webhooks."""

    __tablename__ = "enforcement_policies"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_source: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rule_modality_filter: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rule_severity_min: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evaluation_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="preflight")
    context_extraction_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    on_deny: Mapped[str] = mapped_column(String(20), nullable=False, default="notify")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GatewayEvaluationModel(Base):
    """Record of an automated evaluation triggered by the gateway."""

    __tablename__ = "gateway_evaluations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    policy_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("enforcement_policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_source: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    rule_ids_evaluated: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    violations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actions_taken: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
