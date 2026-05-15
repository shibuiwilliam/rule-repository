"""Domain Pack manifest schema.

Defines the structure of pack.yaml files per PROJECT.md §6.7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PackManifest:
    """Parsed representation of a pack.yaml manifest.

    See CLAUDE.md §14.4 for the full specification.
    """

    domain: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    subject_types: list[str] = field(default_factory=list)
    metadata_extensions: dict[str, Any] = field(default_factory=dict)
    default_modality: str = "MUST"
    preferred_evaluator_subject_kinds: list[str] = field(default_factory=list)
    pack_dir: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def from_yaml(cls, path: Path) -> PackManifest:
        """Load a manifest from a pack.yaml file.

        Args:
            path: Path to the pack.yaml file.

        Returns:
            A populated PackManifest instance.

        Raises:
            FileNotFoundError: If the path does not exist.
            KeyError: If required fields (domain, name) are missing.
            yaml.YAMLError: If the file is not valid YAML.
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(
            domain=data["domain"],
            name=data["name"],
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            subject_types=data.get("subject_types", []),
            metadata_extensions=data.get("metadata_extensions", {}),
            default_modality=data.get("default_modality", "MUST"),
            preferred_evaluator_subject_kinds=data.get("preferred_evaluator_subject_kinds", []),
            pack_dir=path.parent,
        )
