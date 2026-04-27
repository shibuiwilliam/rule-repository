"""Pure domain types for cross-project rule federation.

No external project imports — only stdlib typing and dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FederationNode:
    """A node in the federation hierarchy (organization → team → project).

    Attributes:
        id: Unique identifier.
        name: Human-readable name.
        level: Hierarchy level — organization, team, or project.
        parent_id: Parent node, or None for root nodes.
        description: Optional long-form description.
        default_scope: Scope tags inherited by rules added to this node.
    """

    id: str
    name: str
    level: str  # organization, team, project
    parent_id: str | None
    description: str | None
    default_scope: list[str] = field(default_factory=list)


@dataclass
class EffectiveRule:
    """A rule resolved through the federation chain with override info.

    Attributes:
        rule_id: The rule's UUID.
        statement: The rule statement text.
        modality: Deontic modality (MUST, SHOULD, etc.).
        severity: Impact level.
        source_federation_id: Federation node that owns the rule.
        source_federation_name: Human-readable name of the source node.
        is_overridden: Whether this rule has been overridden by a child node.
        overridden_by_rule_id: The rule that overrides this one, if any.
    """

    rule_id: str
    statement: str
    modality: str
    severity: str
    source_federation_id: str
    source_federation_name: str
    is_overridden: bool = False
    overridden_by_rule_id: str | None = None
