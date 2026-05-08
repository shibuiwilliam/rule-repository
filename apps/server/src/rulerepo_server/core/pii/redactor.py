"""Field-path-based PII redaction for subject facts.

Complements the pattern-based sanitizer in ``core/pii/__init__.py``.
This module handles explicit PII field marking: subjects declare which
JSON paths contain PII, and this function replaces those values with
traceable ``[REDACTED:field:id]`` placeholders.  A redaction map is
retained so that originals can be restored when legitimately needed.

See CLAUDE.md section 14.4.
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PIIClassification(StrEnum):
    """Sensitivity tiers for PII data.

    Ordered from least to most sensitive.  Used to decide encryption
    strength, retention policy, and access requirements.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"
    PII_SPECIAL = "pii_special"


@dataclass(frozen=True, slots=True)
class RedactionResult:
    """Outcome of a redaction operation.

    Attributes:
        redacted_data: Deep copy of the input with PII fields replaced
            by ``[REDACTED:field_name:short_id]`` placeholders.
        redaction_map: Mapping from each placeholder string to the
            original value it replaced.  Must be encrypted before
            persistence.
        redaction_id: Unique identifier for this redaction batch.
            Used as the correlation key in the shadow store.
    """

    redacted_data: dict[str, Any]
    redaction_map: dict[str, Any]
    redaction_id: str


# ---------------------------------------------------------------------------
# PII-name heuristics for auto-detection
# ---------------------------------------------------------------------------

_PII_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bssn\b"),
    re.compile(r"(?i)\bsocial.?security"),
    re.compile(r"(?i)\be?mail\b"),
    re.compile(r"(?i)\bphone\b"),
    re.compile(r"(?i)\bmobile\b"),
    re.compile(r"(?i)\bfax\b"),
    re.compile(r"(?i)\baddress\b"),
    re.compile(r"(?i)\bzip.?code\b"),
    re.compile(r"(?i)\bpostal.?code\b"),
    re.compile(r"(?i)\b(first|last|full|middle).?name\b"),
    re.compile(r"(?i)\bname\b"),
    re.compile(r"(?i)\bbirthday\b"),
    re.compile(r"(?i)\bbirth.?date\b"),
    re.compile(r"(?i)\bdate.?of.?birth\b"),
    re.compile(r"(?i)\bdob\b"),
    re.compile(r"(?i)\bpassport\b"),
    re.compile(r"(?i)\bdriver.?licen[sc]e\b"),
    re.compile(r"(?i)\bnational.?id\b"),
    re.compile(r"(?i)\bmy.?number\b"),
    re.compile(r"(?i)\bcredit.?card\b"),
    re.compile(r"(?i)\bcard.?number\b"),
    re.compile(r"(?i)\baccount.?number\b"),
    re.compile(r"(?i)\biban\b"),
    re.compile(r"(?i)\bip.?address\b"),
    re.compile(r"(?i)\bsalary\b"),
    re.compile(r"(?i)\bcompensation\b"),
    re.compile(r"(?i)\bemployee.?id\b"),
    re.compile(r"(?i)\btax.?id\b"),
    re.compile(r"(?i)\btin\b"),
    re.compile(r"(?i)\bmedical\b"),
    re.compile(r"(?i)\bhealth\b"),
    re.compile(r"(?i)\bdiagnosis\b"),
    re.compile(r"(?i)\bethnicity\b"),
    re.compile(r"(?i)\breligion\b"),
    re.compile(r"(?i)\bsexual.?orientation\b"),
    re.compile(r"(?i)\bunion.?membership\b"),
    re.compile(r"(?i)\bbiometric\b"),
    re.compile(r"(?i)\bgenetic\b"),
]


# Legacy constant kept for backward compatibility with callers that
# import it directly.
_REDACTED = "[REDACTED]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def redact(
    data: dict[str, Any],
    pii_paths: list[str],
    classification: str = "internal",
) -> RedactionResult:
    """Replace PII fields with traceable placeholders.

    Each redacted value is replaced with a string of the form
    ``[REDACTED:field_name:short_id]`` so that log readers can tell
    *which* field was removed without seeing the value.

    Args:
        data: The dictionary (typically subject facts) to redact.
        pii_paths: List of dot-separated field paths to redact.
        classification: The data classification level.  Higher levels
            receive the same placeholder format but may trigger
            additional audit logging upstream.

    Returns:
        A :class:`RedactionResult` containing redacted data, the
        reverse mapping, and a batch identifier.
    """
    redaction_id = uuid.uuid4().hex[:16]
    redacted = copy.deepcopy(data)
    redaction_map: dict[str, Any] = {}

    for field_path in pii_paths:
        parts = field_path.split(".")
        original = _get_nested(data, parts)
        if original is _SENTINEL:
            continue
        short_id = uuid.uuid4().hex[:8]
        leaf = parts[-1]
        placeholder = f"[REDACTED:{leaf}:{short_id}]"
        _set_nested(redacted, parts, placeholder)
        redaction_map[placeholder] = original

    return RedactionResult(
        redacted_data=redacted,
        redaction_map=redaction_map,
        redaction_id=redaction_id,
    )


def restore(redacted_data: dict[str, Any], redaction_map: dict[str, Any]) -> dict[str, Any]:
    """Reverse a redaction using the stored mapping.

    Walks the entire data structure and replaces any placeholder
    string found in *redaction_map* with its original value.

    Args:
        redacted_data: Data previously redacted by :func:`redact`.
        redaction_map: The ``redaction_map`` from the corresponding
            :class:`RedactionResult`.

    Returns:
        A deep copy of the data with original PII values restored.
    """
    restored = copy.deepcopy(redacted_data)
    _restore_recursive(restored, redaction_map)
    return restored


def detect_pii(data: dict[str, Any]) -> list[str]:
    """Auto-detect potential PII fields by inspecting key names.

    Walks the dictionary recursively and returns dot-separated paths
    for any key whose name matches common PII patterns (e.g. ``ssn``,
    ``email``, ``phone``, ``address``, ``name``).

    This is a heuristic aid, not a guarantee.  Callers should review
    the results and may supplement with explicit ``pii_fields`` lists.

    Args:
        data: Dictionary to scan.

    Returns:
        List of dot-separated paths to suspected PII fields.
    """
    results: list[str] = []
    _detect_recursive(data, [], results)
    return results


# ---------------------------------------------------------------------------
# Legacy helper — kept for backward compatibility
# ---------------------------------------------------------------------------


def redact_pii(data: dict[str, Any], pii_fields: list[str]) -> dict[str, Any]:
    """Replace PII fields with simple ``[REDACTED]`` placeholders.

    This is the original, non-traceable redaction function retained for
    backward compatibility.  New code should prefer :func:`redact`.

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SENTINEL = object()


def _get_nested(obj: Any, parts: list[str]) -> Any:
    """Walk into *obj* along *parts* and return the leaf value, or _SENTINEL."""
    current = obj
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return _SENTINEL
        current = current[part]
    return current


def _set_nested(obj: Any, parts: list[str], value: Any) -> None:
    """Walk into *obj* along *parts* and set the leaf to *value*."""
    current = obj
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts[-1] in current:
        current[parts[-1]] = value


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
        obj[key] = _REDACTED
    else:
        _redact_path(obj[key], parts[1:])


def _restore_recursive(obj: Any, redaction_map: dict[str, Any]) -> None:
    """Recursively replace placeholder strings with originals."""
    if isinstance(obj, dict):
        for key in obj:
            if isinstance(obj[key], str) and obj[key] in redaction_map:
                obj[key] = redaction_map[obj[key]]
            elif isinstance(obj[key], dict | list):
                _restore_recursive(obj[key], redaction_map)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item in redaction_map:
                obj[i] = redaction_map[item]
            elif isinstance(item, dict | list):
                _restore_recursive(item, redaction_map)


def _detect_recursive(
    obj: Any,
    prefix: list[str],
    results: list[str],
) -> None:
    """Recursively scan dict keys for PII-like names."""
    if not isinstance(obj, dict):
        return
    for key, value in obj.items():
        path = [*prefix, key]
        if any(pattern.search(key) for pattern in _PII_NAME_PATTERNS):
            results.append(".".join(path))
        if isinstance(value, dict):
            _detect_recursive(value, path, results)
