"""Subject adapter registry — maps SubjectKind to adapter classes.

Uses a ``@register(SubjectKind.X)`` decorator pattern so that adding a
new domain means adding one module, not modifying the orchestrator.

See: CLAUDE.md §11.2
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.errors import RuleRepoError
from rulerepo_server.domain.subject import SubjectKind


class UnsupportedSubjectKindError(RuleRepoError):
    """Raised when no adapter is registered for the requested SubjectKind."""

    def __init__(self, kind: SubjectKind | str) -> None:
        self.kind = kind
        super().__init__(f"No adapter registered for subject kind: {kind}")


_REGISTRY: dict[SubjectKind, type] = {}


def register(kind: SubjectKind):
    """Decorator to register a subject adapter class for a given SubjectKind.

    Usage::

        @register(SubjectKind.CODE_DIFF)
        class CodeDiffAdapter:
            kind = SubjectKind.CODE_DIFF
            ...

    Args:
        kind: The SubjectKind this adapter handles.

    Returns:
        The class, unmodified.
    """

    def decorator(cls: type) -> type:
        _REGISTRY[kind] = cls
        return cls

    return decorator


def resolve(kind: SubjectKind | str) -> Any:
    """Get a fresh adapter instance for the given SubjectKind.

    Args:
        kind: The SubjectKind enum value or its string equivalent.

    Returns:
        An instance of the registered adapter.

    Raises:
        UnsupportedSubjectKindError: If no adapter is registered for ``kind``.
    """
    if isinstance(kind, str):
        try:
            kind = SubjectKind(kind)
        except ValueError as exc:
            raise UnsupportedSubjectKindError(kind) from exc

    try:
        return _REGISTRY[kind]()
    except KeyError as exc:
        raise UnsupportedSubjectKindError(kind) from exc


def list_registered() -> dict[SubjectKind, type]:
    """Return all registered adapters."""
    return dict(_REGISTRY)


# --- Backward-compatible aliases ---


def register_adapter(adapter: Any) -> None:
    """Legacy: register an already-instantiated adapter by its subject_type property."""
    kind_str = getattr(adapter, "subject_type", None) or getattr(adapter, "kind", None)
    if kind_str is None:
        msg = "Adapter must have a 'kind' or 'subject_type' attribute"
        raise TypeError(msg)
    if isinstance(kind_str, str):
        kind_str = SubjectKind(kind_str)
    _REGISTRY[kind_str] = type(adapter)


def get_adapter(subject_type: str) -> Any | None:
    """Legacy: get adapter instance by string key. Returns None if missing."""
    try:
        return resolve(subject_type)
    except UnsupportedSubjectKindError:
        return None
