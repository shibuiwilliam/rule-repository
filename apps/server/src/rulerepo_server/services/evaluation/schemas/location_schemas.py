"""Per-surface location schemas for structured LLM output.

Each surface defines a location schema that tells the LLM how to reference
the specific place in the subject where an issue was found. Code surfaces
use file_path/line_number; contracts use clause_ref/offsets; transactions
use JSON paths; etc.

These schemas are injected into the Gemini structured output definition
so the LLM produces surface-appropriate location fields.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import Surface

CODE_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
        "function_name": {"type": "string"},
        "snippet": {"type": "string"},
    },
}

CONTRACT_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "clause_ref": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "span_text": {"type": "string"},
    },
}

TRANSACTION_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "json_path": {"type": "string"},
        "field_name": {"type": "string"},
        "current_value": {"type": "string"},
    },
}

DOCUMENT_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "section": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "span_text": {"type": "string"},
    },
}

MESSAGE_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "segment": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "span_text": {"type": "string"},
    },
}

HUMAN_ACTION_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "step": {"type": "string"},
        "field": {"type": "string"},
        "context": {"type": "string"},
    },
}

# Permissive union of all location fields — used for the generic/fallback surface
GENERIC_LOCATION: dict[str, Any] = {
    "type": "object",
    "properties": {
        # Code fields
        "file_path": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
        "function_name": {"type": "string"},
        "snippet": {"type": "string"},
        # Document/contract/message fields
        "clause_ref": {"type": "string"},
        "section": {"type": "string"},
        "segment": {"type": "string"},
        "offset_start": {"type": "integer"},
        "offset_end": {"type": "integer"},
        "span_text": {"type": "string"},
        # Transaction fields
        "json_path": {"type": "string"},
        "field_name": {"type": "string"},
        "current_value": {"type": "string"},
        # Human action fields
        "step": {"type": "string"},
        "field": {"type": "string"},
        "context": {"type": "string"},
    },
}

_SURFACE_LOCATION_MAP: dict[Surface, dict[str, Any]] = {
    Surface.CODE: CODE_LOCATION,
    Surface.CONTRACT: CONTRACT_LOCATION,
    Surface.TRANSACTION: TRANSACTION_LOCATION,
    Surface.DOCUMENT: DOCUMENT_LOCATION,
    Surface.MESSAGE: MESSAGE_LOCATION,
    Surface.HUMAN_ACTION: HUMAN_ACTION_LOCATION,
    Surface.GENERIC: GENERIC_LOCATION,
}

# Fields that are valid for each surface — used for validation/stripping
_SURFACE_VALID_FIELDS: dict[Surface, set[str]] = {
    surface: set(schema["properties"].keys()) for surface, schema in _SURFACE_LOCATION_MAP.items()
}


def get_location_schema(surface: Surface | None) -> dict[str, Any]:
    """Return the location schema for a given surface.

    Args:
        surface: The evaluation surface. If None, returns the generic schema.

    Returns:
        JSON schema dict for the location object.
    """
    if surface is None:
        return GENERIC_LOCATION
    return _SURFACE_LOCATION_MAP.get(surface, GENERIC_LOCATION)


def get_valid_location_fields(surface: Surface | None) -> set[str]:
    """Return the set of valid location field names for a surface.

    Args:
        surface: The evaluation surface. If None, returns all fields.

    Returns:
        Set of valid field name strings.
    """
    if surface is None:
        return _SURFACE_VALID_FIELDS[Surface.GENERIC]
    return _SURFACE_VALID_FIELDS.get(surface, _SURFACE_VALID_FIELDS[Surface.GENERIC])
