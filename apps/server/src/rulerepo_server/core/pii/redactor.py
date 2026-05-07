"""Field-path-based PII redaction for subject facts.

Complements the pattern-based sanitizer in ``core/pii/__init__.py``.
This module handles explicit PII field marking: subjects declare which
JSON paths contain PII, and this function replaces those values with
``[REDACTED]`` placeholders.

See CLAUDE.md section 14.4.
"""

from __future__ import annotations

import copy
from typing import Any

_REDACTED = "[REDACTED]"


def redact_pii(data: dict[str, Any], pii_fields: list[str]) -> dict[str, Any]:
    """Replace PII fields with placeholders.

    Handles dotted paths like ``"employee.ssn"`` by walking into nested
    dicts and replacing the leaf value with ``[REDACTED]``.

    Args:
        data: The dictionary (typically subject facts) to redact.
        pii_fields: List of dot-separated field paths to redact.

    Returns:
        A deep copy of *data* with PII fields replaced by ``[REDACTED]``.
        The original dict is not modified.
    """
    redacted = copy.deepcopy(data)
    for field_path in pii_fields:
        parts = field_path.split(".")
        _redact_path(redacted, parts)
    return redacted


def _redact_path(obj: Any, parts: list[str]) -> None:
    """Walk into a nested dict along *parts* and replace the leaf with [REDACTED].

    Silently skips if any intermediate key is missing or the value is not
    a dict where a dict is expected.
    """
    if not parts:
        return

    key = parts[0]

    if not isinstance(obj, dict):
        return

    if key not in obj:
        return

    if len(parts) == 1:
        # Leaf -- replace with redaction marker.
        obj[key] = _REDACTED
    else:
        # Intermediate -- recurse.
        _redact_path(obj[key], parts[1:])
