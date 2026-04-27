"""Analyzer for code convention patterns detected via simple static analysis.

Uses regex-based heuristics (no AST parsing) to detect prevalent conventions
such as test file naming, common imports, and docstring presence.
"""

from __future__ import annotations

import re
from collections import defaultdict

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import (
    DiscoveryContext,
    RawPattern,
    SourceAnalyzer,
)

logger = get_logger(__name__)

# Patterns for analysis
_TEST_FILE_PATTERN = re.compile(r"(^|/)test_[^/]+\.py$")
_PY_FILE_PATTERN = re.compile(r"\.py$")
_PUBLIC_FUNC_PATTERN = re.compile(r"^def\s+([a-z_][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)
_DOCSTRING_AFTER_DEF = re.compile(
    r"^def\s+[a-z_][a-zA-Z0-9_]*\s*\([^)]*\)[^:]*:\s*\n\s+\"\"\"", re.MULTILINE
)
_IMPORT_PATTERN = re.compile(r"^(?:from\s+(\S+)|import\s+(\S+))", re.MULTILINE)

# Minimum number of files needed to detect a pattern
_MIN_FILES_FOR_PATTERN = 3

# Threshold for considering a pattern prevalent
_PREVALENCE_THRESHOLD = 0.8


class CodePatternsAnalyzer(SourceAnalyzer):
    """Detects code convention patterns from file contents.

    Examines file naming conventions, import patterns, and docstring usage
    across Python files to discover implicit project rules.
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze code files for prevalent convention patterns.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns representing detected conventions.
        """
        patterns: list[RawPattern] = []

        py_files = {
            path: content
            for path, content in context.file_contents.items()
            if _PY_FILE_PATTERN.search(path)
        }

        if len(py_files) < _MIN_FILES_FOR_PATTERN:
            logger.debug("code_patterns_insufficient_files", count=len(py_files))
            return patterns

        patterns.extend(self._analyze_test_naming(py_files))
        patterns.extend(self._analyze_docstrings(py_files))
        patterns.extend(self._analyze_imports(py_files))

        logger.info("code_patterns_analysis_complete", pattern_count=len(patterns))
        return patterns

    def _analyze_test_naming(self, py_files: dict[str, str]) -> list[RawPattern]:
        """Check if test files follow the test_*.py naming convention.

        Args:
            py_files: Mapping of Python file paths to contents.

        Returns:
            List of patterns if the convention is prevalent.
        """
        test_files = [p for p in py_files if "test" in p.lower()]
        if len(test_files) < _MIN_FILES_FOR_PATTERN:
            return []

        matching = sum(1 for p in test_files if _TEST_FILE_PATTERN.search(p))
        ratio = matching / len(test_files) if test_files else 0.0

        if ratio >= _PREVALENCE_THRESHOLD:
            return [
                RawPattern(
                    statement="Test files SHOULD follow the test_*.py naming convention.",
                    modality="SHOULD",
                    severity="LOW",
                    scope=["python", "testing"],
                    tags=["naming", "testing"],
                    source_type="code_patterns",
                    source_evidence=(
                        f"{matching}/{len(test_files)} test files use test_*.py naming"
                    ),
                    confidence=ratio * 0.9,
                )
            ]
        return []

    def _analyze_docstrings(self, py_files: dict[str, str]) -> list[RawPattern]:
        """Check if public functions consistently have docstrings.

        Args:
            py_files: Mapping of Python file paths to contents.

        Returns:
            List of patterns if docstring usage is prevalent.
        """
        total_public_funcs = 0
        funcs_with_docstrings = 0

        for content in py_files.values():
            public_funcs = _PUBLIC_FUNC_PATTERN.findall(content)
            # Exclude private functions (starting with _)
            public_funcs = [f for f in public_funcs if not f.startswith("_")]
            total_public_funcs += len(public_funcs)
            funcs_with_docstrings += len(_DOCSTRING_AFTER_DEF.findall(content))

        if total_public_funcs < _MIN_FILES_FOR_PATTERN:
            return []

        ratio = funcs_with_docstrings / total_public_funcs if total_public_funcs else 0.0

        if ratio >= _PREVALENCE_THRESHOLD:
            return [
                RawPattern(
                    statement="Public functions SHOULD include docstrings.",
                    modality="SHOULD",
                    severity="LOW",
                    scope=["python"],
                    tags=["documentation", "docstrings"],
                    source_type="code_patterns",
                    source_evidence=(
                        f"{funcs_with_docstrings}/{total_public_funcs} public functions "
                        f"have docstrings ({ratio:.0%})"
                    ),
                    confidence=ratio * 0.9,
                )
            ]
        return []

    def _analyze_imports(self, py_files: dict[str, str]) -> list[RawPattern]:
        """Detect prevalent import patterns within directory groups.

        If >80% of files in the same directory import the same module,
        it suggests a project convention.

        Args:
            py_files: Mapping of Python file paths to contents.

        Returns:
            List of patterns for prevalent imports.
        """
        # Group files by directory
        dir_files: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for path, content in py_files.items():
            parts = path.rsplit("/", 1)
            directory = parts[0] if len(parts) > 1 else "."
            dir_files[directory].append((path, content))

        patterns: list[RawPattern] = []

        for directory, files in dir_files.items():
            if len(files) < _MIN_FILES_FOR_PATTERN:
                continue

            # Count import occurrences
            import_counts: dict[str, int] = defaultdict(int)
            for _, content in files:
                seen: set[str] = set()
                for match in _IMPORT_PATTERN.finditer(content):
                    module = match.group(1) or match.group(2)
                    root_module = module.split(".")[0]
                    if root_module not in seen:
                        seen.add(root_module)
                        import_counts[root_module] += 1

            file_count = len(files)
            for module, count in import_counts.items():
                ratio = count / file_count
                if ratio >= _PREVALENCE_THRESHOLD and module not in (
                    "__future__",
                    "os",
                    "sys",
                    "typing",
                    "re",
                    "json",
                ):
                    dir_name = directory.rsplit("/", 1)[-1]
                    patterns.append(
                        RawPattern(
                            statement=(f"Python files in {dir_name}/ SHOULD import '{module}'."),
                            modality="SHOULD",
                            severity="LOW",
                            scope=["python", dir_name],
                            tags=["imports", "conventions"],
                            source_type="code_patterns",
                            source_evidence=(
                                f"{count}/{file_count} files in {directory} import {module}"
                            ),
                            confidence=ratio * 0.9,
                        )
                    )

        return patterns
