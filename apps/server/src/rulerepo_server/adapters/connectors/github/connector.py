"""GitHub connector implementation.

Normalizes GitHub webhook events (pull_request, push) into Code surface
subjects for evaluation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class GitHubConnector(SubjectConnector):
    """Connector for GitHub PR and commit webhook events."""

    @property
    def name(self) -> str:
        return "github"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["code"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a GitHub webhook payload into a Code surface subject.

        Supports ``pull_request`` and ``push`` event types. Extracts diff
        content, file paths, repository, and author information.

        Args:
            event: Raw GitHub webhook payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload for the Code surface.
        """
        action = event.get("action", "")
        pull_request = event.get("pull_request", {})
        repository = event.get("repository", {})

        diff = pull_request.get("diff", event.get("diff", ""))
        file_paths: list[str] = []
        if "files" in event:
            file_paths = [f.get("filename", "") for f in event["files"] if f.get("filename")]
        elif "commits" in event:
            for commit in event["commits"]:
                file_paths.extend(commit.get("added", []))
                file_paths.extend(commit.get("modified", []))

        sender = event.get("sender", {})
        actor_identifier = sender.get("login", "unknown")

        return {
            "surface": "code",
            "identifier": pull_request.get("html_url", repository.get("full_name", "")),
            "payload": {
                "diff": diff,
                "file_paths": file_paths,
                "repository": repository.get("full_name", ""),
                "branch": pull_request.get("head", {}).get("ref", event.get("ref", "")),
                "action": action,
            },
            "facts": {
                "pr_number": pull_request.get("number"),
                "title": pull_request.get("title", ""),
                "author": actor_identifier,
            },
            "actor": {
                "kind": "system",
                "identifier": f"github:{actor_identifier}",
            },
            "timestamp": datetime.now(UTC).isoformat(),
            "locale": "en",
        }

    async def validate_connection(self) -> bool:
        """Check that GITHUB_TOKEN is configured."""
        return bool(os.environ.get("GITHUB_TOKEN"))

    async def list_event_types(self) -> list[str]:
        return ["pull_request", "push"]
