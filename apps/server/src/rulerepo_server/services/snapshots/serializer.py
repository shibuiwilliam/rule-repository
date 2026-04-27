"""Snapshot serialization — freeze and thaw rule sets for immutable storage."""

from __future__ import annotations

from typing import Any


def serialize_rules(rules: list[Any]) -> dict[str, Any]:
    """Serialize rule models into a frozen snapshot dict.

    Args:
        rules: List of RuleModel instances (or dicts with matching keys).

    Returns:
        Dict mapping ``rule_id`` to a frozen representation of the rule,
        e.g. ``{rule_id: {statement, modality, severity, ...}}``.
    """
    snapshot: dict[str, Any] = {}
    for rule in rules:
        if isinstance(rule, dict):
            rule_id = str(rule.get("id", ""))
            snapshot[rule_id] = {
                "statement": rule.get("statement", ""),
                "modality": rule.get("modality", ""),
                "severity": rule.get("severity", ""),
                "status": rule.get("status", ""),
                "scope": rule.get("scope", []),
                "tags": rule.get("tags", []),
                "rationale": rule.get("rationale", ""),
            }
        else:
            rule_id = str(rule.id)
            snapshot[rule_id] = {
                "statement": rule.statement,
                "modality": rule.modality,
                "severity": rule.severity,
                "status": rule.status,
                "scope": rule.scope if isinstance(rule.scope, list) else [],
                "tags": rule.tags if isinstance(rule.tags, list) else [],
                "rationale": rule.rationale or "",
            }
    return snapshot


def deserialize_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Deserialize a snapshot back into rule dicts for evaluation.

    Args:
        snapshot: Dict mapping rule_id to frozen rule data.

    Returns:
        List of rule dicts, each containing ``id`` plus the frozen fields.
    """
    rules: list[dict[str, Any]] = []
    for rule_id, data in snapshot.items():
        rule_dict: dict[str, Any] = {"id": rule_id}
        rule_dict.update(data)
        rules.append(rule_dict)
    return rules
