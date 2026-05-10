"""Context Provider abstraction — fetch missing facts for evaluation.

When ``context_facts`` in a subject is incomplete, configured providers
can supply the missing data. See PROJECT.md §6.20 and CLAUDE.md §14.14.

Local-first principle: providers are file-based or in-cluster HTTP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.subject import EvaluationSubject

logger = get_logger(__name__)


@runtime_checkable
class ContextProvider(Protocol):
    """Protocol for context fact providers."""

    async def fetch(self, subject: EvaluationSubject) -> dict[str, Any]:
        """Fetch additional context facts for the subject.

        Args:
            subject: The evaluation subject needing additional facts.

        Returns:
            Dict of additional facts to merge into context.
        """
        ...


class StaticFileProvider:
    """Loads facts from local JSON or CSV files.

    Suitable for employee directories, approval matrices, budget tables,
    and other reference data that changes infrequently.

    Args:
        file_path: Path to the JSON file.
        key_field: Field in the subject payload to use as lookup key.
    """

    def __init__(self, file_path: Path, key_field: str) -> None:
        self._file_path = file_path
        self._key_field = key_field
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        """Load and cache the file contents."""
        if self._data is None:
            if not self._file_path.exists():
                logger.warning("static_file_not_found", path=str(self._file_path))
                self._data = {}
            else:
                with open(self._file_path) as f:
                    raw = json.load(f)
                # Index by key_field if the data is a list
                if isinstance(raw, list):
                    self._data = {str(item.get(self._key_field, "")): item for item in raw if self._key_field in item}
                else:
                    self._data = raw
        return self._data

    async def fetch(self, subject: EvaluationSubject) -> dict[str, Any]:
        """Look up facts by key_field value from the subject payload."""
        data = self._load()
        key_value = subject.payload.get(self._key_field) or subject.context.get(self._key_field)

        if key_value is None:
            return {}

        result = data.get(str(key_value), {})
        if result:
            logger.info(
                "static_provider_hit",
                key_field=self._key_field,
                key_value=key_value,
            )
        return result


class HttpProvider:
    """Calls a /facts endpoint hosted by the integrating business system.

    Local-first: the URL should be an in-cluster HTTP endpoint,
    not an external SaaS service.

    Args:
        base_url: Base URL of the facts endpoint.
        auth_token: Optional bearer token for authentication.
    """

    def __init__(self, base_url: str, auth_token: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_token = auth_token

    async def fetch(self, subject: EvaluationSubject) -> dict[str, Any]:
        """Fetch facts from the HTTP endpoint."""
        try:
            import httpx

            headers: dict[str, str] = {}
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._base_url}/facts",
                    json={
                        "subject_kind": subject.kind.value,
                        "payload": subject.payload,
                        "context": subject.context,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("http_provider_response", url=self._base_url, keys=list(result.keys()))
                return result
        except Exception as exc:
            logger.warning("http_provider_failed", url=self._base_url, error=str(exc))
            return {}


class ContextProviderRegistry:
    """Registry of configured context providers."""

    def __init__(self) -> None:
        self._providers: list[ContextProvider] = []

    def register(self, provider: ContextProvider) -> None:
        """Register a context provider."""
        self._providers.append(provider)

    async def enrich(self, subject: EvaluationSubject) -> dict[str, Any]:
        """Fetch and merge facts from all registered providers.

        Args:
            subject: The subject to enrich with additional context.

        Returns:
            Merged dict of all provider results.
        """
        merged: dict[str, Any] = {}
        for provider in self._providers:
            try:
                facts = await provider.fetch(subject)
                merged.update(facts)
            except Exception as exc:
                logger.warning("context_provider_error", error=str(exc))
        return merged
