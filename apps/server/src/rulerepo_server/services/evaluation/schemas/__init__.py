"""Surface-aware structured output schemas for the evaluation engine.

Builds complete Gemini JSON schemas by composing the appropriate
location and remediation sub-schemas for each evaluation surface.

Usage:
    from rulerepo_server.services.evaluation.schemas import (
        build_verdict_schema,
        build_batch_verdict_schema,
        parse_location,
        validate_location_fields,
    )
    schema = build_verdict_schema(Surface.CONTRACT)
"""

from __future__ import annotations

import copy
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import (
    CodeLocation,
    ContractLocation,
    DocumentLocation,
    HumanActionLocation,
    IssueLocation,
    MessageLocation,
    Surface,
    TransactionLocation,
)
from rulerepo_server.services.evaluation.schemas.location_schemas import (
    get_location_schema,
    get_valid_location_fields,
)
from rulerepo_server.services.evaluation.schemas.remediation_schemas import (
    get_remediation_schema,
)

logger = get_logger(__name__)

# Base verdict schema — location and remediation items are injected per surface
_BASE_VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [
                "ALLOW",
                "DENY",
                "NEEDS_CONFIRMATION",
                "ALLOW_WITH_CONDITIONS",
                "REQUIRES_DISCLOSURE",
            ],
        },
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "issue_description": {"type": "string"},
        "fix_suggestion": {"type": "string"},
        "locations": {
            "type": "array",
            "items": {},  # Placeholder — filled per surface
        },
        "remediations": {
            "type": "array",
            "items": {},  # Placeholder — filled per surface
        },
    },
    "required": ["verdict", "confidence", "reasoning"],
}


def build_verdict_schema(surface: Surface | None = None) -> dict[str, Any]:
    """Build a complete verdict JSON schema for a given surface.

    Args:
        surface: The evaluation surface. If None, uses the generic (permissive) schema.

    Returns:
        JSON schema dict suitable for Gemini's response_json_schema parameter.
    """
    schema = copy.deepcopy(_BASE_VERDICT_SCHEMA)
    schema["properties"]["locations"]["items"] = get_location_schema(surface)
    schema["properties"]["remediations"]["items"] = get_remediation_schema(surface)
    return schema


def build_batch_verdict_schema(surface: Surface | None = None) -> dict[str, Any]:
    """Build a batch verdict JSON schema for a given surface.

    Args:
        surface: The evaluation surface. If None, uses the generic schema.

    Returns:
        JSON schema dict for batch evaluation responses.
    """
    verdict_item = build_verdict_schema(surface)
    # Add rule_index and rule_id to the verdict item for batch matching
    verdict_item["properties"]["rule_index"] = {"type": "integer"}
    verdict_item["properties"]["rule_id"] = {"type": "string"}
    verdict_item["required"] = ["rule_index", "rule_id", "verdict", "confidence", "reasoning"]

    return {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": verdict_item,
            },
        },
        "required": ["verdicts"],
    }


def parse_location(data: dict[str, Any], surface: Surface | None) -> IssueLocation:
    """Parse a location dict from LLM output into the appropriate domain object.

    Args:
        data: Raw location dict from LLM JSON output.
        surface: The evaluation surface for type dispatch.

    Returns:
        A surface-appropriate location dataclass instance.
    """
    match surface:
        case Surface.CODE:
            return CodeLocation(
                file_path=data.get("file_path", ""),
                start_line=data.get("start_line"),
                end_line=data.get("end_line"),
                function_name=data.get("function_name"),
                snippet=data.get("snippet"),
            )
        case Surface.CONTRACT:
            return ContractLocation(
                clause_ref=data.get("clause_ref", ""),
                offset_start=data.get("offset_start"),
                offset_end=data.get("offset_end"),
                span_text=data.get("span_text"),
            )
        case Surface.TRANSACTION:
            return TransactionLocation(
                json_path=data.get("json_path", ""),
                field_name=data.get("field_name", ""),
                current_value=data.get("current_value", ""),
            )
        case Surface.DOCUMENT:
            return DocumentLocation(
                section=data.get("section", ""),
                offset_start=data.get("offset_start"),
                offset_end=data.get("offset_end"),
                span_text=data.get("span_text"),
            )
        case Surface.MESSAGE:
            return MessageLocation(
                segment=data.get("segment", ""),
                offset_start=data.get("offset_start"),
                offset_end=data.get("offset_end"),
                span_text=data.get("span_text"),
            )
        case Surface.HUMAN_ACTION:
            return HumanActionLocation(
                step=data.get("step", ""),
                field=data.get("field", ""),
                context=data.get("context", ""),
            )
        case _:
            # Generic/None — fall back to CodeLocation for backward compat
            return CodeLocation(
                file_path=data.get("file_path", ""),
                start_line=data.get("start_line"),
                end_line=data.get("end_line"),
                function_name=data.get("function_name"),
                snippet=data.get("snippet"),
            )


def validate_location_fields(
    data: dict[str, Any],
    surface: Surface | None,
) -> dict[str, Any]:
    """Validate and strip invalid location fields for a surface.

    If the LLM returns fields that don't belong to the surface (e.g.,
    ``file_path`` in a contract evaluation), those fields are logged
    as warnings and stripped from the dict.

    Args:
        data: Raw location dict from LLM output.
        surface: The evaluation surface.

    Returns:
        A cleaned dict with only valid fields for the surface.
    """
    if surface is None or surface == Surface.GENERIC:
        return data

    valid_fields = get_valid_location_fields(surface)
    invalid_keys = set(data.keys()) - valid_fields

    if invalid_keys:
        logger.warning(
            "location_field_mismatch",
            surface=surface.value,
            invalid_fields=sorted(invalid_keys),
            valid_fields=sorted(valid_fields),
        )
        return {k: v for k, v in data.items() if k in valid_fields}

    return data


__all__ = [
    "build_batch_verdict_schema",
    "build_verdict_schema",
    "parse_location",
    "validate_location_fields",
]
