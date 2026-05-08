"""Internal master data fact provider.

Generic key-value lookup against tenant master data.  Resolves facts
like product category, vendor status, cost center budget, and project
classification.

In development mode the provider returns data from a configurable dict.
In production this would query the tenant's master data table.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import Fact, FactSchema, FactStatus

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock master data for development
# ---------------------------------------------------------------------------

_MOCK_MASTER_DATA: dict[str, dict[str, Any]] = {
    # product_category: keyed by product_id
    "product_category": {
        "PROD-001": "software_license",
        "PROD-002": "consulting_service",
        "PROD-003": "hardware",
    },
    # vendor_status: keyed by vendor_id
    "vendor_status": {
        "VEND-001": "approved",
        "VEND-002": "pending_review",
        "VEND-003": "blocked",
    },
    # cost_center_budget: keyed by cost_center_id
    "cost_center_budget": {
        "CC-100": {"annual_budget_jpy": 50_000_000, "remaining_jpy": 12_000_000},
        "CC-200": {"annual_budget_jpy": 30_000_000, "remaining_jpy": 25_000_000},
    },
    # project_classification: keyed by project_id
    "project_classification": {
        "PRJ-A": "internal",
        "PRJ-B": "confidential",
        "PRJ-C": "public",
    },
}

# ---------------------------------------------------------------------------
# Context key mapping per fact key
# ---------------------------------------------------------------------------

_CONTEXT_KEY_MAP: dict[str, str] = {
    "product_category": "product_id",
    "vendor_status": "vendor_id",
    "cost_center_budget": "cost_center_id",
    "project_classification": "project_id",
}

# ---------------------------------------------------------------------------
# Supported fact schemas
# ---------------------------------------------------------------------------

_SCHEMAS: list[FactSchema] = [
    FactSchema(
        key="product_category",
        description="Category classification of a product (e.g., software_license, hardware).",
        value_type="str",
        required_context_keys=["product_id"],
        domain="operations",
    ),
    FactSchema(
        key="vendor_status",
        description="Approval status of a vendor: approved, pending_review, or blocked.",
        value_type="str",
        required_context_keys=["vendor_id"],
        domain="procurement",
    ),
    FactSchema(
        key="cost_center_budget",
        description="Budget information for a cost center including annual and remaining amounts.",
        value_type="dict",
        required_context_keys=["cost_center_id"],
        domain="finance",
    ),
    FactSchema(
        key="project_classification",
        description="Data classification level of a project: public, internal, or confidential.",
        value_type="str",
        required_context_keys=["project_id"],
        domain="operations",
    ),
]


class InternalMasterDataProvider:
    """Resolves facts from tenant internal master data.

    Attributes:
        name: Provider name.
        domain: Business domain.
    """

    name: str = "internal_master_data"
    domain: str = "operations"

    def __init__(
        self,
        master_data: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._data = master_data if master_data is not None else _MOCK_MASTER_DATA

    async def supported_facts(self) -> list[FactSchema]:
        """Return master-data fact schemas."""
        return list(_SCHEMAS)

    async def fetch(self, key: str, context: dict[str, Any]) -> Fact | None:
        """Look up a master data value.

        Args:
            key: Fact key (e.g., ``vendor_status``).
            context: Must contain the appropriate lookup key
                (e.g., ``vendor_id``).

        Returns:
            Resolved ``Fact`` or ``None``.
        """
        context_key = _CONTEXT_KEY_MAP.get(key)
        if context_key is None:
            logger.warning("master_data_unknown_key", key=key)
            return None

        lookup_id = context.get(context_key)
        if not lookup_id:
            logger.warning(
                "master_data_missing_context",
                key=key,
                required=context_key,
            )
            return None

        key_data = self._data.get(key)
        if key_data is None:
            return None

        value = key_data.get(lookup_id)
        if value is None:
            return None

        return Fact(
            key=key,
            value=value,
            status=FactStatus.RESOLVED,
            source_provider=self.name,
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=1800,  # 30 min cache for master data
            metadata={context_key: lookup_id},
        )

    async def health_check(self) -> bool:
        """Master data provider is always healthy in dev mode."""
        return True
