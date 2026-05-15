"""Domain Pack loader — discovers, validates, and registers packs at startup.

Scans ``domain_packs/`` for ``pack.yaml`` files, validates their schema,
and registers them in the pack registry. ``ENABLED_PACKS`` env var controls
which packs are loaded.

See CLAUDE.md §14.9.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Internal packs (inside the server package)
_INTERNAL_PACKS_DIR = Path(__file__).parent.parent.parent / "domain_packs"
# External packs (packages/domain-packs/ at repo root)
_EXTERNAL_PACKS_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "packages" / "domain-packs"

# Keep the old name for backward compatibility (points to internal dir)
DOMAIN_PACKS_DIR = _INTERNAL_PACKS_DIR


@dataclass
class PackManifest:
    """Parsed representation of a pack.yaml.

    Each domain pack is a self-contained unit containing:
    - ``pack.yaml``: this manifest (metadata, surfaces, scopes, persona)
    - ``rules/``: seed rule YAML files
    - ``prompts/``: LLM prompt templates for extraction and evaluation
    - ``analyzers/``: domain-specific document analyzers for discovery
    - ``samples/``: example business data for testing
    """

    name: str
    version: str
    display_name: str
    description: str
    surfaces: list[str] = field(default_factory=list)
    required_adapters: list[str] = field(default_factory=list)
    default_scopes: list[str] = field(default_factory=list)
    ui_routes: list[str] = field(default_factory=list)
    seed_rules_path: str = "rules/"
    prompts_path: str = "prompts/"
    analyzers_path: str = "analyzers/"
    samples_path: str = "samples/"
    metadata_schema: dict[str, Any] = field(default_factory=dict)
    persona: str = "admin"
    pack_dir: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def from_dict(cls, data: dict[str, Any], pack_dir: Path) -> PackManifest:
        """Create a PackManifest from a parsed YAML dict."""
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            display_name=data.get("display_name", data.get("name", "")),
            description=data.get("description", ""),
            surfaces=data.get("surfaces", []),
            required_adapters=data.get("required_adapters", []),
            default_scopes=data.get("default_scopes", []),
            ui_routes=data.get("ui_routes", []),
            seed_rules_path=data.get("seed_rules_path", "rules/"),
            prompts_path=data.get("prompts_path", "prompts/"),
            analyzers_path=data.get("analyzers_path", "analyzers/"),
            samples_path=data.get("samples_path", "samples/"),
            metadata_schema=data.get("metadata_schema", {}),
            persona=data.get("persona", "admin"),
            pack_dir=pack_dir,
        )

    @property
    def rules_dir(self) -> Path:
        """Absolute path to the pack's rules directory."""
        return self.pack_dir / self.seed_rules_path

    @property
    def prompts_dir(self) -> Path:
        """Absolute path to the pack's prompts directory."""
        return self.pack_dir / self.prompts_path

    @property
    def analyzers_dir(self) -> Path:
        """Absolute path to the pack's analyzers directory."""
        return self.pack_dir / self.analyzers_path

    @property
    def samples_dir(self) -> Path:
        """Absolute path to the pack's samples directory."""
        return self.pack_dir / self.samples_path

    @property
    def has_prompts(self) -> bool:
        """Whether the pack has prompt templates."""
        return self.prompts_dir.is_dir() and any(self.prompts_dir.iterdir())

    @property
    def has_analyzers(self) -> bool:
        """Whether the pack has domain-specific analyzers."""
        d = self.analyzers_dir
        return d.is_dir() and any(f for f in d.iterdir() if f.suffix == ".py" and f.name != "__init__.py")

    @property
    def has_samples(self) -> bool:
        """Whether the pack has sample data files."""
        return self.samples_dir.is_dir() and any(self.samples_dir.iterdir())


# Global registry
_LOADED_PACKS: dict[str, PackManifest] = {}


class DomainPackLoader:
    """Loads and validates domain packs from the filesystem."""

    def __init__(
        self,
        packs_dir: Path | None = None,
        *,
        extra_packs_dirs: list[Path] | None = None,
    ) -> None:
        self._packs_dir = packs_dir or DOMAIN_PACKS_DIR
        # By default, also scan the external packs directory at the repo root.
        if extra_packs_dirs is not None:
            self._extra_dirs = list(extra_packs_dirs)
        else:
            self._extra_dirs = [_EXTERNAL_PACKS_DIR]

    # Directories to skip when scanning external packs (shared utilities, not packs)
    _SKIP_DIRS: frozenset[str] = frozenset({"_core", "__pycache__"})

    def _scan_directory(
        self,
        base_dir: Path,
        *,
        skip_dirs: frozenset[str] | None = None,
    ) -> list[PackManifest]:
        """Scan a single directory for pack.yaml files and return manifests."""
        packs: list[PackManifest] = []
        if not base_dir.is_dir():
            logger.warning("domain_packs_dir_not_found", path=str(base_dir))
            return packs

        for pack_dir in sorted(base_dir.iterdir()):
            if not pack_dir.is_dir():
                continue
            if skip_dirs and pack_dir.name in skip_dirs:
                continue
            pack_yaml = pack_dir / "pack.yaml"
            if not pack_yaml.exists():
                continue

            try:
                import yaml

                data = yaml.safe_load(pack_yaml.read_text())
                manifest = PackManifest.from_dict(data, pack_dir)
                packs.append(manifest)
                logger.info(
                    "pack_discovered",
                    name=manifest.name,
                    version=manifest.version,
                    persona=manifest.persona,
                    source=str(base_dir),
                )
            except Exception as exc:
                logger.warning(
                    "pack_load_failed",
                    path=str(pack_yaml),
                    error=str(exc),
                )

        return packs

    def discover(self) -> list[PackManifest]:
        """Discover all packs with pack.yaml files.

        Scans the primary packs directory (internal) and any extra directories
        (by default, ``packages/domain-packs/`` at the repo root). Packs from
        the extra directories skip utility directories like ``_core/``.

        When the same pack name appears in multiple directories the last
        occurrence wins, so external packs can override internal ones.
        """
        seen: dict[str, PackManifest] = {}

        # Scan internal packs first
        for manifest in self._scan_directory(self._packs_dir):
            seen[manifest.name] = manifest

        # Scan extra directories (external packs); skip _core/ etc.
        for extra_dir in self._extra_dirs:
            for manifest in self._scan_directory(extra_dir, skip_dirs=self._SKIP_DIRS):
                if manifest.name in seen:
                    logger.info(
                        "pack_overridden_by_external",
                        name=manifest.name,
                        source=str(extra_dir),
                    )
                seen[manifest.name] = manifest

        return list(seen.values())

    def load_enabled(self) -> list[PackManifest]:
        """Load only the packs listed in ENABLED_PACKS env var.

        If ENABLED_PACKS is not set, loads all discovered packs.
        """
        global _LOADED_PACKS

        enabled_str = os.environ.get("ENABLED_PACKS", "")
        enabled_names = {n.strip() for n in enabled_str.split(",") if n.strip()} if enabled_str else None

        all_packs = self.discover()
        loaded = []

        for pack in all_packs:
            if enabled_names is not None and pack.name not in enabled_names:
                logger.info("pack_skipped_not_enabled", name=pack.name)
                continue

            _LOADED_PACKS[pack.name] = pack
            loaded.append(pack)
            logger.info(
                "pack_loaded",
                name=pack.name,
                version=pack.version,
                surfaces=pack.surfaces,
                persona=pack.persona,
            )

        return loaded

    @staticmethod
    def get_loaded_packs() -> dict[str, PackManifest]:
        """Return the registry of currently loaded packs."""
        return dict(_LOADED_PACKS)

    @staticmethod
    def get_pack(name: str) -> PackManifest | None:
        """Get a loaded pack by name."""
        return _LOADED_PACKS.get(name)

    @staticmethod
    def get_packs_for_surface(surface: str) -> list[PackManifest]:
        """Return all loaded packs that handle a given surface type.

        Args:
            surface: The surface type (e.g. ``code``, ``contract``, ``transaction``).

        Returns:
            List of packs whose ``surfaces`` list contains the given surface.
        """
        return [p for p in _LOADED_PACKS.values() if surface in p.surfaces]

    @staticmethod
    def get_packs_for_persona(persona: str) -> list[PackManifest]:
        """Return all loaded packs targeting a given persona.

        Args:
            persona: The persona name (e.g. ``legal``, ``hr``, ``finance``).

        Returns:
            List of packs whose ``persona`` matches.
        """
        return [p for p in _LOADED_PACKS.values() if p.persona == persona]

    @staticmethod
    def get_prompt_files(pack_name: str) -> list[Path]:
        """Return all prompt template files for a loaded pack.

        Args:
            pack_name: The pack's registered name.

        Returns:
            List of absolute paths to prompt files, or empty list if pack
            not found or has no prompts.
        """
        pack = _LOADED_PACKS.get(pack_name)
        if pack is None or not pack.has_prompts:
            return []
        return sorted(pack.prompts_dir.glob("*.txt"))
