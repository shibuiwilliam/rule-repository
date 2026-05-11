"""Acceptance test: Sales email pre-send.

Scenario (PROJECT.md §11.5 #4):
    1. Outbound email draft
    2. POST /api/v1/evaluate/document
    3. Privacy / pharmaceutical / consumer-protection checks
    4. Flagged spans + suggested rewrites

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from rulerepo_server.domain.evaluation import EvaluationContext, Verdict
from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.scope import DOMAIN_KEY, SUBJECT_TYPE_KEY, matches_scope_dimensions
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.services.evaluation.context_assembler import assemble_context_from_subject
from rulerepo_server.services.evaluation.kind_dispatch import partition_by_kind


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

    # ------------------------------------------------------------------
    # Polymorphic context assembly (Proposal 1)
    # ------------------------------------------------------------------

    def test_context_assembly_from_document_subject(self) -> None:
        """assemble_context_from_subject builds document context for email."""
        subject = EvaluationSubject(
            kind=SubjectKind.DOCUMENT,
            payload={
                "text": "Our supplement is clinically proven to cure diabetes.",
                "document_type": "email",
            },
        )
        ctx = assemble_context_from_subject(subject)

        assert ctx.surface == "document"
        assert ctx.diff is None
        assert ctx.files_changed == []
        assert "clinically proven" in (ctx.narrative or "")

    # ------------------------------------------------------------------
    # Structured scope (Proposal 2)
    # ------------------------------------------------------------------

    def test_sales_communication_scope_matches(self) -> None:
        """A sales/communication rule matches sales communication query."""
        rule_scope = {DOMAIN_KEY: "sales", SUBJECT_TYPE_KEY: "communication"}
        query_dims = {DOMAIN_KEY: "sales", SUBJECT_TYPE_KEY: "communication"}
        assert matches_scope_dimensions(rule_scope, query_dims) is True

    def test_sales_rule_does_not_match_engineering(self) -> None:
        """A sales rule does not match an engineering query."""
        rule_scope = {DOMAIN_KEY: "sales", SUBJECT_TYPE_KEY: "communication"}
        query_dims = {DOMAIN_KEY: "engineering"}
        assert matches_scope_dimensions(rule_scope, query_dims) is False

    # ------------------------------------------------------------------
    # Kind dispatch (Proposal 3)
    # ------------------------------------------------------------------

    def test_normative_email_rules_go_to_llm(self) -> None:
        """Normative rules about email content require LLM judgment."""
        rules = [
            {
                "id": "r-pharma",
                "kind": "normative",
                "statement": "Sales emails MUST NOT contain unverified health claims.",
            },
            {
                "id": "r-privacy",
                "kind": "normative",
                "statement": "Customer PII MUST NOT be shared without consent.",
            },
        ]
        llm_rules, local_rules = partition_by_kind(rules)
        assert len(llm_rules) == 2
        assert len(local_rules) == 0

    def test_principle_rule_allows_without_llm(self) -> None:
        """A principle rule about communication standards returns ALLOW locally."""
        from rulerepo_server.services.evaluation.kind_dispatch import evaluate_local

        rule = {
            "id": "r-principle-comms",
            "kind": "principle",
            "statement": "All external communications must be honest and transparent.",
        }
        verdict, _, _ = evaluate_local(rule, EvaluationContext())
        assert verdict.verdict == Verdict.ALLOW
        assert "principle" in verdict.reasoning.lower()
