"""Per-surface remediation schemas for structured LLM output.

Each surface defines a remediation schema that tells the LLM how to express
machine-readable fix suggestions. Code uses patch-like edits; contracts use
text_rewrite with clause refs; transactions use field_change/approval_add/
process_reroute; etc.

These schemas are injected into the Gemini structured output definition.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import Surface

CODE_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["replace", "insert", "delete", "add_import", "rename"],
        },
        "file_path": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
        "original": {"type": "string"},
        "replacement": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
    },
}

CONTRACT_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["text_rewrite", "clause_revision", "block", "clarification"],
        },
        "clause_ref": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "original": {"type": "string"},
        "replacement": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
        "requires_counterparty_consent": {"type": "boolean"},
    },
}

TRANSACTION_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["field_change", "approval_add", "process_reroute", "block"],
        },
        "json_path": {"type": "string"},
        "field_name": {"type": "string"},
        "current_value": {"type": "string"},
        "suggested_value": {"type": "string"},
        "approval_level": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
    },
}

DOCUMENT_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["text_rewrite", "block", "clarification"],
        },
        "section": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "original": {"type": "string"},
        "replacement": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
    },
}

MESSAGE_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["text_rewrite", "block", "clarification"],
        },
        "segment": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "original": {"type": "string"},
        "replacement": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
    },
}

HUMAN_ACTION_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["process_reroute", "approval_add", "block", "clarification"],
        },
        "step": {"type": "string"},
        "field": {"type": "string"},
        "action_required": {"type": "string"},
        "escalation_target": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
    },
}

# Permissive union — used for generic/fallback surface
GENERIC_REMEDIATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        # Code fields
        "file_path": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
        # Document/contract/message fields
        "clause_ref": {"type": "string"},
        "section": {"type": "string"},
        "segment": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        # Transaction fields
        "json_path": {"type": "string"},
        "field_name": {"type": "string"},
        "current_value": {"type": "string"},
        "suggested_value": {"type": "string"},
        "approval_level": {"type": "string"},
        # Human action fields
        "step": {"type": "string"},
        "field": {"type": "string"},
        "action_required": {"type": "string"},
        "escalation_target": {"type": "string"},
        # Common fields
        "original": {"type": "string"},
        "replacement": {"type": "string"},
        "description": {"type": "string"},
        "auto_applicable": {"type": "boolean"},
        "requires_counterparty_consent": {"type": "boolean"},
    },
}

_SURFACE_REMEDIATION_MAP: dict[Surface, dict[str, Any]] = {
    Surface.CODE: CODE_REMEDIATION,
    Surface.CONTRACT: CONTRACT_REMEDIATION,
    Surface.TRANSACTION: TRANSACTION_REMEDIATION,
    Surface.DOCUMENT: DOCUMENT_REMEDIATION,
    Surface.MESSAGE: MESSAGE_REMEDIATION,
    Surface.HUMAN_ACTION: HUMAN_ACTION_REMEDIATION,
    Surface.GENERIC: GENERIC_REMEDIATION,
}


def get_remediation_schema(surface: Surface | None) -> dict[str, Any]:
    """Return the remediation schema for a given surface.

    Args:
        surface: The evaluation surface. If None, returns the generic schema.

    Returns:
        JSON schema dict for the remediation object.
    """
    if surface is None:
        return GENERIC_REMEDIATION
    return _SURFACE_REMEDIATION_MAP.get(surface, GENERIC_REMEDIATION)
