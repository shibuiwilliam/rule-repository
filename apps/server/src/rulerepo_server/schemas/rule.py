"""Pydantic request/response schemas for rule CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from rulerepo_server.domain.rule import Modality, RegulatorySeverity, RuleStatus, Sensitivity, Severity

# ---------------------------------------------------------------------------
# Nested value-object schemas
# ---------------------------------------------------------------------------


class SourceRefSchema(BaseModel):
    """Source document reference."""

    document_id: str
    section: str | None = None
    offset: int | None = None
    page: int | None = None


class EffectivePeriodSchema(BaseModel):
    """Time window for rule effectiveness."""

    valid_from: datetime | None = None
    valid_until: datetime | None = None


class GovernanceSchema(BaseModel):
    """Ownership and approval metadata."""

    owner: str = "system"
    approvers: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""

    statement: str = Field(..., min_length=1, max_length=10000, description="Rule text")
    modality: Modality = Modality.MUST
    severity: Severity = Severity.MEDIUM
    status: RuleStatus = RuleStatus.DRAFT
    scope: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rationale: str = ""
    context: str = Field(
        default="",
        description="Surrounding document context — section hierarchy, definitions, and qualifying information.",
    )
    preconditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    following_examples: list[str] = Field(
        default_factory=list,
        description="Examples of activities that follow this rule.",
    )
    violation_examples: list[str] = Field(
        default_factory=list,
        description="Examples of activities that violate this rule.",
    )
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    regulatory_severity: RegulatorySeverity = RegulatorySeverity.NONE
    applicable_subject_types: list[str] = Field(default_factory=lambda: ["code_diff"])
    jurisdiction: str = "global"
    legal_force: str = "policy"
    review_cadence: str | None = None
    source_refs: list[SourceRefSchema] = Field(default_factory=list)
    effective_period: EffectivePeriodSchema = Field(default_factory=EffectivePeriodSchema)
    governance: GovernanceSchema = Field(default_factory=GovernanceSchema)


class RuleUpdate(BaseModel):
    """Schema for updating an existing rule. All fields are optional."""

    statement: str | None = Field(default=None, min_length=1, max_length=10000)
    modality: Modality | None = None
    severity: Severity | None = None
    status: RuleStatus | None = None
    scope: list[str] | None = None
    tags: list[str] | None = None
    rationale: str | None = None
    context: str | None = None
    preconditions: list[str] | None = None
    exceptions: list[str] | None = None
    following_examples: list[str] | None = None
    violation_examples: list[str] | None = None
    sensitivity: Sensitivity | None = None
    regulatory_severity: RegulatorySeverity | None = None
    applicable_subject_types: list[str] | None = None
    jurisdiction: str | None = None
    legal_force: str | None = None
    review_cadence: str | None = None
    source_refs: list[SourceRefSchema] | None = None
    effective_period: EffectivePeriodSchema | None = None
    governance: GovernanceSchema | None = None
    revision_note: str = Field(default="", description="Reason for this change")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RuleResponse(BaseModel):
    """Full rule representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: str | None = None
    maturity_level: str = "experimental"
    statement: str
    modality: Modality
    severity: Severity
    status: RuleStatus
    scope: list[str]
    tags: list[str]
    rationale: str
    context: str = ""
    preconditions: list[str]
    exceptions: list[str]
    following_examples: list[str] = Field(default_factory=list)
    violation_examples: list[str] = Field(default_factory=list)
    sensitivity: str = "INTERNAL"
    regulatory_severity: str = "NONE"
    applicable_subject_types: list[str] = Field(default_factory=lambda: ["code_diff"])
    jurisdiction: str = "global"
    legal_force: str = "policy"
    review_cadence: str | None = None
    source_refs: list[SourceRefSchema]
    effective_period: EffectivePeriodSchema
    governance: GovernanceSchema
    created_at: datetime
    updated_at: datetime


class RuleListResponse(BaseModel):
    """Paginated list of rules."""

    items: list[RuleResponse]
    total: int
    page: int
    page_size: int


class RuleRevisionResponse(BaseModel):
    """A single revision in the rule's history."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    revision_number: int
    statement: str
    modality: str
    severity: str
    status: str
    scope: list[str]
    tags: list[str]
    rationale: str
    changed_by: str
    change_note: str
    created_at: datetime


class RelationshipResponse(BaseModel):
    """A relationship between two rules."""

    source_id: UUID
    target_id: UUID
    relationship_type: str
    created_at: datetime
    created_by: str


class RelationshipCreate(BaseModel):
    """Schema for creating a rule relationship."""

    source_id: UUID
    target_id: UUID
    relationship_type: str


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------


class RuleImportItem(BaseModel):
    """A single rule in a bulk import payload."""

    statement: str = Field(..., min_length=1, max_length=10000)
    modality: str = "MUST"
    severity: str = "MEDIUM"
    scope: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rationale: str = ""
    context: str = ""
    following_examples: list[str] = Field(default_factory=list)
    violation_examples: list[str] = Field(default_factory=list)
    source: str | None = None
    confidence: float | None = None
    # Phase 7b fields
    applicable_subject_types: list[str] | None = None
    jurisdiction: str | None = None
    legal_force: str | None = None
    review_cadence: str | None = None
    sensitivity: str | None = None
    regulatory_severity: str | None = None


class RulesImportRequest(BaseModel):
    """Bulk import payload matching the rules.yaml format."""

    version: int = 1
    project: str | None = None
    rules: list[RuleImportItem] = Field(..., min_length=1)
