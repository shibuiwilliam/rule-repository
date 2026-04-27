"""GitHub webhook event normalizer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.gateway.normalizers.base import EventNormalizer
from rulerepo_server.gateway.schemas import NormalizedEvent


class GitHubNormalizer(EventNormalizer):
    """Normalizes GitHub webhook payloads into NormalizedEvent."""

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Convert a GitHub webhook payload.

        Supports: pull_request, push, issues, and other common events.
        """
        action = payload.get("action", "")
        event_type_parts = []

        if "pull_request" in payload:
            event_type_parts = ["pull_request", action]
            pr = payload["pull_request"]
            subject = f"PR #{pr.get('number', '?')}: {pr.get('title', 'untitled')}"
            actor = pr.get("user", {}).get("login", "unknown")
            metadata = {
                "pr_number": pr.get("number"),
                "title": pr.get("title"),
                "body": (pr.get("body") or "")[:500],
                "base_branch": pr.get("base", {}).get("ref"),
                "head_branch": pr.get("head", {}).get("ref"),
                "changed_files": pr.get("changed_files", 0),
                "repo": payload.get("repository", {}).get("full_name"),
            }
        elif "issue" in payload:
            event_type_parts = ["issues", action]
            issue = payload["issue"]
            subject = f"Issue #{issue.get('number', '?')}: {issue.get('title', 'untitled')}"
            actor = issue.get("user", {}).get("login", "unknown")
            metadata = {
                "issue_number": issue.get("number"),
                "title": issue.get("title"),
                "body": (issue.get("body") or "")[:500],
                "repo": payload.get("repository", {}).get("full_name"),
            }
        else:
            event_type_parts = ["github", action or "unknown"]
            subject = f"GitHub event: {action}"
            actor = payload.get("sender", {}).get("login", "unknown")
            metadata = {"repo": payload.get("repository", {}).get("full_name")}

        return NormalizedEvent(
            source="github",
            event_type=".".join(filter(None, event_type_parts)),
            actor=actor,
            subject=subject,
            metadata=metadata,
            raw_payload=payload,
            timestamp=datetime.now(tz=UTC),
        )
