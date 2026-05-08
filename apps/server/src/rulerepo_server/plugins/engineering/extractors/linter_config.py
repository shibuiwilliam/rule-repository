"""Extractor for linter configuration files.

Maps linter rules from .eslintrc, ruff.toml, pyproject.toml [tool.ruff],
.pylintrc, and similar files into natural-language rule candidates.

See: CLAUDE.md SS16
"""

from __future__ import annotations

import json
import re
from typing import Any

# Well-known ruff rule prefixes and their natural-language descriptions
_RUFF_RULE_DESCRIPTIONS: dict[str, str] = {
    "E": "PEP 8 style violation",
    "W": "PEP 8 warning",
    "F": "Pyflakes logical error",
    "I": "Import ordering convention",
    "N": "PEP 8 naming convention",
    "D": "Docstring convention",
    "UP": "Python upgrade opportunity",
    "S": "Security issue (Bandit)",
    "B": "Bug risk (flake8-bugbear)",
    "A": "Built-in shadowing",
    "C4": "Comprehension style",
    "DTZ": "Datetime timezone handling",
    "T20": "Print statement usage",
    "PT": "Pytest style",
    "SIM": "Code simplification opportunity",
    "TCH": "Type-checking import optimization",
    "ARG": "Unused argument",
    "ERA": "Commented-out code",
    "PL": "Pylint convention",
    "RUF": "Ruff-specific rule",
}

# Well-known ESLint rule descriptions
_ESLINT_RULE_DESCRIPTIONS: dict[str, str] = {
    "no-unused-vars": "Variables must be used after declaration",
    "no-console": "Console statements should not appear in production code",
    "no-debugger": "Debugger statements must not appear in production code",
    "eqeqeq": "Always use strict equality (=== and !==)",
    "no-var": "Use let or const instead of var",
    "prefer-const": "Use const for variables that are never reassigned",
    "no-eval": "Never use eval() due to security risks",
    "no-implied-eval": "Avoid implied eval through setTimeout/setInterval strings",
    "curly": "Always use curly braces for control flow statements",
    "no-throw-literal": "Only throw Error objects",
    "no-return-await": "Avoid unnecessary return await",
    "prefer-template": "Use template literals instead of string concatenation",
    "no-shadow": "Avoid variable shadowing in nested scopes",
    "no-use-before-define": "Define variables before using them",
    "@typescript-eslint/no-explicit-any": "Avoid using the any type",
    "@typescript-eslint/explicit-function-return-type": "Functions should have explicit return types",
    "@typescript-eslint/no-non-null-assertion": "Avoid non-null assertions (!)",
    "@typescript-eslint/strict-boolean-expressions": "Use strict boolean expressions in conditions",
}


def _severity_from_level(level: Any) -> str:
    """Map a linter rule level to a rule severity.

    Args:
        level: Linter rule level (0/off, 1/warn, 2/error, or string).

    Returns:
        Rule severity string.
    """
    if isinstance(level, str):
        level = level.lower()
    if level in (2, "error"):
        return "HIGH"
    if level in (1, "warn", "warning"):
        return "MEDIUM"
    return "LOW"


def _modality_from_level(level: Any) -> str:
    """Map a linter rule level to a rule modality.

    Args:
        level: Linter rule level.

    Returns:
        Rule modality string.
    """
    if isinstance(level, str):
        level = level.lower()
    if level in (2, "error"):
        return "MUST"
    if level in (1, "warn", "warning"):
        return "SHOULD"
    return "MAY"


def _parse_eslintrc(content: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse ESLint configuration and extract rule candidates.

    Args:
        content: ESLint config file content (JSON or JS-like).
        metadata: File metadata.

    Returns:
        List of candidate rule dicts.
    """
    candidates: list[dict[str, Any]] = []

    try:
        # Try parsing as JSON (handles .eslintrc.json and .eslintrc)
        config = json.loads(content)
    except json.JSONDecodeError:
        # Try extracting rules from JS-style config
        rules_match = re.search(r'"rules"\s*:\s*\{([^}]+)\}', content)
        if not rules_match:
            return candidates
        try:
            config = {"rules": json.loads("{" + rules_match.group(1) + "}")}
        except json.JSONDecodeError:
            return candidates

    rules = config.get("rules", {})
    for rule_name, rule_config in rules.items():
        # Extract level from config (can be int, string, or array)
        level = rule_config[0] if isinstance(rule_config, list) else rule_config

        if level in (0, "off"):
            continue

        description = _ESLINT_RULE_DESCRIPTIONS.get(
            rule_name,
            f"ESLint rule '{rule_name}' must be followed",
        )

        candidates.append(
            {
                "statement": description,
                "modality": _modality_from_level(level),
                "severity": _severity_from_level(level),
                "scope": ["engineering/typescript", "engineering/javascript"],
                "rationale": (
                    f"Derived from ESLint rule '{rule_name}' configured at "
                    f"level '{level}' in {metadata.get('filename', '.eslintrc')}."
                ),
                "source": {
                    "type": "eslint_config",
                    "filename": metadata.get("filename", ".eslintrc"),
                    "rule_id": rule_name,
                    "level": str(level),
                },
                "tags": ["auto-extracted", "linter", "eslint"],
                "applicable_subject_types": ["code_diff"],
            }
        )

    return candidates


def _parse_ruff_toml(content: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse ruff configuration and extract rule candidates.

    Handles both standalone ruff.toml and [tool.ruff] sections in
    pyproject.toml.

    Args:
        content: Configuration file content.
        metadata: File metadata.

    Returns:
        List of candidate rule dicts.
    """
    candidates: list[dict[str, Any]] = []

    # Extract selected rules from select = ["E", "F", ...]
    select_match = re.search(r"select\s*=\s*\[([^\]]+)\]", content)
    if not select_match:
        return candidates

    raw_rules = select_match.group(1)
    rule_ids = re.findall(r'"([^"]+)"', raw_rules)

    for rule_id in rule_ids:
        # Find the matching prefix for a description
        description = None
        for prefix, desc in _RUFF_RULE_DESCRIPTIONS.items():
            if rule_id == prefix or rule_id.startswith(prefix):
                description = f"Python code must comply with {desc} checks ({rule_id})"
                break

        if description is None:
            description = f"Python code must comply with ruff rule {rule_id}"

        candidates.append(
            {
                "statement": description,
                "modality": "MUST",
                "severity": "MEDIUM",
                "scope": ["engineering/python"],
                "rationale": (
                    f"Derived from ruff rule '{rule_id}' configured in "
                    f"{metadata.get('filename', 'ruff.toml')}. "
                    f"Rules selected in the linter config represent team conventions."
                ),
                "source": {
                    "type": "ruff_config",
                    "filename": metadata.get("filename", "ruff.toml"),
                    "rule_id": rule_id,
                },
                "tags": ["auto-extracted", "linter", "ruff"],
                "applicable_subject_types": ["code_diff"],
            }
        )

    # Extract ignored rules to note exceptions
    ignore_match = re.search(r"ignore\s*=\s*\[([^\]]+)\]", content)
    if ignore_match:
        raw_ignores = ignore_match.group(1)
        ignore_ids = re.findall(r'"([^"]+)"', raw_ignores)
        for rule_id in ignore_ids:
            for prefix, desc in _RUFF_RULE_DESCRIPTIONS.items():
                if rule_id == prefix or rule_id.startswith(prefix):
                    candidates.append(
                        {
                            "statement": (f"{desc} check ({rule_id}) is explicitly disabled for this project"),
                            "modality": "INFO",
                            "severity": "LOW",
                            "scope": ["engineering/python"],
                            "rationale": (
                                f"Rule '{rule_id}' is in the ignore list of "
                                f"{metadata.get('filename', 'ruff.toml')}. "
                                f"Documenting explicit exceptions."
                            ),
                            "source": {
                                "type": "ruff_config",
                                "filename": metadata.get("filename", "ruff.toml"),
                                "rule_id": rule_id,
                                "status": "ignored",
                            },
                            "tags": ["auto-extracted", "linter", "ruff", "exception"],
                            "applicable_subject_types": ["code_diff"],
                        }
                    )
                    break

    return candidates


def _detect_config_type(filename: str) -> str | None:
    """Detect the linter config type from the filename.

    Args:
        filename: Name of the configuration file.

    Returns:
        Config type string, or None if unrecognized.
    """
    lower = filename.lower()
    if "eslint" in lower:
        return "eslint"
    if lower in ("ruff.toml", ".ruff.toml"):
        return "ruff"
    if lower == "pyproject.toml":
        return "ruff"  # check for [tool.ruff] section
    return None


class LinterConfigExtractor:
    """Extracts rule candidates from linter configuration files.

    Supports ESLint (.eslintrc, .eslintrc.json, .eslintrc.js) and
    ruff (ruff.toml, pyproject.toml) configurations. Maps linter rules
    to natural-language rule candidates with appropriate modality,
    severity, and scope.
    """

    @property
    def name(self) -> str:
        return "linter_config"

    @property
    def domain(self) -> str:
        return "engineering"

    @property
    def supported_source_types(self) -> list[str]:
        return ["eslint_config", "ruff_config", "linter_config"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract rule candidates from a linter configuration file.

        Args:
            content: Raw bytes of the configuration file.
            source_type: One of 'eslint_config', 'ruff_config', 'linter_config'.
            metadata: Additional metadata (must include 'filename').

        Returns:
            List of candidate rule dicts.
        """
        text = content.decode("utf-8", errors="replace")
        filename = metadata.get("filename", "")

        if source_type == "eslint_config" or (
            source_type == "linter_config" and _detect_config_type(filename) == "eslint"
        ):
            return _parse_eslintrc(text, metadata)

        if source_type == "ruff_config" or (source_type == "linter_config" and _detect_config_type(filename) == "ruff"):
            return _parse_ruff_toml(text, metadata)

        # Unknown config type: try both parsers
        candidates = _parse_eslintrc(text, metadata)
        if not candidates:
            candidates = _parse_ruff_toml(text, metadata)

        return candidates
