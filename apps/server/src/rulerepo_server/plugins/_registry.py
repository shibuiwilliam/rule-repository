"""Concrete plugin loader and singleton registry.

Discovers and loads all plugin modules under ``plugins/*/plugin.py``.
Called from server startup to populate the global PluginRegistry.

Usage::

    from rulerepo_server.plugins._registry import get_plugin_registry, load_plugins

    # At server startup:
    load_plugins()

    # Later, from any service:
    registry = get_plugin_registry()
    evaluators = registry.evaluators.get_for_subject_kind("code_diff")
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

import rulerepo_server.plugins as plugins_pkg
from rulerepo_server.plugins.base import DomainPlugin, PluginRegistry

logger = logging.getLogger(__name__)

_registry: PluginRegistry | None = None


def _discover_plugin_modules() -> list[str]:
    """Discover plugin modules by scanning ``plugins/*/plugin.py``.

    Walks the plugins package directory looking for sub-packages that
    contain a ``plugin.py`` module. Each such module is expected to
    expose a ``create_plugin()`` factory function that returns a
    ``DomainPlugin`` instance.

    Returns:
        List of fully qualified module names (e.g.
        ``rulerepo_server.plugins.engineering.plugin``).
    """
    plugins_dir = Path(plugins_pkg.__file__).parent
    discovered: list[str] = []

    for item in sorted(plugins_dir.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith("_"):
            continue
        plugin_module = item / "plugin.py"
        if plugin_module.exists():
            module_name = f"rulerepo_server.plugins.{item.name}.plugin"
            discovered.append(module_name)

    return discovered


def _load_plugin_from_module(module_name: str) -> DomainPlugin | None:
    """Import a plugin module and call its ``create_plugin()`` factory.

    Args:
        module_name: Fully qualified module name.

    Returns:
        A DomainPlugin instance, or None if loading fails.
    """
    try:
        module = importlib.import_module(module_name)
    except Exception:
        logger.exception("Failed to import plugin module: %s", module_name)
        return None

    factory = getattr(module, "create_plugin", None)
    if factory is None:
        logger.warning(
            "Plugin module %s does not expose create_plugin(); skipping",
            module_name,
        )
        return None

    try:
        plugin = factory()
    except Exception:
        logger.exception("Failed to create plugin from %s", module_name)
        return None

    if not isinstance(plugin, DomainPlugin):
        logger.warning(
            "create_plugin() in %s returned %s which does not satisfy DomainPlugin protocol; skipping",
            module_name,
            type(plugin).__name__,
        )
        return None

    return plugin


def load_plugins(*, registry: PluginRegistry | None = None) -> PluginRegistry:
    """Discover and load all domain plugins.

    Scans ``plugins/*/plugin.py`` for modules that expose a
    ``create_plugin()`` factory, instantiates each plugin, and
    registers it with the plugin registry.

    Args:
        registry: Optional pre-existing registry to populate. If None,
            creates a new one and sets it as the singleton.

    Returns:
        The populated PluginRegistry.
    """
    global _registry

    if registry is None:
        registry = PluginRegistry()

    module_names = _discover_plugin_modules()
    logger.info(
        "Discovered %d plugin module(s): %s",
        len(module_names),
        [m.rsplit(".", 2)[-2] for m in module_names],
    )

    for module_name in module_names:
        plugin = _load_plugin_from_module(module_name)
        if plugin is not None:
            try:
                registry.register_plugin(plugin)
            except Exception:
                logger.exception("Failed to register plugin from %s", module_name)

    _registry = registry
    logger.info(
        "Plugin loading complete: %d plugin(s) active across domains %s",
        len(registry.list_domains()),
        registry.list_domains(),
    )

    return registry


def get_plugin_registry() -> PluginRegistry:
    """Return the singleton PluginRegistry.

    If plugins have not been loaded yet, loads them first.

    Returns:
        The global PluginRegistry.
    """
    global _registry
    if _registry is None:
        _registry = load_plugins()
    return _registry


def reset_registry() -> None:
    """Reset the singleton registry. Used in tests."""
    global _registry
    _registry = None
