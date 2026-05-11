"""Context Assembler — normalizes various inputs into a unified EvaluationContext.

Per CLAUDE_ENHANCE.md §1.4.1: supports diff mode, file mode, facts mode, and hybrid.
Polymorphic: builds surface-appropriate context for code, document, transaction,
and other subject kinds without requiring diff/file_path for non-code surfaces.

This module is **subject-agnostic** (CLAUDE.md rule #18). Code-specific parsing
(diff parsing, language detection) is performed by the code surface adapter
(``surfaces/code/``) and passed in via pre-assembled fields.  The shared
assembler never imports ``diff_parser`` directly.
"""

from __future__ import annotations

import json
from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext, FileChange
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind

# Surfaces that use the code-centric assembly path (diff + file paths).
_CODE_SURFACES = {"code", "code_diff"}


def assemble_context(
    *,
    diff: str | None = None,
    files: list[dict[str, str]] | None = None,
    facts: dict[str, Any] | None = None,
    intent: str | None = None,
    scope: str | None = None,
    repository: str | None = None,
    actor: str | None = None,
    surface: str | None = None,
    # Pre-assembled code fields — populated by the code surface adapter or
    # by the legacy backward-compatibility shim ``assemble_code_context()``.
    files_changed: list[FileChange] | None = None,
    file_paths: list[str] | None = None,
    languages: list[str] | None = None,
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
        surface: Surface type hint (e.g., "code", "transaction", "document").
        files_changed: Pre-parsed FileChange list (code surface adapter).
        file_paths: Pre-parsed file paths (code surface adapter).
        languages: Pre-parsed language list (code surface adapter).

    Returns:
        A unified EvaluationContext.
    """
    resolved_files_changed = list(files_changed) if files_changed else []
    resolved_file_paths = list(file_paths) if file_paths else []
    resolved_languages = set(languages) if languages else set()

    # For backward compatibility: when the legacy ``evaluate()`` path sends a
    # raw diff/files without pre-parsed fields and without an explicit surface,
    # delegate to the code-specific parser.  This keeps the shared assembler
    # free of top-level diff_parser imports while still supporting the old API.
    is_code = surface in _CODE_SURFACES or (surface is None and diff is not None)
    needs_parsing = is_code and not resolved_files_changed and (diff is not None or files is not None)

    if needs_parsing:
        resolved_files_changed, resolved_file_paths, resolved_languages = _parse_code_inputs(diff, files)

    # Build a surface-appropriate narrative.
    narrative = _build_narrative(
        surface=surface,
        intent=intent,
        facts=facts,
        diff=diff,
    )

    return EvaluationContext(
        diff=diff if is_code else None,
        files_changed=resolved_files_changed,
        file_paths=resolved_file_paths,
        languages=sorted(resolved_languages),
        repository=repository,
        intent=intent,
        actor=actor,
        facts=facts or {},
        narrative=narrative,
        surface=surface,
    )


def assemble_code_context(
    *,
    diff: str | None = None,
    files: list[dict[str, str]] | None = None,
    facts: dict[str, Any] | None = None,
    intent: str | None = None,
    repository: str | None = None,
    actor: str | None = None,
    scope: str | None = None,
) -> EvaluationContext:
    """Convenience wrapper for the code surface.

    Parses diff/files and feeds the pre-assembled results into the shared
    ``assemble_context()``.  Code-specific callers (the code surface adapter,
    the legacy ``evaluate()`` shim) should prefer this over calling
    ``assemble_context()`` with raw diff + surface='code'.
    """
    files_changed, file_paths, languages = _parse_code_inputs(diff, files)
    return assemble_context(
        diff=diff,
        files=files,
        facts=facts,
        intent=intent,
        scope=scope,
        repository=repository,
        actor=actor,
        surface="code",
        files_changed=files_changed,
        file_paths=file_paths,
        languages=list(languages),
    )


def _parse_code_inputs(
    diff: str | None,
    files: list[dict[str, str]] | None,
) -> tuple[list[FileChange], list[str], set[str]]:
    """Parse code-specific inputs (diff text and file lists).

    Lazy-imports ``diff_parser`` so the shared assembler has no top-level
    dependency on code-specific modules.
    """
    from rulerepo_server.services.evaluation.diff_parser import (
        detect_language,
        parse_unified_diff,
    )

    files_changed: list[FileChange] = []
    file_paths: list[str] = []
    languages: set[str] = set()

    if diff:
        files_changed = parse_unified_diff(diff)
        file_paths = [f.path for f in files_changed]
        languages = {f.language for f in files_changed if f.language}

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

    return files_changed, file_paths, languages


def assemble_context_from_subject(subject: EvaluationSubject) -> EvaluationContext:
    """Build an EvaluationContext directly from an EvaluationSubject.

    This is the preferred entry point for the polymorphic evaluation pipeline.
    It dispatches on ``subject.kind`` to build the right context without
    requiring callers to destructure the subject into diff/files/facts.

    Args:
        subject: The evaluation subject.

    Returns:
        A unified EvaluationContext.
    """
    kind = subject.kind
    payload = subject.payload
    context_extra = subject.context
    meta = subject.metadata

    surface = _subject_kind_to_surface(kind)

    match kind:
        case SubjectKind.CODE_DIFF:
            return assemble_context(
                diff=payload.get("diff"),
                files=payload.get("files"),
                facts=context_extra or None,
                intent=payload.get("intent") or meta.get("intent"),
                repository=payload.get("repository") or meta.get("repository"),
                actor=meta.get("actor"),
                surface=surface,
            )
        case SubjectKind.DOCUMENT:
            return assemble_context(
                facts={"document_text": payload.get("text", ""), **payload},
                intent=payload.get("description") or meta.get("intent"),
                actor=meta.get("actor"),
                surface=surface,
            )
        case SubjectKind.TRANSACTION:
            return assemble_context(
                facts=payload,
                intent=payload.get("description") or meta.get("intent"),
                actor=meta.get("actor"),
                surface=surface,
            )
        case SubjectKind.EVENT:
            return assemble_context(
                facts=payload,
                intent=payload.get("action") or meta.get("intent"),
                actor=meta.get("actor"),
                surface=surface,
            )
        case SubjectKind.CLAUSE_SET:
            return assemble_context(
                facts={"clause_text": payload.get("text", ""), **payload},
                intent=meta.get("intent"),
                actor=meta.get("actor"),
                surface=surface,
            )
        case _:
            # CREATIVE, DECISION, IDENTITY, and any future kinds
            return assemble_context(
                facts=payload,
                intent=meta.get("intent"),
                actor=meta.get("actor"),
                surface=surface,
            )


def _subject_kind_to_surface(kind: SubjectKind) -> str:
    """Map SubjectKind to the surface string used in EvaluationContext."""
    mapping: dict[SubjectKind, str] = {
        SubjectKind.CODE_DIFF: "code",
        SubjectKind.DOCUMENT: "document",
        SubjectKind.TRANSACTION: "transaction",
        SubjectKind.EVENT: "human_action",
        SubjectKind.CLAUSE_SET: "contract",
        SubjectKind.CREATIVE: "message",
        SubjectKind.DECISION: "generic",
        SubjectKind.IDENTITY: "generic",
    }
    return mapping.get(kind, "generic")


def _build_narrative(
    *,
    surface: str | None,
    intent: str | None,
    facts: dict[str, Any] | None,
    diff: str | None,
) -> str | None:
    """Build a surface-appropriate narrative string.

    For code surfaces the narrative is just the intent. For other surfaces the
    narrative should give the LLM a rich, structured text representation of the
    subject so that rule matching and evaluation work well even without
    file_paths/languages.
    """
    if intent and (surface in _CODE_SURFACES or surface is None):
        return intent

    parts: list[str] = []
    if intent:
        parts.append(intent)

    if not facts:
        return parts[0] if parts else None

    # Document surface: prefer full text in the narrative.
    if surface in {"document", "contract"}:
        doc_text = facts.get("document_text") or facts.get("clause_text") or facts.get("text")
        if doc_text:
            parts.append(str(doc_text))
        else:
            parts.append(_facts_to_text(facts))
    elif surface == "transaction":
        # Structured JSON summary for transactions.
        parts.append(json.dumps(facts, default=str, ensure_ascii=False))
    elif surface in {"human_action", "event"}:
        action = facts.get("action", "")
        if action:
            parts.append(f"Action: {action}")
        parts.append(_facts_to_text({k: v for k, v in facts.items() if k != "action"}))
    else:
        parts.append(_facts_to_text(facts))

    return "\n".join(p for p in parts if p) or None


def _facts_to_text(facts: dict[str, Any]) -> str:
    """Convert a dict of facts to a readable key: value string."""
    return "; ".join(f"{k}: {v}" for k, v in facts.items() if v is not None)
