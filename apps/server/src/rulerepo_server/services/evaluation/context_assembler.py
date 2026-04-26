"""Context Assembler — normalizes various inputs into a unified EvaluationContext.

Per CLAUDE_ENHANCE.md §1.4.1: supports diff mode, file mode, facts mode, and hybrid.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext, FileChange
from rulerepo_server.services.evaluation.diff_parser import (
    detect_language,
    parse_unified_diff,
)


def assemble_context(
    *,
    diff: str | None = None,
    files: list[dict[str, str]] | None = None,
    facts: dict[str, Any] | None = None,
    intent: str | None = None,
    scope: str | None = None,
    repository: str | None = None,
    actor: str | None = None,
) -> EvaluationContext:
    """Build an EvaluationContext from various input modes.

    Args:
        diff: Unified diff text (diff mode).
        files: List of {"path": ..., "content": ...} dicts (file mode).
        facts: Key-value pairs (facts mode).
        intent: Natural language description of the change.
        scope: Rule scope filter.
        repository: Repository identifier.
        actor: Who triggered the evaluation.

    Returns:
        A unified EvaluationContext.
    """
    files_changed: list[FileChange] = []
    file_paths: list[str] = []
    languages: set[str] = set()

    # Diff mode: parse the unified diff
    if diff:
        files_changed = parse_unified_diff(diff)
        file_paths = [f.path for f in files_changed]
        languages = {f.language for f in files_changed if f.language}

    # File mode: extract paths and languages from file list
    if files:
        for f in files:
            path = f.get("path", "")
            if path and path not in file_paths:
                file_paths.append(path)
                lang = detect_language(path)
                if lang:
                    languages.add(lang)
                files_changed.append(
                    FileChange(
                        path=path,
                        change_type="modified",
                        language=lang,
                    )
                )

    # Build narrative from intent and facts for non-code evaluations
    narrative = intent
    if facts and not narrative:
        fact_lines = [f"{k}: {v}" for k, v in facts.items()]
        narrative = "; ".join(fact_lines)

    return EvaluationContext(
        diff=diff,
        files_changed=files_changed,
        file_paths=file_paths,
        languages=sorted(languages),
        repository=repository,
        intent=intent,
        actor=actor,
        facts=facts or {},
        narrative=narrative,
    )
