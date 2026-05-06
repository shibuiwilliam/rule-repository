"""SQLAlchemy ORM models — the physical database schema.

These map 1:1 to PostgreSQL tables and drive Alembic migrations.
Complex nested fields (source_refs, governance, etc.) are stored as JSONB.
"""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# ---------------------------------------------------------------------------
# Project — top-level organizational boundary
# ---------------------------------------------------------------------------

DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"


class TenantModel(Base):
    """A tenant — the top-level isolation boundary for multi-tenancy."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"


class ProjectModel(Base):
    """A project groups rules, documents, and other resources."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RuleModel(Base):
    """Persistent representation of a Rule."""

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
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

    # Maturity model (PROJECT_ENHANCE.md §2)
    maturity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="experimental")
    false_positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    true_positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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
    context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    following_examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    violation_examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Sensitivity — drives LLM provider routing and log retention
    sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, default="INTERNAL")

    # Regulatory severity — penalty band independent of operational severity
    regulatory_severity: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE")

    # Multi-tenancy
    tenant_id: Mapped[str] = mapped_column(Uuid, nullable=False, default=DEFAULT_TENANT_ID, index=True)

    # Polyglot rules — shared equivalence_id groups translations
    equivalence_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Embedding stored as float array (for pgvector compatibility later)
    embedding: Mapped[list | None] = mapped_column(ARRAY(Float), nullable=True)

    clarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    revisions: Mapped[list["RuleRevisionModel"]] = relationship(
        back_populates="rule", order_by="RuleRevisionModel.revision_number"
    )


# ---------------------------------------------------------------------------
# Enhancement 1: Rule Playground & Testing Framework
# ---------------------------------------------------------------------------


class RuleTestCaseModel(Base):
    """A test case attached to a rule for the playground testing framework."""

    __tablename__ = "rule_test_cases"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sample_input: Mapped[str] = mapped_column(Text, nullable=False)
    input_type: Mapped[str] = mapped_column(String(20), nullable=False, default="code")
    expected_verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    last_result: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    passing: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Enhancement 2: Alerts
# ---------------------------------------------------------------------------


class AlertModel(Base):
    """General-purpose alert raised by intelligence workers."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("rules.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Enhancement 2: Intelligence Persistence (health scores + recommendations)
# ---------------------------------------------------------------------------


class RuleHealthScoreModel(Base):
    """Persisted health score snapshot computed by the daily worker."""

    __tablename__ = "rule_health_scores"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness: Mapped[float] = mapped_column(Float, nullable=False)
    clarity: Mapped[float] = mapped_column(Float, nullable=False)
    test_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    freshness: Mapped[float] = mapped_column(Float, nullable=False)
    activity: Mapped[float] = mapped_column(Float, nullable=False)
    owner_engagement: Mapped[float] = mapped_column(Float, nullable=False)
    issues: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RuleRecommendationModel(Base):
    """Persisted recommendation generated by the daily worker."""

    __tablename__ = "rule_recommendations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_change: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_rule_ids: Mapped[list] = mapped_column(ARRAY(String), server_default="{}")
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Enhancement 3: Cross-Project Rule Federation
# ---------------------------------------------------------------------------


class RuleFederationModel(Base):
    """A node in the federation hierarchy (organization -> team -> project)."""

    __tablename__ = "rule_federations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        Uuid, ForeignKey("rule_federations.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_scope: Mapped[list] = mapped_column(ARRAY(String), server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RuleFederationMembershipModel(Base):
    """Associates a rule with a federation node, optionally overriding a parent rule."""

    __tablename__ = "rule_federation_memberships"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    federation_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("rule_federations.id", ondelete="CASCADE"), nullable=False
    )
    override_parent_rule_id: Mapped[str | None] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RuleRevisionModel(Base):
    """Immutable snapshot of a rule at each change."""

    __tablename__ = "rule_revisions"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    rule: Mapped["RuleModel"] = relationship(back_populates="revisions")


class RuleRelationshipModel(Base):
    """Directed edge between two rules — also projected to Neo4j."""

    __tablename__ = "rule_relationships"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
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
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Enhancement 2: Gateway
# ---------------------------------------------------------------------------


class EnforcementPolicyModel(Base):
    """Defines when and how rules are automatically enforced via webhooks."""

    __tablename__ = "enforcement_policies"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EvaluationRecordModel(Base):
    """Per-rule evaluation result for analytics and persistence."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True, index=True)
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scope: Mapped[str | None] = mapped_column(String(500), nullable=True)
    input_type: Mapped[str] = mapped_column(String(20), nullable=False, default="code")
    model_id: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    cached: Mapped[bool] = mapped_column(default=False)
    agent_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Encrypted evaluation context — PII-safe at rest (AES-GCM, key from core/secrets)
    context_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Cost ledger — token counts and estimated cost per evaluation
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(sa.Numeric(10, 6), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Evaluations Daily Aggregation — intelligence dashboard backing table
# ---------------------------------------------------------------------------


class EvaluationDailyAggModel(Base):
    """Pre-aggregated daily evaluation metrics per rule per tenant."""

    __tablename__ = "evaluations_daily_agg"
    __table_args__ = (sa.UniqueConstraint("rule_id", "tenant_id", "date", name="uq_eval_daily_agg"),)

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    rule_id: Mapped[str] = mapped_column(Uuid, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(Uuid, nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(sa.Date, nullable=False)
    allow_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deny_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_confirmation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(sa.Numeric(10, 6), nullable=True)


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Enhancement 1: Automatic Rule Discovery
# ---------------------------------------------------------------------------


class DiscoveryScanModel(Base):
    """Record of a discovery scan that analyzes source files for implicit rules."""

    __tablename__ = "discovery_scans"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="running")
    sources: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    repository: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidates_found: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidates: Mapped[list["DiscoveryCandidateModel"]] = relationship(
        back_populates="scan", order_by="DiscoveryCandidateModel.confidence.desc()"
    )


class DiscoveryCandidateModel(Base):
    """A candidate rule discovered during a scan, pending review."""

    __tablename__ = "discovery_candidates"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    scan_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("discovery_scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[list] = mapped_column(ARRAY(String), server_default="{}")
    tags: Mapped[list] = mapped_column(ARRAY(String), server_default="{}")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    created_rule_id: Mapped[str | None] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    scan: Mapped["DiscoveryScanModel"] = relationship(back_populates="candidates")
    created_rule: Mapped["RuleModel | None"] = relationship(foreign_keys=[created_rule_id])


# ---------------------------------------------------------------------------
# Enhancement 3: Rule Set Snapshots & Deployments
# ---------------------------------------------------------------------------


class RuleSetSnapshotModel(Base):
    """Immutable snapshot of a set of rules at a point in time."""

    __tablename__ = "rule_set_snapshots"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_filter: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    rule_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rule_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RuleSetDeploymentModel(Base):
    """Tracks which snapshot is deployed to which environment."""

    __tablename__ = "rule_set_deployments"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rule_set_snapshots.id"), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    deployed_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Enhancement 2: Correction Feedback Loop
# ---------------------------------------------------------------------------


class CorrectionModel(Base):
    """A correction feedback record linking a code diff to rule improvements."""

    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    project_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("projects.id"), nullable=False, index=True, default=DEFAULT_PROJECT_ID
    )
    original_diff: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_diff: Mapped[str] = mapped_column(Text, nullable=False)
    delta_summary: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    file_paths: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    affected_functions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    lines_added: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    lines_removed: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    repository: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Analysis results
    analysis_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    matched_rule_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    candidate_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_modality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    candidate_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    created_rule_id: Mapped[str | None] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Enhancement 3: Correction-to-Rule Flywheel (PROJECT_ENHANCE.md §3)
# ---------------------------------------------------------------------------


class DraftRuleProposalModel(Base):
    """A rule draft auto-generated from clustered corrections."""

    __tablename__ = "draft_rule_proposals"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_correction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cluster_size: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_rule_id: Mapped[str | None] = mapped_column(
        Uuid, ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 6a: Collaborative Governance — Proposals
# ---------------------------------------------------------------------------


class ProposalModel(Base):
    """A governance proposal wrapping rule changes in a reviewable workflow."""

    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str | None] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=True, index=True)
    proposal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    author_id: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Structured change specification
    change_spec: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_rule_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Automated analysis results
    conflict_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    impact_preview: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Approval workflow
    required_approvers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    approval_votes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    enacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    comments: Mapped[list["ProposalCommentModel"]] = relationship(
        back_populates="proposal", order_by="ProposalCommentModel.created_at"
    )


class ProposalCommentModel(Base):
    """A threaded comment on a governance proposal."""

    __tablename__ = "proposal_comments"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    proposal_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_comment_id: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    author_id: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    comment_type: Mapped[str] = mapped_column(String(20), nullable=False, default="comment")
    suggestion_spec: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    proposal: Mapped["ProposalModel"] = relationship(back_populates="comments")


class NotificationModel(Base):
    """User notification generated by proposal activity."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    proposal_id: Mapped[str | None] = mapped_column(
        Uuid, ForeignKey("proposals.id", ondelete="CASCADE"), nullable=True, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 6b: Autonomous Agent Governance
# ---------------------------------------------------------------------------


class AgentProfileModel(Base):
    """Persistent governance profile for an AI agent."""

    __tablename__ = "agent_profiles"

    agent_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    trust_level: Mapped[str] = mapped_column(String(20), nullable=False, default="untrusted")

    # Behavioral model (auto-computed by cron)
    compliance_rate_30d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    violation_patterns: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    strength_areas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    weakness_areas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Governance permissions
    can_propose_rules: Mapped[bool] = mapped_column(default=False)
    can_vote_on_proposals: Mapped[bool] = mapped_column(default=False)
    max_auto_fix_severity: Mapped[str] = mapped_column(String(20), nullable=False, default="none")

    # Adaptive delivery
    personalized_rule_weights: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    suppressed_rule_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    mastery_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AgentExceptionRequestModel(Base):
    """An agent's request for a rule exception in a specific context."""

    __tablename__ = "agent_exception_requests"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("agent_profiles.agent_id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_exception: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    proposal_id: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentNegotiationModel(Base):
    """An agent's challenge of a verdict with a counter-argument."""

    __tablename__ = "agent_negotiations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("agent_profiles.agent_id", ondelete="CASCADE"), nullable=False, index=True
    )
    evaluation_id: Mapped[str] = mapped_column(Uuid, nullable=False)
    rule_id: Mapped[str] = mapped_column(Uuid, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    original_verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    counter_argument: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_action: Mapped[str] = mapped_column(String(30), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GovernanceSessionModel(Base):
    """Multi-agent governance session for shared verdict context."""

    __tablename__ = "governance_sessions"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str | None] = mapped_column(Uuid, nullable=True)
    context_ref: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    agent_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    shared_verdicts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
