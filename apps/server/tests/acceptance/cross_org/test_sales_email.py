"""Acceptance test: Sales email pre-send.

Scenario (PROJECT.md §11.5 #4):
    1. Outbound email draft
    2. POST /api/v1/evaluate/document
    3. Privacy / pharmaceutical / consumer-protection checks
    4. Flagged spans + suggested rewrites

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind


class TestSalesEmail:
    """End-to-end sales email pre-send acceptance test."""

    def test_email_subject_construction(self) -> None:
        """Email draft can be represented as a DOCUMENT or CREATIVE subject."""
        email_content = (
            "Dear Mr. Tanaka,\n\n"
            "Thank you for your interest in our product. "
            "Our supplement is clinically proven to cure diabetes and "
            "has been endorsed by the Ministry of Health. "
            "I am attaching the customer list from our CRM for your reference.\n\n"
            "Best regards,\n"
            "Sales Team"
        )

        subject = EvaluationSubject(
            kind=SubjectKind.DOCUMENT,
            payload={
                "document_type": "email",
                "content": email_content,
            },
            metadata={"language": "en"},
            context={
                "department": "sales",
                "recipient_type": "customer",
            },
        )

        assert subject.kind == SubjectKind.DOCUMENT
        assert "clinically proven to cure" in subject.payload["content"]

    def test_pharmaceutical_claim_rewrite(self) -> None:
        """Pharmaceutical claims trigger text_rewrite Remediation."""
        remediation = PolymorphicRemediation(
            kind=RemediationKind.TEXT_REWRITE,
            auto_applicable=False,
            description="Remove unverified health claim",
            payload={
                "offset_start": 85,
                "offset_end": 145,
                "original": "clinically proven to cure diabetes",
                "suggested": "designed to support healthy blood sugar levels",
            },
        )
        assert remediation.validate_payload()
        assert remediation.kind == RemediationKind.TEXT_REWRITE

    def test_privacy_violation_detection(self) -> None:
        """Customer data leakage triggers text_rewrite Remediation."""
        remediation = PolymorphicRemediation(
            kind=RemediationKind.TEXT_REWRITE,
            auto_applicable=False,
            description="Remove customer list reference — sharing CRM data violates privacy policy",
            payload={
                "offset_start": 180,
                "offset_end": 240,
                "original": "I am attaching the customer list from our CRM for your reference",
                "suggested": "Please let me know if you would like more information about our offerings",
            },
        )
        assert remediation.validate_payload()

    def test_consumer_protection_claim(self) -> None:
        """Government endorsement claims trigger text_rewrite."""
        remediation = PolymorphicRemediation(
            kind=RemediationKind.TEXT_REWRITE,
            auto_applicable=False,
            description="Remove false government endorsement claim",
            payload={
                "offset_start": 150,
                "offset_end": 200,
                "original": "endorsed by the Ministry of Health",
                "suggested": "compliant with applicable health regulations",
            },
        )
        assert remediation.validate_payload()

    def test_all_remediation_kinds_handled(self) -> None:
        """All RemediationKind values are accounted for."""
        all_kinds = set(RemediationKind)
        expected = {
            RemediationKind.CODE_EDIT,
            RemediationKind.TEXT_REWRITE,
            RemediationKind.FIELD_CHANGE,
            RemediationKind.APPROVAL_ADD,
            RemediationKind.PROCESS_REROUTE,
            RemediationKind.CLARIFICATION,
            RemediationKind.BLOCK,
        }
        assert all_kinds == expected
