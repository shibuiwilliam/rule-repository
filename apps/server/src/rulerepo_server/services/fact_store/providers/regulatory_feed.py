"""Regulatory feed fact provider.

Resolves facts about the status of regulations: whether they are
active, their effective date, and whether an amendment is pending.

Ships with mock data covering Japanese labor law references.
A production deployment would integrate with e-Gov API or FSA feeds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import Fact, FactSchema, FactStatus

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock regulation data — Japanese labor law
# ---------------------------------------------------------------------------

_MOCK_REGULATIONS: dict[str, dict[str, Any]] = {
    "労働基準法": {
        "status": "active",
        "effective_date": "1947-04-07",
        "amendment_pending": False,
        "latest_amendment": "2024-04-01",
        "full_name": "労働基準法(昭和二十二年法律第四十九号)",
    },
    "労働安全衛生法": {
        "status": "active",
        "effective_date": "1972-06-08",
        "amendment_pending": True,
        "latest_amendment": "2023-04-01",
        "pending_amendment_summary": "ストレスチェック制度の拡充",
        "full_name": "労働安全衛生法(昭和四十七年法律第五十七号)",
    },
    "個人情報保護法": {
        "status": "active",
        "effective_date": "2003-05-30",
        "amendment_pending": False,
        "latest_amendment": "2022-04-01",
        "full_name": "個人情報の保護に関する法律",
    },
    "下請法": {
        "status": "active",
        "effective_date": "1956-06-01",
        "amendment_pending": False,
        "latest_amendment": "2024-11-01",
        "full_name": "下請代金支払遅延等防止法",
    },
    "景品表示法": {
        "status": "active",
        "effective_date": "1962-05-15",
        "amendment_pending": True,
        "latest_amendment": "2023-10-01",
        "pending_amendment_summary": "ステルスマーケティング規制の強化",
        "full_name": "不当景品類及び不当表示防止法",
    },
}

# ---------------------------------------------------------------------------
# Supported fact schemas
# ---------------------------------------------------------------------------

_SCHEMAS: list[FactSchema] = [
    FactSchema(
        key="regulation_status",
        description="Current status of a regulation: active, repealed, or superseded.",
        value_type="str",
        required_context_keys=["regulation_id"],
        domain="legal",
    ),
    FactSchema(
        key="regulation_effective_date",
        description="Date when the regulation came into force (ISO 8601).",
        value_type="str",
        required_context_keys=["regulation_id"],
        domain="legal",
    ),
    FactSchema(
        key="regulation_amendment_pending",
        description=(
            "Whether an amendment to the regulation is pending.  "
            "Returns a dict with ``pending`` (bool) and optional "
            "``summary`` of the amendment."
        ),
        value_type="dict",
        required_context_keys=["regulation_id"],
        domain="legal",
    ),
]


class RegulatoryFeedProvider:
    """Resolves regulatory status facts.

    Attributes:
        name: Provider name.
        domain: Business domain.
    """

    name: str = "regulatory_feed"
    domain: str = "legal"

    def __init__(
        self,
        regulations: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._data = regulations if regulations is not None else _MOCK_REGULATIONS

    async def supported_facts(self) -> list[FactSchema]:
        """Return regulatory fact schemas."""
        return list(_SCHEMAS)

    async def fetch(self, key: str, context: dict[str, Any]) -> Fact | None:
        """Resolve a regulatory fact.

        Args:
            key: Fact key (e.g., ``regulation_status``).
            context: Must contain ``regulation_id`` matching a
                regulation name or ID.

        Returns:
            Resolved ``Fact`` or ``None``.
        """
        regulation_id = context.get("regulation_id")
        if not regulation_id:
            logger.warning("regulatory_feed_missing_regulation_id", key=key)
            return None

        reg = self._data.get(regulation_id)
        if reg is None:
            return None

        value: Any = None
        if key == "regulation_status":
            value = reg["status"]
        elif key == "regulation_effective_date":
            value = reg["effective_date"]
        elif key == "regulation_amendment_pending":
            value = {
                "pending": reg.get("amendment_pending", False),
                "summary": reg.get("pending_amendment_summary"),
                "latest_amendment": reg.get("latest_amendment"),
            }
        else:
            return None

        return Fact(
            key=key,
            value=value,
            status=FactStatus.RESOLVED,
            source_provider=self.name,
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=43200,  # 12 hour cache for regulation data
            metadata={"regulation_id": regulation_id},
        )

    async def health_check(self) -> bool:
        """Regulatory feed provider is always healthy in mock mode."""
        return True
