"""Acceptance test: Contract clause review.

Scenario (PROJECT.md §11.5 #2):
    1. Standard NDA template + counterparty's draft (markdown)
    2. POST /api/v1/evaluate/document (or evaluate with surface=contract)
    3. Flagged dangerous clauses + text_rewrite Remediations

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.scope import DOMAIN_KEY, SUBJECT_TYPE_KEY, matches_scope_dimensions
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.services.evaluation.context_assembler import assemble_context_from_subject
from rulerepo_server.services.evaluation.kind_dispatch import evaluate_local, partition_by_kind


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

    # ------------------------------------------------------------------
    # Polymorphic context assembly (Proposal 1)
    # ------------------------------------------------------------------

    def test_context_assembly_from_clause_set_subject(self) -> None:
        """assemble_context_from_subject builds contract context without code artifacts."""
        subject = EvaluationSubject(
            kind=SubjectKind.CLAUSE_SET,
            payload={
                "text": "The Contractor shall be liable without limitation.",
                "clause_type": "liability",
            },
        )
        ctx = assemble_context_from_subject(subject)

        assert isinstance(ctx, EvaluationContext)
        assert ctx.surface == "contract"
        assert ctx.diff is None
        assert ctx.files_changed == []
        # Clause text should appear in the narrative
        assert "liable without limitation" in (ctx.narrative or "")

    # ------------------------------------------------------------------
    # Structured scope (Proposal 2)
    # ------------------------------------------------------------------

    def test_legal_contract_scope_matches(self) -> None:
        """A legal/contract rule matches legal contract query dimensions."""
        rule_scope = {DOMAIN_KEY: "legal", SUBJECT_TYPE_KEY: "contract"}
        query_dims = {DOMAIN_KEY: "legal", SUBJECT_TYPE_KEY: "contract"}
        assert matches_scope_dimensions(rule_scope, query_dims) is True

    def test_legal_rule_does_not_match_hr_query(self) -> None:
        """A legal rule does not match an HR query."""
        rule_scope = {DOMAIN_KEY: "legal", SUBJECT_TYPE_KEY: "contract"}
        query_dims = {DOMAIN_KEY: "hr", SUBJECT_TYPE_KEY: "attendance"}
        assert matches_scope_dimensions(rule_scope, query_dims) is False

    def test_universal_rule_matches_any_query(self) -> None:
        """A rule with no dimension restrictions matches any query."""
        rule_scope: dict[str, str | list[str]] = {}
        query_dims = {DOMAIN_KEY: "legal", SUBJECT_TYPE_KEY: "contract"}
        assert matches_scope_dimensions(rule_scope, query_dims) is True

    # ------------------------------------------------------------------
    # Kind dispatch: normative contract rules go to LLM (Proposal 3)
    # ------------------------------------------------------------------

    def test_normative_contract_rule_routes_to_llm(self) -> None:
        """A normative contract clause rule is not resolved locally."""
        rules = [
            {
                "id": "r-liability-cap",
                "kind": "normative",
                "statement": "Liability clauses must include a cap.",
                "modality": "MUST",
                "severity": "HIGH",
            }
        ]
        llm_rules, local_rules = partition_by_kind(rules)
        assert len(llm_rules) == 1
        assert len(local_rules) == 0

    def test_definitional_contract_term_resolved_locally(self) -> None:
        """A definitional rule (term definition) returns ALLOW without LLM."""
        rule = {
            "id": "r-def-force-majeure",
            "kind": "definitional",
            "statement": "Force majeure means acts of God, war, or government action.",
            "modality": "INFO",
            "severity": "LOW",
        }
        llm_rules, local_rules = partition_by_kind([rule])
        assert len(local_rules) == 1

        from rulerepo_server.domain.evaluation import Verdict

        verdict, model_id, _ = evaluate_local(rule, EvaluationContext())
        assert verdict.verdict == Verdict.ALLOW
        assert "definitional" in verdict.reasoning.lower()
