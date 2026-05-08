"""OFAC sanctions screening fact provider.

Resolves sanctions-related facts by checking entity names against the
OFAC SDN (Specially Designated Nationals) list.

This module ships with a mock implementation containing sample SDN
entries.  A production deployment would integrate with an actual OFAC
API or a locally-mirrored SDN list updated daily.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import Fact, FactSchema, FactStatus

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock SDN data for development
# ---------------------------------------------------------------------------

_MOCK_SDN_ENTRIES: list[dict[str, Any]] = [
    {
        "name": "EVIL CORP LTD",
        "aliases": ["EVIL CORPORATION", "EC LTD"],
        "program": "CYBER2",
        "type": "entity",
        "country": "RU",
    },
    {
        "name": "JOHN BADACTOR",
        "aliases": ["J. BADACTOR"],
        "program": "SDGT",
        "type": "individual",
        "country": "SY",
    },
    {
        "name": "SHADY BANK SA",
        "aliases": ["SHADYBANK"],
        "program": "IRAN",
        "type": "entity",
        "country": "IR",
    },
]

# ---------------------------------------------------------------------------
# Supported fact schemas
# ---------------------------------------------------------------------------

_SCHEMAS: list[FactSchema] = [
    FactSchema(
        key="ofac_match",
        description=("Whether the entity name matches an OFAC SDN entry.  Returns match details or null if no match."),
        value_type="dict",
        required_context_keys=["entity_name"],
        domain="compliance",
    ),
    FactSchema(
        key="sanctions_screening_status",
        description=("Overall sanctions screening status for an entity: clear, match_found, or review_required."),
        value_type="str",
        required_context_keys=["entity_name"],
        domain="compliance",
    ),
]


class OFACSanctionsProvider:
    """Resolves sanctions screening facts against the OFAC SDN list.

    Attributes:
        name: Provider name.
        domain: Business domain.
    """

    name: str = "ofac_sanctions"
    domain: str = "compliance"

    def __init__(
        self,
        sdn_entries: list[dict[str, Any]] | None = None,
    ) -> None:
        self._entries = sdn_entries if sdn_entries is not None else _MOCK_SDN_ENTRIES

    async def supported_facts(self) -> list[FactSchema]:
        """Return sanctions-related fact schemas."""
        return list(_SCHEMAS)

    async def fetch(self, key: str, context: dict[str, Any]) -> Fact | None:
        """Screen an entity against the SDN list.

        Args:
            key: ``ofac_match`` or ``sanctions_screening_status``.
            context: Must contain ``entity_name``.

        Returns:
            Resolved ``Fact`` or ``None`` if context is incomplete.
        """
        entity_name = context.get("entity_name")
        if not entity_name:
            logger.warning("ofac_missing_entity_name", key=key)
            return None

        match = self._find_match(entity_name)

        if key == "ofac_match":
            return Fact(
                key=key,
                value=match,
                status=FactStatus.RESOLVED,
                source_provider=self.name,
                resolved_at=datetime.now(tz=UTC),
                ttl_seconds=86400,  # 24 hour cache
                metadata={"entity_name": entity_name},
            )

        if key == "sanctions_screening_status":
            status = "clear" if match is None else "match_found"
            return Fact(
                key=key,
                value=status,
                status=FactStatus.RESOLVED,
                source_provider=self.name,
                resolved_at=datetime.now(tz=UTC),
                ttl_seconds=86400,
                metadata={"entity_name": entity_name},
            )

        return None

    def _find_match(self, entity_name: str) -> dict[str, Any] | None:
        """Check entity name against SDN entries (case-insensitive).

        Args:
            entity_name: The name to screen.

        Returns:
            Match details dict or ``None``.
        """
        normalized = entity_name.upper().strip()
        for entry in self._entries:
            names = [entry["name"]] + entry.get("aliases", [])
            for name in names:
                if name.upper() == normalized:
                    return {
                        "matched_name": entry["name"],
                        "matched_alias": name if name != entry["name"] else None,
                        "program": entry["program"],
                        "type": entry["type"],
                        "country": entry["country"],
                    }
        return None

    async def health_check(self) -> bool:
        """OFAC provider is always healthy in mock mode."""
        return True
