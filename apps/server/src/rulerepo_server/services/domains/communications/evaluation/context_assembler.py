"""Communications context assembler — transforms email/chat artifacts into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class CommunicationsContextAssembler:
    """Assembles LLM-ready context from communication artifacts.

    Handles:
    - email_message: sender, recipients, subject, body, attachments, classification
    - chat_message: sender, channel/DM, message text, thread context, platform
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        artifact_type = evaluable.get("artifact_type", "email_message")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        if artifact_type == "email_message":
            return self._assemble_email(payload, metadata)
        elif artifact_type == "chat_message":
            return self._assemble_chat(payload, metadata)
        else:
            context = str(payload)
            logger.debug(
                "communications_context_fallback",
                artifact_type=artifact_type,
                length=len(context),
            )
            return context

    def _assemble_email(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        """Assemble context for an email message artifact."""
        parts: list[str] = []

        # Sender and recipients
        if sender := payload.get("sender"):
            parts.append(f"From: {sender}")
        if recipients := payload.get("recipients"):
            if isinstance(recipients, list):
                parts.append(f"To: {', '.join(recipients)}")
            else:
                parts.append(f"To: {recipients}")
        if cc := payload.get("cc"):
            if isinstance(cc, list):
                parts.append(f"CC: {', '.join(cc)}")
            else:
                parts.append(f"CC: {cc}")

        # Subject
        if subject := payload.get("subject"):
            parts.append(f"Subject: {subject}")

        # Classification level
        classification = payload.get(
            "classification_level",
            metadata.get("classification_level", ""),
        )
        if classification:
            parts.append(f"Classification: {classification}")

        # Direction (internal/external)
        if direction := payload.get("direction", metadata.get("direction")):
            parts.append(f"Direction: {direction}")

        # Body
        if body := payload.get("body", ""):
            parts.append(f"\n--- EMAIL BODY ---\n{body}")

        # Attachments summary
        if attachments := payload.get("attachments"):
            if isinstance(attachments, list):
                summary = ", ".join(a if isinstance(a, str) else a.get("name", str(a)) for a in attachments)
            else:
                summary = str(attachments)
            parts.append(f"\nAttachments: {summary}")

        context = "\n".join(parts)
        logger.debug(
            "email_context_assembled",
            length=len(context),
            has_attachments=bool(attachments),
        )
        return context

    def _assemble_chat(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        """Assemble context for a chat message artifact."""
        parts: list[str] = []

        # Platform
        platform = payload.get("platform", metadata.get("platform", ""))
        if platform:
            parts.append(f"Platform: {platform}")

        # Sender
        if sender := payload.get("sender"):
            parts.append(f"Sender: {sender}")

        # Channel or DM
        if channel := payload.get("channel"):
            parts.append(f"Channel: {channel}")
        if payload.get("is_dm", metadata.get("is_dm")):
            parts.append("Type: Direct Message")
        elif channel:
            channel_type = payload.get(
                "channel_type",
                metadata.get("channel_type", ""),
            )
            if channel_type:
                parts.append(f"Channel Type: {channel_type}")

        # Visibility
        if visibility := payload.get("visibility", metadata.get("visibility")):
            parts.append(f"Visibility: {visibility}")

        # Message text
        if message := payload.get("message", payload.get("text", "")):
            parts.append(f"\n--- MESSAGE ---\n{message}")

        # Thread context (previous messages for context)
        if thread_context := payload.get("thread_context"):
            if isinstance(thread_context, list):
                thread_text = "\n".join(
                    f"  [{m.get('sender', '?')}]: {m.get('text', '')}" for m in thread_context if isinstance(m, dict)
                )
            else:
                thread_text = str(thread_context)
            parts.append(f"\n--- THREAD CONTEXT ---\n{thread_text}")

        context = "\n".join(parts)
        logger.debug(
            "chat_context_assembled",
            platform=platform,
            length=len(context),
        )
        return context
