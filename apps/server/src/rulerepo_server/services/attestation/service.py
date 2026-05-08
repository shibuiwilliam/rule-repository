"""Attestation service -- manages campaign lifecycle and response tracking.

See IMPROVEMENT.md RR-014.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.attestation import (
    AttestationCampaign,
    AttestationResponse,
    CampaignProgress,
    CampaignStatus,
    ResponseStatus,
)

logger = get_logger(__name__)


class AttestationService:
    """Manages attestation campaigns and user responses.

    Uses in-memory storage. Will be replaced with Postgres persistence
    once the DB model is finalized.
    """

    def __init__(self) -> None:
        self._campaigns: dict[UUID, AttestationCampaign] = {}
        self._responses: dict[UUID, list[AttestationResponse]] = {}

    async def create_campaign(
        self,
        *,
        tenant_id: str = "default",
        title: str,
        description: str = "",
        rule_ids: list[str],
        target_users: list[str] | None = None,
        target_departments: list[str] | None = None,
        due_date: datetime | None = None,
        reminder_interval_days: int = 7,
        created_by: str = "system",
    ) -> AttestationCampaign:
        """Create a new attestation campaign.

        Args:
            tenant_id: Tenant identifier.
            title: Campaign title.
            description: Human-readable description.
            rule_ids: IDs of rules users must attest to.
            target_users: User IDs who must respond (or ``None`` for all).
            target_departments: Department names to target.
            due_date: Optional deadline for responses.
            reminder_interval_days: Days between reminder notifications.
            created_by: ID of the user creating the campaign.

        Returns:
            The newly created campaign.
        """
        campaign = AttestationCampaign(
            id=uuid4(),
            tenant_id=tenant_id,
            title=title,
            description=description,
            rule_ids=rule_ids,
            target_users=target_users or [],
            target_departments=target_departments or [],
            due_date=due_date,
            reminder_interval_days=reminder_interval_days,
            created_by=created_by,
        )
        self._campaigns[campaign.id] = campaign
        self._responses[campaign.id] = []

        # Seed pending responses for each target user.
        for user_id in campaign.target_users:
            response = AttestationResponse(
                id=uuid4(),
                campaign_id=campaign.id,
                user_id=user_id,
                status=ResponseStatus.PENDING,
            )
            self._responses[campaign.id].append(response)

        logger.info(
            "attestation_campaign_created",
            campaign_id=str(campaign.id),
            title=title,
            target_user_count=len(campaign.target_users),
        )
        return campaign

    async def get_campaign(self, campaign_id: UUID) -> AttestationCampaign:
        """Get a single campaign by ID.

        Args:
            campaign_id: The campaign UUID.

        Returns:
            The matching campaign.

        Raises:
            NotFoundError: If the campaign does not exist.
        """
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            raise NotFoundError("AttestationCampaign", str(campaign_id))
        return campaign

    async def list_campaigns(self, tenant_id: str = "default") -> list[AttestationCampaign]:
        """List all campaigns for a tenant.

        Args:
            tenant_id: Tenant identifier to filter by.

        Returns:
            List of campaigns ordered by creation time (newest first).
        """
        campaigns = [c for c in self._campaigns.values() if c.tenant_id == tenant_id]
        campaigns.sort(key=lambda c: c.created_at, reverse=True)
        return campaigns

    async def get_campaign_progress(self, campaign_id: UUID) -> CampaignProgress:
        """Compute aggregate completion stats for a campaign.

        Args:
            campaign_id: The campaign UUID.

        Returns:
            CampaignProgress with counts and completion rate.

        Raises:
            NotFoundError: If the campaign does not exist.
        """
        if campaign_id not in self._campaigns:
            raise NotFoundError("AttestationCampaign", str(campaign_id))

        responses = self._responses.get(campaign_id, [])
        total = len(responses)
        attested = sum(1 for r in responses if r.status == ResponseStatus.ATTESTED)
        declined = sum(1 for r in responses if r.status == ResponseStatus.DECLINED)
        expired = sum(1 for r in responses if r.status == ResponseStatus.EXPIRED)
        pending = sum(1 for r in responses if r.status == ResponseStatus.PENDING)
        completion_rate = (attested / total * 100.0) if total > 0 else 0.0

        return CampaignProgress(
            campaign_id=campaign_id,
            total_users=total,
            attested=attested,
            declined=declined,
            pending=pending,
            expired=expired,
            completion_rate=round(completion_rate, 2),
        )

    async def record_response(
        self,
        *,
        campaign_id: UUID,
        user_id: str,
        status: ResponseStatus,
        declined_reason: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> AttestationResponse:
        """Record a user's attestation response.

        If the user already has a pending response for this campaign, it is
        updated in place. Otherwise a new response is created.

        Args:
            campaign_id: The campaign UUID.
            user_id: Responding user's identifier.
            status: The response status (ATTESTED or DECLINED).
            declined_reason: Reason text when declining.
            ip_address: Client IP for audit trail.
            user_agent: Client user-agent for audit trail.

        Returns:
            The recorded or updated response.

        Raises:
            NotFoundError: If the campaign does not exist.
        """
        if campaign_id not in self._campaigns:
            raise NotFoundError("AttestationCampaign", str(campaign_id))

        responses = self._responses.setdefault(campaign_id, [])

        # Find existing pending response for this user.
        existing = next(
            (r for r in responses if r.user_id == user_id and r.status == ResponseStatus.PENDING),
            None,
        )

        now = datetime.now(tz=UTC)

        if existing is not None:
            existing.status = status
            existing.attested_at = now if status == ResponseStatus.ATTESTED else None
            existing.declined_reason = declined_reason
            existing.ip_address = ip_address
            existing.user_agent = user_agent
            response = existing
        else:
            response = AttestationResponse(
                id=uuid4(),
                campaign_id=campaign_id,
                user_id=user_id,
                status=status,
                attested_at=now if status == ResponseStatus.ATTESTED else None,
                declined_reason=declined_reason,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            responses.append(response)

        logger.info(
            "attestation_response_recorded",
            campaign_id=str(campaign_id),
            user_id=user_id,
            status=status.value,
        )
        return response

    async def get_user_pending(
        self,
        user_id: str,
        tenant_id: str = "default",
    ) -> list[dict[str, object]]:
        """List pending attestations for a user across all campaigns.

        Args:
            user_id: The user to look up.
            tenant_id: Tenant identifier to scope the lookup.

        Returns:
            List of dicts with campaign info and the pending response.
        """
        pending: list[dict[str, object]] = []
        for campaign in self._campaigns.values():
            if campaign.tenant_id != tenant_id:
                continue
            if campaign.status != CampaignStatus.ACTIVE:
                continue
            responses = self._responses.get(campaign.id, [])
            for r in responses:
                if r.user_id == user_id and r.status == ResponseStatus.PENDING:
                    pending.append(
                        {
                            "campaign_id": str(campaign.id),
                            "campaign_title": campaign.title,
                            "due_date": campaign.due_date.isoformat() if campaign.due_date else None,
                            "rule_ids": campaign.rule_ids,
                            "response_id": str(r.id),
                        }
                    )
        return pending

    async def close_campaign(self, campaign_id: UUID) -> AttestationCampaign:
        """Close a campaign and expire any remaining pending responses.

        Args:
            campaign_id: The campaign UUID.

        Returns:
            The updated campaign with CLOSED status.

        Raises:
            NotFoundError: If the campaign does not exist.
        """
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            raise NotFoundError("AttestationCampaign", str(campaign_id))

        campaign.status = CampaignStatus.CLOSED
        campaign.updated_at = datetime.now(tz=UTC)

        # Expire remaining pending responses.
        for r in self._responses.get(campaign_id, []):
            if r.status == ResponseStatus.PENDING:
                r.status = ResponseStatus.EXPIRED

        logger.info("attestation_campaign_closed", campaign_id=str(campaign_id))
        return campaign
