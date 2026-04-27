"""Analyzer for linter and tool configuration files.

Detects ruff, ESLint, tsconfig, and similar tool configs, translating
their settings into candidate rule statements.
"""

from __future__ import annotations

import json
import re
import tomllib

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import (
    DiscoveryContext,
    RawPattern,
    SourceAnalyzer,
)

logger = get_logger(__name__)

_RUFF_TOML_PATTERN = re.compile(r"(^|/)ruff\.toml$")
_PYPROJECT_TOML_PATTERN = re.compile(r"(^|/)pyproject\.toml$")
_ESLINTRC_PATTERN = re.compile(r"(^|/)\.eslintrc(\.json)?$")
_TSCONFIG_PATTERN = re.compile(r"(^|/)tsconfig\.json$")


class LinterConfigAnalyzer(SourceAnalyzer):
    """Extracts candidate rules from linter and tool configuration files.

    Supports ruff.toml, pyproject.toml [tool.ruff], .eslintrc/.eslintrc.json,
    and tsconfig.json. Translates config settings into structured rule statements.
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze linter config files for candidate rules.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns extracted from config files.
        """
        patterns: list[RawPattern] = []

        for path, content in context.file_contents.items():
            try:
                if _RUFF_TOML_PATTERN.search(path):
                    patterns.extend(self._parse_ruff_toml(path, content))
                elif _PYPROJECT_TOML_PATTERN.search(path):
                    patterns.extend(self._parse_pyproject_ruff(path, content))
                elif _ESLINTRC_PATTERN.search(path):
                    patterns.extend(self._parse_eslintrc(path, content))
                elif _TSCONFIG_PATTERN.search(path):
                    patterns.extend(self._parse_tsconfig(path, content))
            except Exception:
                logger.warning("linter_config_parse_error", path=path, exc_info=True)

        logger.info("linter_config_analysis_complete", pattern_count=len(patterns))
        return patterns

    def _parse_ruff_toml(self, path: str, content: str) -> list[RawPattern]:
        """Parse a standalone ruff.toml file.

        Args:
            path: File path for provenance.
            content: TOML content.

        Returns:
            List of patterns from ruff config.
        """
        try:
            data = tomllib.loads(content)
        except Exception:
            logger.warning("ruff_toml_parse_error", path=path, exc_info=True)
            return []
        return self._extract_ruff_patterns(path, data)

    def _parse_pyproject_ruff(self, path: str, content: str) -> list[RawPattern]:
        """Parse [tool.ruff] section from pyproject.toml.

        Args:
            path: File path for provenance.
            content: TOML content.

        Returns:
            List of patterns from ruff config within pyproject.toml.
        """
        try:
            data = tomllib.loads(content)
        except Exception:
            logger.warning("pyproject_toml_parse_error", path=path, exc_info=True)
            return []

        ruff_config = data.get("tool", {}).get("ruff", {})
        if not ruff_config:
            return []
        return self._extract_ruff_patterns(path, ruff_config)

    def _extract_ruff_patterns(self, path: str, config: dict) -> list[RawPattern]:
        """Extract rule patterns from parsed ruff configuration.

        Args:
            path: Source file path.
            config: Parsed ruff config dict.

        Returns:
            List of raw patterns.
        """
        patterns: list[RawPattern] = []

        # Line length
        line_length = config.get("line-length") or config.get("line_length")
        if line_length:
            patterns.append(
                RawPattern(
                    statement=f"Python code lines MUST NOT exceed {line_length} characters.",
                    modality="MUST_NOT",
                    severity="MEDIUM",
                    scope=["python"],
                    tags=["formatting", "ruff"],
                    source_type="linter_config",
                    source_evidence=f"line-length = {line_length} in {path}",
                    confidence=0.85,
                )
            )

        # Target version
        target_version = config.get("target-version") or config.get("target_version")
        if target_version:
            patterns.append(
                RawPattern(
                    statement=f"Python code MUST target Python {target_version} or newer.",
                    modality="MUST",
                    severity="HIGH",
                    scope=["python"],
                    tags=["compatibility", "ruff"],
                    source_type="linter_config",
                    source_evidence=f"target-version = {target_version!r} in {path}",
                    confidence=0.85,
                )
            )

        # Selected lint rules
        lint_config = config.get("lint", {})
        selected = lint_config.get("select", config.get("select", []))
        if selected:
            rule_codes = ", ".join(selected) if isinstance(selected, list) else str(selected)
            patterns.append(
                RawPattern(
                    statement=f"Python code MUST pass ruff linting with rule codes: {rule_codes}.",
                    modality="MUST",
                    severity="HIGH",
                    scope=["python"],
                    tags=["linting", "ruff"],
                    source_type="linter_config",
                    source_evidence=f"select = {selected!r} in {path}",
                    confidence=0.85,
                )
            )

        # General ruff enforcement
        if not patterns and config:
            patterns.append(
                RawPattern(
                    statement="Python code MUST pass ruff linting.",
                    modality="MUST",
                    severity="HIGH",
                    scope=["python"],
                    tags=["linting", "ruff"],
                    source_type="linter_config",
                    source_evidence=f"ruff config present in {path}",
                    confidence=0.85,
                )
            )

        return patterns

    def _parse_eslintrc(self, path: str, content: str) -> list[RawPattern]:
        """Parse .eslintrc or .eslintrc.json for ESLint rules.

        Args:
            path: File path for provenance.
            content: JSON content.

        Returns:
            List of patterns from ESLint config.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("eslintrc_parse_error", path=path, exc_info=True)
            return []

        patterns: list[RawPattern] = []
        rules = data.get("rules", {})

        error_rules: list[str] = []
        for rule_name, rule_value in rules.items():
            # ESLint rules: "error" or 2 means enforced
            is_list_error = (
                isinstance(rule_value, list)
                and len(rule_value) > 0
                and rule_value[0] in ("error", 2)
            )
            if rule_value == "error" or rule_value == 2 or is_list_error:
                error_rules.append(rule_name)

        if error_rules:
            for rule_name in error_rules:
                patterns.append(
                    RawPattern(
                        statement=f"Code MUST NOT violate ESLint rule: {rule_name}.",
                        modality="MUST_NOT",
                        severity="MEDIUM",
                        scope=["typescript", "javascript"],
                        tags=["linting", "eslint"],
                        source_type="linter_config",
                        source_evidence=f"ESLint rule {rule_name} set to error in {path}",
                        confidence=0.85,
                    )
                )

        # General ESLint enforcement
        if not error_rules and rules:
            patterns.append(
                RawPattern(
                    statement="TypeScript/JavaScript code MUST pass ESLint linting.",
                    modality="MUST",
                    severity="MEDIUM",
                    scope=["typescript", "javascript"],
                    tags=["linting", "eslint"],
                    source_type="linter_config",
                    source_evidence=f"ESLint config present in {path}",
                    confidence=0.85,
                )
            )

        return patterns

    def _parse_tsconfig(self, path: str, content: str) -> list[RawPattern]:
        """Parse tsconfig.json for TypeScript strictness settings.

        Args:
            path: File path for provenance.
            content: JSON content.

        Returns:
            List of patterns from tsconfig.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("tsconfig_parse_error", path=path, exc_info=True)
            return []

        patterns: list[RawPattern] = []
        compiler_options = data.get("compilerOptions", {})

        if compiler_options.get("strict") is True:
            patterns.append(
                RawPattern(
                    statement="TypeScript MUST use strict type checking.",
                    modality="MUST",
                    severity="HIGH",
                    scope=["typescript"],
                    tags=["type_safety", "tsconfig"],
                    source_type="linter_config",
                    source_evidence=f'"strict": true in {path}',
                    confidence=0.85,
                )
            )

        if compiler_options.get("noImplicitAny") is True:
            patterns.append(
                RawPattern(
                    statement="TypeScript MUST NOT use implicit 'any' types.",
                    modality="MUST_NOT",
                    severity="HIGH",
                    scope=["typescript"],
                    tags=["type_safety", "tsconfig"],
                    source_type="linter_config",
                    source_evidence=f'"noImplicitAny": true in {path}',
                    confidence=0.85,
                )
            )

        if compiler_options.get("noUnusedLocals") is True:
            patterns.append(
                RawPattern(
                    statement="TypeScript MUST NOT contain unused local variables.",
                    modality="MUST_NOT",
                    severity="MEDIUM",
                    scope=["typescript"],
                    tags=["code_quality", "tsconfig"],
                    source_type="linter_config",
                    source_evidence=f'"noUnusedLocals": true in {path}',
                    confidence=0.85,
                )
            )

        return patterns
