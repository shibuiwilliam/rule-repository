"""Change Communication Service — notifies stakeholders of rule changes (RR-038).

When rules are created, modified, or retired, affected stakeholders
receive notifications through configured channels (webhook, email,
Slack, etc.).

See IMPROVEMENT.md §9.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChangeNotification:
    """A notification about a rule change."""

    rule_id: str
    change_type: str  # "created", "updated", "retired", "effective_date"
    summary: str
    affected_scopes: list[str] = field(default_factory=list)
    notified_channels: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class ChangeCommunicationService:
    """Manages change notifications for rule updates."""

    def __init__(self) -> None:
        self._notifications: list[ChangeNotification] = []
        self._subscribers: dict[str, list[str]] = {}

    def subscribe(self, scope: str, channel: str) -> None:
        """Subscribe a channel to notifications for a scope.

        Args:
            scope: Scope pattern (e.g., ``legal/*``, ``hr/attendance``).
            channel: Notification channel (e.g., ``webhook:url``,
                ``slack:#channel``, ``email:team@co.com``).
        """
        if scope not in self._subscribers:
            self._subscribers[scope] = []
        if channel not in self._subscribers[scope]:
            self._subscribers[scope].append(channel)
        logger.info("change_subscription_added", scope=scope, channel=channel)

    async def notify_change(
        self,
        *,
        rule_id: str,
        change_type: str,
        summary: str,
        scopes: list[str] | None = None,
    ) -> ChangeNotification:
        """Send notifications about a rule change.

        Finds all subscribers whose scope pattern matches any of the
        rule's scopes and dispatches to their configured channels.
        """
        import fnmatch

        affected_scopes = scopes or []
        channels: list[str] = []

        for pattern, subs in self._subscribers.items():
            for scope in affected_scopes:
                if fnmatch.fnmatch(scope, pattern):
                    channels.extend(subs)
                    break

        channels = list(set(channels))

        notification = ChangeNotification(
            rule_id=rule_id,
            change_type=change_type,
            summary=summary,
            affected_scopes=affected_scopes,
            notified_channels=channels,
        )
        self._notifications.append(notification)

        # In production, dispatch to actual channels
        for channel in channels:
            logger.info(
                "change_notification_dispatched",
                rule_id=rule_id,
                channel=channel,
                change_type=change_type,
            )

        return notification

    def get_recent_notifications(
        self,
        *,
        limit: int = 50,
        scope: str | None = None,
    ) -> list[ChangeNotification]:
        """Get recent change notifications."""
        results = list(reversed(self._notifications))
        if scope:
            results = [n for n in results if scope in n.affected_scopes]
        return results[:limit]
