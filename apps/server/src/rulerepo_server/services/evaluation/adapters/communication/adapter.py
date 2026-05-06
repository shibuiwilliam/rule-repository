"""Communication domain adapter for the evaluation engine.

Evaluates messages (Slack, Teams, email, etc.) against communication rules
covering tone, sensitivity, audience appropriateness, and policy compliance.

Per CLAUDE.md Tier 4.1: communication adapter + Slack/Teams/Email gateways.
"""

from __future__ import annotations

from rulerepo_server.domain.evaluation import EvaluationContext

# Mapping from channel sensitivity level to rule scopes.
_SENSITIVITY_SCOPE_MAP: dict[str, list[str]] = {
    "public": ["communication/public"],
    "internal": ["communication/internal"],
    "confidential": ["communication/confidential", "communication/internal"],
    "restricted": [
        "communication/restricted",
        "communication/confidential",
        "communication/internal",
    ],
}

# Default scopes applied to all communication evaluations.
_BASE_SCOPES: list[str] = ["communication"]


class CommunicationAdapter:
    """Adapter for evaluating communication messages against rules.

    Supports messages from various channels (Slack, Teams, email) with
    sensitivity-based scope resolution.

    Attributes:
        domain: The domain discriminator string.
    """

    domain: str = "communication"

    async def parse(self, payload: dict) -> EvaluationContext:
        """Parse a communication payload into an EvaluationContext.

        Expected payload fields:
            message (str): The message text to evaluate.
            channel (str, optional): Channel name or identifier.
            sender (str, optional): Sender identity.
            thread_id (str, optional): Conversation thread identifier.
            sensitivity (str, optional): Channel sensitivity level
                (public, internal, confidential, restricted). Defaults to "internal".
            recipients (list[str], optional): List of recipient identifiers.
            subject (str, optional): Message subject line (for email).

        Args:
            payload: The communication-specific request payload.

        Returns:
            A unified EvaluationContext with communication facts.
        """
        message = payload.get("message", "")
        channel = payload.get("channel")
        sender = payload.get("sender")
        thread_id = payload.get("thread_id")
        sensitivity = payload.get("sensitivity", "internal")
        recipients = payload.get("recipients", [])
        subject = payload.get("subject")

        facts: dict = {
            "message": message,
            "sensitivity": sensitivity,
        }
        if channel:
            facts["channel"] = channel
        if thread_id:
            facts["thread_id"] = thread_id
        if recipients:
            facts["recipients"] = recipients
        if subject:
            facts["subject"] = subject

        # Build a narrative summary for the LLM
        narrative_parts = [f"Message in {sensitivity} channel"]
        if channel:
            narrative_parts.append(f"(#{channel})")
        if sender:
            narrative_parts.append(f"from {sender}")
        narrative_parts.append(f": {message[:500]}")

        return EvaluationContext(
            actor=sender,
            facts=facts,
            narrative=" ".join(narrative_parts),
        )

    def resolve_scopes(self, payload: dict) -> list[str]:
        """Resolve rule scopes based on channel sensitivity.

        Maps channel sensitivity levels to rule scopes. Higher sensitivity
        levels include all lower-sensitivity scopes (e.g., confidential
        includes internal rules).

        Args:
            payload: The communication-specific request payload.

        Returns:
            Deduplicated list of applicable scope strings.
        """
        sensitivity = payload.get("sensitivity", "internal")
        scopes = list(_BASE_SCOPES)

        extra = _SENSITIVITY_SCOPE_MAP.get(sensitivity, _SENSITIVITY_SCOPE_MAP["internal"])
        for scope in extra:
            if scope not in scopes:
                scopes.append(scope)

        return scopes

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return communication-specific prompt fragments.

        Returns:
            Mapping of placeholder name to prompt text fragment.
        """
        return {
            "domain_intro": (
                "You are evaluating a communication message (e.g., Slack message, "
                "email, Teams chat) against organizational communication rules. "
                "Consider tone, sensitivity, audience appropriateness, information "
                "classification, and policy compliance."
            ),
            "context_format": (
                "The input is a message with metadata including channel, sender, "
                "sensitivity level, and optionally recipients and subject. "
                "Evaluate whether the message content is appropriate for the "
                "channel's sensitivity level and complies with communication policies."
            ),
            "verdict_guidance": (
                "DENY if the message violates a communication rule (e.g., sharing "
                "confidential information in a public channel, inappropriate tone, "
                "policy violation). ALLOW if the message complies with all applicable "
                "rules. NEEDS_CONFIRMATION if the evaluation is uncertain or the "
                "message is borderline."
            ),
        }
