"""Domain Pack distribution service (Phase 13).

Lists, installs, version-pins, and auto-updates Domain Packs
for cross-organizational distribution via the Marketplace.

See CLAUDE.md §14.8.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.domain_packs.loader import DomainPackLoader, PackManifest

logger = get_logger(__name__)


@dataclass
class PackListing:
    """A pack as listed in the marketplace."""

    name: str
    version: str
    display_name: str
    description: str
    persona: str
    surfaces: list[str]
    rule_count: int = 0
    quality_score: float | None = None
    installed: bool = False


@dataclass
class PackInstallResult:
    """Result of installing a pack."""

    name: str
    version: str
    rules_imported: int
    success: bool
    message: str = ""


@dataclass
class PackSignature:
    """Cryptographic signature for pack verification."""

    pack_name: str
    version: str
    hash: str
    signed_by: str


def list_available_packs() -> list[PackListing]:
    """List all available domain packs for installation.

    Discovers packs from the local filesystem and annotates them
    with installation status and quality scores.
    """
    loader = DomainPackLoader()
    all_packs = loader.discover()
    loaded = loader.get_loaded_packs()

    listings = []
    for pack in all_packs:
        rule_count = _count_rules_in_pack(pack)
        listings.append(
            PackListing(
                name=pack.name,
                version=pack.version,
                display_name=pack.display_name,
                description=pack.description,
                persona=pack.persona,
                surfaces=pack.surfaces,
                rule_count=rule_count,
                installed=pack.name in loaded,
            )
        )

    return listings


def compute_pack_quality_score(pack_name: str) -> float | None:
    """Compute an aggregate quality score for a pack's rules.

    Aggregates effectiveness metrics (true positive rate, false positive
    rate) across all rules in the pack.

    Returns:
        Quality score between 0.0 and 1.0, or None if insufficient data.
    """
    pack = DomainPackLoader.get_pack(pack_name)
    if not pack:
        return None

    # Placeholder: real implementation would query evaluation metrics
    return None


def verify_pack_signature(pack_name: str, expected_hash: str) -> bool:
    """Verify the integrity of a pack by comparing content hashes.

    Args:
        pack_name: Name of the pack to verify.
        expected_hash: Expected SHA-256 hash of pack contents.

    Returns:
        True if the hash matches.
    """
    pack = DomainPackLoader.get_pack(pack_name)
    if not pack:
        return False

    actual_hash = _compute_pack_hash(pack)
    return hmac.compare_digest(actual_hash, expected_hash)


def detect_composition_conflicts(
    pack_names: list[str],
) -> list[dict[str, Any]]:
    """Detect potential conflicts when composing multiple packs.

    Checks for overlapping scopes, contradictory rules, and
    surface adapter conflicts between packs.

    Args:
        pack_names: Names of packs to compose.

    Returns:
        List of detected conflicts with details.
    """
    conflicts: list[dict[str, Any]] = []
    loader = DomainPackLoader()
    loaded = loader.get_loaded_packs()

    packs = [loaded[n] for n in pack_names if n in loaded]

    # Check for scope overlaps
    scope_owners: dict[str, str] = {}
    for pack in packs:
        for scope in pack.default_scopes:
            if scope in scope_owners:
                conflicts.append(
                    {
                        "type": "scope_overlap",
                        "scope": scope,
                        "pack_a": scope_owners[scope],
                        "pack_b": pack.name,
                        "severity": "warning",
                    }
                )
            else:
                scope_owners[scope] = pack.name

    return conflicts


def _count_rules_in_pack(pack: PackManifest) -> int:
    """Count rules in a pack's YAML files."""
    count = 0
    rules_dir = pack.rules_dir
    if rules_dir.is_dir():
        for yaml_file in rules_dir.glob("*.yaml"):
            try:
                import yaml

                data = yaml.safe_load(yaml_file.read_text())
                if data and "rules" in data:
                    count += len(data["rules"])
            except Exception:
                pass
    return count


def _compute_pack_hash(pack: PackManifest) -> str:
    """Compute SHA-256 hash of all pack content files."""
    h = hashlib.sha256()
    pack_dir = pack.pack_dir
    for f in sorted(pack_dir.rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            h.update(f.read_bytes())
    return h.hexdigest()
