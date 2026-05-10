"""Message surface adapter — evaluates communications.

Provides channel detection, recipient analysis (internal vs external),
content classification (PII, claims, confidential info), and
channel+recipient-based scope resolution.

See CLAUDE.md §14.5 for the Communication Evaluation Path.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "message_hints.txt"

# --------------------------------------------------------------------------
# Channel classification
# --------------------------------------------------------------------------

_CHANNEL_TYPES: dict[str, str] = {
    "email": "email",
    "slack": "chat",
    "teams": "chat",
    "discord": "chat",
    "line": "chat",
    "sms": "sms",
    "twitter": "social",
    "x": "social",
    "linkedin": "social",
    "facebook": "social",
    "instagram": "social",
    "press_release": "press",
    "blog": "content",
    "newsletter": "content",
    "customer_support": "support",
    "chatbot": "support",
}

# Channel → scope mapping (channel_category + audience determines scope)
_CHANNEL_SCOPE_MAP: dict[str, dict[str, list[str]]] = {
    "email": {
        "external": ["sales/communication", "compliance/data-protection"],
        "internal": ["general/internal-communication"],
        "customer": ["sales/communication", "compliance/consumer-protection"],
        "regulatory": ["compliance/regulatory-communication"],
    },
    "chat": {
        "external": ["communications/external"],
        "internal": ["general/internal-communication"],
        "customer": ["sales/communication"],
    },
    "social": {
        "external": ["marketing/external", "compliance/advertising"],
        "internal": ["general/internal-communication"],
    },
    "press": {
        "external": ["marketing/external", "compliance/disclosure", "legal/public-statement"],
    },
    "content": {
        "external": ["marketing/external", "compliance/advertising"],
        "internal": ["general/internal-communication"],
    },
    "support": {
        "customer": ["sales/communication", "compliance/consumer-protection"],
        "external": ["sales/communication"],
    },
}

# --------------------------------------------------------------------------
# PII detection patterns
# --------------------------------------------------------------------------

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email_address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone_jp": re.compile(r"(?:0\d{1,4}-?\d{1,4}-?\d{3,4})"),
    "phone_intl": re.compile(r"\+\d{1,3}[\s-]?\d{3,}[\s-]?\d{3,}"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "my_number_jp": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),  # 12-digit Japanese My Number
    "postal_code_jp": re.compile(r"\b\d{3}-\d{4}\b"),
    "account_number": re.compile(r"(?:口座番号|account\s*(?:no|number|#))[\s:\uff1a]*\d{5,}", re.IGNORECASE),
}

# Content classification patterns
_CLAIM_PATTERNS: dict[str, re.Pattern[str]] = {
    "health_claim": re.compile(
        r"(?:治る|治療|効果|効能|改善|痩せる|cure|treat|heal|miracle|proven\s+to)",
        re.IGNORECASE,
    ),
    "financial_claim": re.compile(
        r"(?:guaranteed\s+return|確実に儲かる|元本保証|利回り保証|必ず.*利益)",
        re.IGNORECASE,
    ),
    "legal_claim": re.compile(
        r"(?:legally\s+binding|法的拘束力|契約.*成立|guarantee.*compliance)",
        re.IGNORECASE,
    ),
    "superlative_claim": re.compile(
        r"(?:最高|最安|日本一|世界一|No\.\s*1|best\s+in|#1|number\s+one|業界初)",
        re.IGNORECASE,
    ),
}

# Confidential information markers
_CONFIDENTIAL_PATTERNS = re.compile(
    r"(?:confidential|機密|社外秘|部外秘|取扱注意|internal\s+only|do\s+not\s+distribute|NDA)",
    re.IGNORECASE,
)


def _classify_channel(channel: str) -> str:
    """Classify channel into a category."""
    channel_lower = channel.lower().replace(" ", "_").replace("-", "_")
    return _CHANNEL_TYPES.get(channel_lower, "other")


def _classify_audience(recipients: list[str], payload_audience: str | None, sender_domain: str | None) -> str:
    """Classify audience as internal, external, customer, or regulatory."""
    if payload_audience:
        return payload_audience.lower()

    if not recipients:
        return "external"  # Conservative default

    # Check if recipients share domain with sender
    if sender_domain:
        external_count = sum(1 for r in recipients if "@" in r and not r.lower().endswith(f"@{sender_domain}"))
        if external_count == 0:
            return "internal"

    # Heuristic: check for regulatory/government domains
    regulatory_domains = {"go.jp", "gov", "fsa.go.jp", "mhlw.go.jp", "sec.gov"}
    for r in recipients:
        r_lower = r.lower()
        if any(d in r_lower for d in regulatory_domains):
            return "regulatory"

    return "external"


def _detect_pii(content: str) -> list[dict[str, str]]:
    """Detect PII patterns in message content."""
    findings: list[dict[str, str]] = []
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(content)
        if matches:
            findings.append(
                {
                    "type": pii_type,
                    "count": str(len(matches)),
                    "sample": matches[0][:20] + "..." if len(matches[0]) > 20 else matches[0],
                }
            )
    return findings


def _detect_claims(content: str) -> list[str]:
    """Detect potentially problematic claims in content."""
    found: list[str] = []
    for claim_type, pattern in _CLAIM_PATTERNS.items():
        if pattern.search(content):
            found.append(claim_type)
    return found


def _detect_confidential_markers(content: str) -> bool:
    """Check if content contains confidentiality markers."""
    return bool(_CONFIDENTIAL_PATTERNS.search(content))


class MessageSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for communication message evaluation.

    Handles email, Slack, Teams, social media, press releases, and other
    messaging channels. Provides channel classification, audience detection,
    PII scanning, claim detection, and confidentiality checks.
    """

    @property
    def surface(self) -> Surface:
        return Surface.MESSAGE

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a communication message into a uniform subject.

        Expected payload keys:
            - content: str — message body text
            - subject_line: str — email subject or message title
            - channel: str — communication channel (email, slack, teams, etc.)
            - sender: str — sender identifier (email or user ID)
            - recipients: list[str] — recipient identifiers
            - audience: str — explicit audience classification (internal/external/customer/regulatory)
            - thread_id: str — thread or conversation identifier
            - attachments: list[str] — attachment filenames
            - facts: dict — additional structured facts

        Returns:
            EvaluationSubjectPayload with message-specific fields.
        """
        content = payload.get("content", "")
        subject_line = payload.get("subject_line", "")
        channel = payload.get("channel", "unknown")
        sender = payload.get("sender", "unknown")
        recipients = payload.get("recipients", [])
        thread_id = payload.get("thread_id", "")

        # Classify channel and audience
        channel_category = _classify_channel(channel)
        sender_domain = sender.split("@")[-1].lower() if "@" in sender else None
        audience = _classify_audience(recipients, payload.get("audience"), sender_domain)

        # Content analysis
        full_text = f"{subject_line}\n{content}" if subject_line else content
        pii_findings = _detect_pii(full_text)
        claims_found = _detect_claims(full_text)
        has_confidential_markers = _detect_confidential_markers(full_text)

        # Build description
        recipients_str = ", ".join(recipients[:5]) if recipients else "unknown"
        if len(recipients) > 5:
            recipients_str += f" (+{len(recipients) - 5} more)"

        description = f"Message via {channel} ({audience}) from {sender} to {recipients_str}"
        if subject_line:
            description += f"\nSubject: {subject_line}"
        description += f"\n\n{content}"

        # Build facts
        facts = dict(payload.get("facts", {}))
        facts["channel"] = channel
        facts["channel_category"] = channel_category
        facts["audience"] = audience
        facts["recipient_count"] = len(recipients)
        if pii_findings:
            facts["pii_detected"] = pii_findings
        if claims_found:
            facts["unverified_claims"] = claims_found
        if has_confidential_markers:
            facts["contains_confidential_markers"] = True
        if payload.get("attachments"):
            facts["attachment_count"] = len(payload["attachments"])

        # Build identifier
        thread_part = f"/thread:{thread_id}" if thread_id else ""
        identifier = f"message:{channel}/{sender}{thread_part}"

        return EvaluationSubjectPayload(
            surface=Surface.MESSAGE,
            identifier=identifier,
            description=description,
            payload={
                "content": content,
                "subject_line": subject_line,
                "channel": channel,
                "channel_category": channel_category,
                "sender": sender,
                "recipients": recipients,
                "audience": audience,
                "thread_id": thread_id,
                "pii_detected": pii_findings,
                "claims_detected": claims_found,
                "confidential_markers": has_confidential_markers,
            },
            facts=facts,
            locale=payload.get("locale", "ja"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from channel category and audience.

        Uses channel+audience → scope mapping equivalent to the code adapter's
        file-path → language scope mapping.
        """
        scopes: set[str] = set()

        channel_category = _classify_channel(payload.get("channel", ""))
        audience = payload.get("audience", "external")

        # Map channel_category + audience to scopes
        channel_scopes = _CHANNEL_SCOPE_MAP.get(channel_category, {})
        if audience in channel_scopes:
            scopes.update(channel_scopes[audience])
        elif "external" in channel_scopes and audience != "internal":
            scopes.update(channel_scopes["external"])

        # Always add base communication scope
        scopes.add(f"communications/{channel_category}")

        # Add data protection scope if PII is likely (external recipients)
        if audience in ("external", "customer", "regulatory"):
            scopes.add("compliance/data-protection")

        return sorted(scopes) if scopes else ["communications/general"]

    def get_prompt_hints(self) -> str:
        """Return message-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a communication message for compliance with "
            "organizational policies. Focus on PII exposure, unverified claims, "
            "confidentiality, and channel-appropriate conduct."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        fields = ["sender", "recipients"]
        if payload.get("facts", {}).get("customer_name"):
            fields.append("facts.customer_name")
        return fields

    @property
    def default_audit_retention_days(self) -> int:
        return 1095  # 3 years for communication records
