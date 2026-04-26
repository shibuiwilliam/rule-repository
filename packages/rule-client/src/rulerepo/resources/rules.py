"""Rules resource — CRUD operations on rules."""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import Relationship, Revision, Rule, RuleList


class RulesResource:
    """Provides CRUD operations on rules via the REST API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get(self, rule_id: str) -> Rule:
        """Fetch a single rule by ID.

        Args:
            rule_id: The rule's UUID string.

        Returns:
            The matching Rule.
        """
        resp = await self._client.get(f"/api/v1/rules/{rule_id}")
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return Rule.model_validate(resp.json())

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> RuleList:
        """List rules with optional filters and pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            **filters: Additional query parameters (modality, severity, status, etc.).

        Returns:
            Paginated RuleList.
        """
        params = {"page": page, "page_size": page_size, **filters}
        resp = await self._client.get("/api/v1/rules", params=params)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return RuleList.model_validate(resp.json())

    async def create(self, statement: str, **kwargs: Any) -> Rule:
        """Create a new rule.

        Args:
            statement: The rule text.
            **kwargs: Additional rule fields (modality, severity, scope, tags, etc.).

        Returns:
            The newly created Rule.
        """
        body = {"statement": statement, **kwargs}
        resp = await self._client.post("/api/v1/rules", json=body)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return Rule.model_validate(resp.json())

    async def update(self, rule_id: str, **kwargs: Any) -> Rule:
        """Update an existing rule.

        Args:
            rule_id: The rule's UUID string.
            **kwargs: Fields to update.

        Returns:
            The updated Rule.
        """
        resp = await self._client.patch(f"/api/v1/rules/{rule_id}", json=kwargs)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return Rule.model_validate(resp.json())

    async def retire(self, rule_id: str) -> Rule:
        """Retire a rule (soft-delete).

        Args:
            rule_id: The rule's UUID string.

        Returns:
            The retired Rule.
        """
        resp = await self._client.post(f"/api/v1/rules/{rule_id}/retire")
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return Rule.model_validate(resp.json())

    async def revisions(self, rule_id: str) -> list[Revision]:
        """Get the revision history for a rule.

        Args:
            rule_id: The rule's UUID string.

        Returns:
            List of Revision objects.
        """
        resp = await self._client.get(f"/api/v1/rules/{rule_id}/revisions")
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return [Revision.model_validate(r) for r in resp.json()]

    async def relationships(self, rule_id: str) -> list[Relationship]:
        """Get all relationships involving a rule.

        Args:
            rule_id: The rule's UUID string.

        Returns:
            List of Relationship objects.
        """
        resp = await self._client.get(f"/api/v1/rules/{rule_id}/relationships")
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return [Relationship.model_validate(r) for r in resp.json()]
