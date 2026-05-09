"""Surface adapter registry — maps Surface enum values to adapter instances.

The evaluation core dispatches through this registry. Never hardcode
surface lists in core logic.

See CLAUDE.md §14.9.
"""

from __future__ import annotations

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

# Lazy-loaded registry to avoid import-time cost
_REGISTRY: dict[Surface, SurfaceAdapter] | None = None


def _build_registry() -> dict[Surface, SurfaceAdapter]:
    """Build the surface adapter registry on first access."""
    from rulerepo_server.services.evaluation.surfaces.code.adapter import (
        CodeSurfaceAdapter,
    )
    from rulerepo_server.services.evaluation.surfaces.contract.adapter import (
        ContractSurfaceAdapter,
    )
    from rulerepo_server.services.evaluation.surfaces.document.adapter import (
        DocumentSurfaceAdapter,
    )
    from rulerepo_server.services.evaluation.surfaces.generic.adapter import (
        GenericSurfaceAdapter,
    )
    from rulerepo_server.services.evaluation.surfaces.human_action.adapter import (
        HumanActionSurfaceAdapter,
    )
    from rulerepo_server.services.evaluation.surfaces.message.adapter import (
        MessageSurfaceAdapter,
    )
    from rulerepo_server.services.evaluation.surfaces.transaction.adapter import (
        TransactionSurfaceAdapter,
    )

    return {
        Surface.CODE: CodeSurfaceAdapter(),
        Surface.CONTRACT: ContractSurfaceAdapter(),
        Surface.HUMAN_ACTION: HumanActionSurfaceAdapter(),
        Surface.TRANSACTION: TransactionSurfaceAdapter(),
        Surface.DOCUMENT: DocumentSurfaceAdapter(),
        Surface.MESSAGE: MessageSurfaceAdapter(),
        Surface.GENERIC: GenericSurfaceAdapter(),
    }


def get_surface_adapter(surface: Surface | str) -> SurfaceAdapter:
    """Get the adapter for a given surface.

    Args:
        surface: Surface enum value or string name.

    Returns:
        The corresponding SurfaceAdapter instance.

    Raises:
        KeyError: If no adapter is registered for the surface.
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()

    if isinstance(surface, str):
        try:
            surface = Surface(surface)
        except ValueError:
            available = ", ".join(s.value for s in Surface)
            msg = f"Unknown surface '{surface}'. Available: {available}"
            raise KeyError(msg) from None

    if surface not in _REGISTRY:
        available = ", ".join(s.value for s in _REGISTRY)
        msg = f"No adapter registered for surface '{surface.value}'. Available: {available}"
        raise KeyError(msg)

    return _REGISTRY[surface]


def list_surfaces() -> list[Surface]:
    """Return all registered surfaces."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return sorted(_REGISTRY.keys(), key=lambda s: s.value)


__all__ = [
    "EvaluationSubjectPayload",
    "SurfaceAdapter",
    "get_surface_adapter",
    "list_surfaces",
]
