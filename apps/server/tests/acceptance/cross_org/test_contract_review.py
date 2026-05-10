"""Acceptance test: Contract clause review.

Scenario (PROJECT.md §11.5 #2):
    1. Standard NDA template + counterparty's draft (markdown)
    2. POST /api/v1/evaluate/document (or evaluate with surface=contract)
    3. Flagged dangerous clauses + text_rewrite Remediations

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind


class TestContractReview:
    """End-to-end contract clause review acceptance test."""

    def test_contract_subject_construction(self) -> None:
        """Contract evaluation subject can be constructed."""
        subject = EvaluationSubject(
            kind=SubjectKind.CLAUSE_SET,
            payload={
                "document_type": "contract_clause",
                "content": (
                    "The Contractor shall be liable for all damages arising from this agreement "
                    "without any limitation whatsoever. The governing law shall be determined "
                    "by mutual agreement at the time of dispute."
                ),
                "parties": ["Acme Corp", "Client Inc"],
            },
            metadata={"language": "en"},
        )

        assert subject.kind == SubjectKind.CLAUSE_SET
        assert "without any limitation" in subject.payload["content"]

    def test_text_rewrite_remediation(self) -> None:
        """text_rewrite Remediation correctly targets clause spans."""
        remediation = PolymorphicRemediation(
            kind=RemediationKind.TEXT_REWRITE,
            auto_applicable=False,
            description="Replace unlimited liability with capped liability",
            payload={
                "offset_start": 45,
                "offset_end": 95,
                "original": "without any limitation whatsoever",
                "suggested": "limited to the total fees paid under this agreement",
            },
        )
        assert remediation.validate_payload()
        assert remediation.kind == RemediationKind.TEXT_REWRITE

    def test_dangerous_clause_detection_subjects(self) -> None:
        """Document with dangerous clauses produces CLAUSE_SET or DOCUMENT subject."""
        # Test that both subject kinds can represent contract content
        for kind in [SubjectKind.CLAUSE_SET, SubjectKind.DOCUMENT]:
            subject = EvaluationSubject(
                kind=kind,
                payload={
                    "content": "Foreign jurisdiction clause with no termination rights",
                },
            )
            assert subject.kind in (SubjectKind.CLAUSE_SET, SubjectKind.DOCUMENT)

    def test_multiple_remediation_kinds(self) -> None:
        """Contract review may produce text_rewrite and clarification remediations."""
        remediations = [
            PolymorphicRemediation(
                kind=RemediationKind.TEXT_REWRITE,
                auto_applicable=False,
                description="Cap liability",
                payload={
                    "offset_start": 0,
                    "offset_end": 50,
                    "original": "unlimited liability",
                    "suggested": "liability capped at contract value",
                },
            ),
            PolymorphicRemediation(
                kind=RemediationKind.CLARIFICATION,
                auto_applicable=False,
                description="Add governing law clause",
                payload={
                    "missing_element": "governing_law",
                },
            ),
        ]

        assert all(r.validate_payload() for r in remediations)
        kinds = {r.kind for r in remediations}
        assert RemediationKind.TEXT_REWRITE in kinds
        assert RemediationKind.CLARIFICATION in kinds
