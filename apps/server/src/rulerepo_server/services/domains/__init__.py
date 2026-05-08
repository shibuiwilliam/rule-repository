"""Domain module registry — auto-discovers and registers domain plugins.

Each subdirectory under ``services/domains/`` that contains an ``__init__.py``
exporting a ``module`` attribute (satisfying the :class:`DomainModule` protocol)
is automatically registered on first access.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.domains._protocol import DomainModule

logger = get_logger(__name__)

_registry: dict[str, DomainModule] = {}
_discovered: bool = False


def _discover_modules() -> None:
    """Scan the domains package for DomainModule implementations."""
    global _discovered
    if _discovered:
        return
    _discovered = True

    package_path = Path(__file__).parent
    for info in pkgutil.iter_modules([str(package_path)]):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(
                f"rulerepo_server.services.domains.{info.name}",
            )
            domain_module: Any = getattr(mod, "module", None)
            if domain_module is not None and isinstance(domain_module, DomainModule):
                _registry[domain_module.name] = domain_module
                logger.info(
                    "domain_module_registered",
                    name=domain_module.name,
                    artifact_types=domain_module.supported_artifact_types,
                )
            else:
                logger.debug(
                    "domain_module_skipped",
                    name=info.name,
                    reason="no valid 'module' attribute",
                )
        except Exception as exc:
            logger.warning(
                "domain_module_load_failed",
                name=info.name,
                error=str(exc),
            )


def get_domain_module(name: str) -> DomainModule | None:
    """Return a registered domain module by name, or ``None``."""
    _discover_modules()
    return _registry.get(name)


def get_module_for_artifact_type(artifact_type: str) -> DomainModule | None:
    """Return the first domain module that handles *artifact_type*."""
    _discover_modules()
    for mod in _registry.values():
        if artifact_type in mod.supported_artifact_types:
            return mod
    return None


def get_all_modules() -> dict[str, DomainModule]:
    """Return a copy of the full module registry."""
    _discover_modules()
    return dict(_registry)
