"""Pydantic request/response schemas for the federation API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FederationCreate(BaseModel):
    """Request body for creating a federation node.

    Attributes:
        name: Human-readable name.
        level: Hierarchy level (organization, team, project).
        parent_id: Parent node UUID, or None for root.
        description: Optional description.
        default_scope: Default scope tags for this node.
    """

    model_config = ConfigDict(strict=True)

    name: str
    level: str
    parent_id: str | None = None
    description: str | None = None
    default_scope: list[str] = []


class FederationResponse(BaseModel):
    """Response for a federation node.

    Attributes:
        id: UUID of the federation node.
        name: Human-readable name.
        level: Hierarchy level.
        parent_id: Parent node UUID or None.
        description: Optional description.
        default_scope: Default scope tags.
        created_at: ISO timestamp of creation.
        children: Nested child federation nodes.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    level: str
    parent_id: str | None = None
    description: str | None = None
    default_scope: list[str] = []
    created_at: str | None = None
    children: list[FederationResponse] = []


class AddRuleRequest(BaseModel):
    """Request body for adding a rule to a federation node.

    Attributes:
        rule_id: UUID of the rule to add.
        override_parent_rule_id: UUID of a parent-level rule this overrides.
    """

    model_config = ConfigDict(strict=True)

    rule_id: str
    override_parent_rule_id: str | None = None


class EffectiveRuleResponse(BaseModel):
    """Response for a single effective rule resolved through the federation chain.

    Attributes:
        rule_id: UUID of the rule.
        statement: The rule statement text.
        modality: Deontic modality.
        severity: Impact level.
        source_federation_id: UUID of the federation node that owns the rule.
        source_federation_name: Human-readable name of the source node.
        overrides: UUID of the parent rule this overrides, or None.
    """

    model_config = ConfigDict(from_attributes=True)

    rule_id: str
    statement: str
    modality: str
    severity: str
    source_federation_id: str
    source_federation_name: str
    overrides: str | None = None
