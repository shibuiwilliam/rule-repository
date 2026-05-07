"""Subject adapter registry — maps SubjectType to adapter instances."""

from __future__ import annotations

from rulerepo_server.subjects.base import SubjectAdapter

_REGISTRY: dict[str, SubjectAdapter] = {}


def register_adapter(adapter: SubjectAdapter) -> None:
    """Register a subject adapter.

    Args:
        adapter: An adapter implementing the SubjectAdapter protocol.
    """
    _REGISTRY[adapter.subject_type] = adapter


def get_adapter(subject_type: str) -> SubjectAdapter | None:
    """Get the adapter for a subject type.

    Args:
        subject_type: The SubjectType string.

    Returns:
        The adapter, or None if not registered.
    """
    return _REGISTRY.get(subject_type)


def list_adapters() -> dict[str, SubjectAdapter]:
    """Return all registered adapters."""
    return dict(_REGISTRY)
