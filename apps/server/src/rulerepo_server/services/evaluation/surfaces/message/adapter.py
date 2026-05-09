"""Message surface adapter — evaluates communications.

Handles email, Slack messages, Teams messages, and other communication
channels. See CLAUDE.md §14.6.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "message_hints.txt"


class MessageSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for communication message evaluation.

    Handles email, Slack, Teams, and other messaging channels subject
    to communication policies, harassment rules, confidentiality rules,
    and regulatory compliance.
    """

    @property
    def surface(self) -> Surface:
        return Surface.MESSAGE

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a communication message into a uniform subject.

        Expected payload keys:
            - content: str — message body text
            - channel: str — communication channel (email, slack, teams)
            - sender: str — sender identifier
            - recipients: list[str] — recipient identifiers
            - thread_id: str — thread or conversation identifier
            - facts: dict — additional structured facts

        Returns:
            EvaluationSubjectPayload with message-specific fields.
        """
        content = payload.get("content", "")
        channel = payload.get("channel", "unknown")
        sender = payload.get("sender", "unknown")
        recipients = payload.get("recipients", [])
        thread_id = payload.get("thread_id", "")

        recipients_str = ", ".join(recipients[:5]) if recipients else "unknown"
        if len(recipients) > 5:
            recipients_str += f" (+{len(recipients) - 5} more)"

        description = f"Message via {channel} from {sender} to {recipients_str}:\n\n{content}"

        facts = dict(payload.get("facts", {}))
        facts["channel"] = channel
        facts["recipient_count"] = len(recipients)

        thread_part = f"/thread:{thread_id}" if thread_id else ""
        identifier = f"message:{channel}/{sender}{thread_part}"

        return EvaluationSubjectPayload(
            surface=Surface.MESSAGE,
            identifier=identifier,
            description=description,
            payload={
                "content": content,
                "channel": channel,
                "sender": sender,
                "recipients": recipients,
                "thread_id": thread_id,
            },
            facts=facts,
            locale=payload.get("locale", "en"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from channel type."""
        scopes: set[str] = set()

        channel = payload.get("channel", "")
        if channel == "email":
            scopes.add("communications/email")
        elif channel == "slack" or channel == "teams":
            scopes.add("communications/chat")
        else:
            scopes.add(f"communications/{channel}")

        return sorted(scopes) if scopes else ["communications/general"]

    def get_prompt_hints(self) -> str:
        """Return message-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a communication message for compliance with "
            "organizational communication policies. Focus on harassment "
            "prevention, confidentiality of customer data, regulated-substance "
            "discussion, product-claim accuracy, and appropriate tone. Do not "
            "provide code-level remediations; instead describe the policy "
            "issue and suggest revised language."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["sender", "recipients", "facts.customer_name"]

    @property
    def default_audit_retention_days(self) -> int:
        return 1095  # 3 years for communication records
