"""Regional data routing for data-residency and sovereignty compliance.

Ensures that LLM calls, data storage, and processing respect the
geographic constraints configured per tenant.  This is critical for
GDPR (EU data must stay in EU), APPI (Japan), and similar regulations.

Tenant settings are read from configuration; in production these come
from the tenant management database.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rulerepo_server.core.errors import RuleRepoError, ValidationError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class DataResidencyViolationError(RuleRepoError):
    """Raised when an operation would violate data-residency constraints."""

    def __init__(self, tenant_id: str, target_region: str) -> None:
        super().__init__(
            message=(
                f"Data residency violation: tenant '{tenant_id}' is not "
                f"permitted to process data in region '{target_region}'"
            ),
            code="DATA_RESIDENCY_VIOLATION",
            status_code=403,
        )


# ---------------------------------------------------------------------------
# Well-known Vertex AI regional endpoints
# ---------------------------------------------------------------------------

_VERTEX_AI_ENDPOINTS: dict[str, str] = {
    "us-central1": "https://us-central1-aiplatform.googleapis.com",
    "us-east1": "https://us-east1-aiplatform.googleapis.com",
    "us-east4": "https://us-east4-aiplatform.googleapis.com",
    "us-west1": "https://us-west1-aiplatform.googleapis.com",
    "europe-west1": "https://europe-west1-aiplatform.googleapis.com",
    "europe-west4": "https://europe-west4-aiplatform.googleapis.com",
    "asia-northeast1": "https://asia-northeast1-aiplatform.googleapis.com",
    "asia-southeast1": "https://asia-southeast1-aiplatform.googleapis.com",
    "asia-east1": "https://asia-east1-aiplatform.googleapis.com",
}


@dataclass(frozen=True, slots=True)
class TenantRegionConfig:
    """Region configuration for a single tenant.

    Attributes:
        tenant_id: Tenant identifier.
        llm_region: Region where LLM calls must be routed.
        storage_region: Region where data must be stored.
        allowed_regions: Set of regions the tenant is allowed to use.
            An empty set means all regions are allowed.
    """

    tenant_id: str
    llm_region: str = "us-central1"
    storage_region: str = "us-central1"
    allowed_regions: frozenset[str] = field(default_factory=frozenset)


# Default region configuration used when a tenant has no explicit config.
_DEFAULT_CONFIG = TenantRegionConfig(
    tenant_id="__default__",
    llm_region="us-central1",
    storage_region="us-central1",
)


class RegionalRouter:
    """Routes data and LLM requests to the correct geographic region.

    In development, tenant configurations are stored in memory.  In
    production, they are loaded from the tenant management database
    and cached with a short TTL.
    """

    def __init__(self) -> None:
        self._configs: dict[str, TenantRegionConfig] = {}

    # ------------------------------------------------------------------
    # Configuration management
    # ------------------------------------------------------------------

    def configure_tenant(self, config: TenantRegionConfig) -> None:
        """Set or update the region configuration for a tenant.

        Args:
            config: The tenant's region configuration.
        """
        self._configs[config.tenant_id] = config
        logger.info(
            "regional_routing_configured",
            tenant_id=config.tenant_id,
            llm_region=config.llm_region,
            storage_region=config.storage_region,
        )

    def _get_config(self, tenant_id: str) -> TenantRegionConfig:
        """Retrieve the region config for a tenant, falling back to default."""
        return self._configs.get(tenant_id, _DEFAULT_CONFIG)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_llm_region(self, tenant_id: str) -> str:
        """Return the configured LLM processing region for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            GCP region string (e.g. ``"asia-northeast1"``).
        """
        return self._get_config(tenant_id).llm_region

    def get_storage_region(self, tenant_id: str) -> str:
        """Return the configured data storage region for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            GCP region string.
        """
        return self._get_config(tenant_id).storage_region

    def validate_data_residency(self, tenant_id: str, target_region: str) -> bool:
        """Check whether a tenant is permitted to use a target region.

        If the tenant has an explicit ``allowed_regions`` set, the target
        must be in that set.  If the set is empty (no restrictions beyond
        the configured defaults), any region is accepted.

        Args:
            tenant_id: Tenant identifier.
            target_region: The region to validate.

        Returns:
            True if the region is permitted.
        """
        config = self._get_config(tenant_id)
        if not config.allowed_regions:
            return True
        return target_region in config.allowed_regions

    def get_vertex_ai_endpoint(self, region: str) -> str:
        """Return the Vertex AI endpoint URL for a region.

        Args:
            region: GCP region string.

        Returns:
            The HTTPS endpoint URL for Vertex AI in the given region.

        Raises:
            ValidationError: If the region is not recognized.
        """
        endpoint = _VERTEX_AI_ENDPOINTS.get(region)
        if endpoint is None:
            raise ValidationError(
                f"Unknown Vertex AI region: '{region}'. Known regions: {sorted(_VERTEX_AI_ENDPOINTS)}"
            )
        return endpoint
