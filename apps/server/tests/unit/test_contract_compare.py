"""Tests for the contract comparator adapter.

Covers clause matching, deviation detection, and comparison results.
"""

from __future__ import annotations

from rulerepo_server.adapters.contract_compare import (
    ComparisonResult,
    ContractComparator,
)
from rulerepo_server.services.extraction.contract.clause_segmenter import Clause


class TestContractComparator:
    """Tests for ContractComparator.compare()."""

    def test_compare_identical_clauses(self) -> None:
        draft = [
            Clause(id="art1", heading="Confidentiality", text="All information is confidential.", level=0),
        ]
        standard = [
            Clause(id="art1", heading="Confidentiality", text="All information is confidential.", level=0),
        ]
        comparator = ContractComparator()
        result = comparator.compare(
            draft,
            standard,
            draft_types={"art1": "confidentiality"},
            standard_types={"art1": "confidentiality"},
        )

        assert isinstance(result, ComparisonResult)
        assert len(result.matched_clauses) == 1
        assert result.matched_clauses[0].similarity == 1.0
        assert result.matched_clauses[0].risk_level == "low"
        assert len(result.unmatched_draft) == 0
        assert len(result.missing_standard) == 0

    def test_compare_similar_clauses(self) -> None:
        draft = [
            Clause(
                id="art1",
                heading="Confidentiality",
                text=(
                    "The Receiving Party shall maintain strict confidentiality"
                    " of all disclosed information for five years."
                ),
                level=0,
            ),
        ]
        standard = [
            Clause(
                id="art1",
                heading="Confidentiality",
                text="The Receiving Party shall maintain confidentiality of all disclosed information for three years.",
                level=0,
            ),
        ]
        comparator = ContractComparator()
        result = comparator.compare(
            draft,
            standard,
            draft_types={"art1": "confidentiality"},
            standard_types={"art1": "confidentiality"},
        )

        assert len(result.matched_clauses) == 1
        # Similar but not identical
        assert 0.5 < result.matched_clauses[0].similarity < 1.0

    def test_compare_unmatched_draft_clause(self) -> None:
        draft = [
            Clause(id="art1", heading="Conf", text="Confidential.", level=0),
            Clause(id="art2", heading="Non-compete", text="Shall not compete for 5 years.", level=0),
        ]
        standard = [
            Clause(id="art1", heading="Conf", text="Confidential.", level=0),
        ]
        comparator = ContractComparator()
        result = comparator.compare(
            draft,
            standard,
            draft_types={"art1": "confidentiality", "art2": "non_compete"},
            standard_types={"art1": "confidentiality"},
        )

        assert len(result.matched_clauses) == 1
        assert len(result.unmatched_draft) == 1
        assert result.unmatched_draft[0].clause_id == "art2"

    def test_compare_missing_standard_clause(self) -> None:
        draft = [
            Clause(id="art1", heading="Conf", text="Confidential.", level=0),
        ]
        standard = [
            Clause(id="art1", heading="Conf", text="Confidential.", level=0),
            Clause(id="art2", heading="Payment", text="Payment within 30 days.", level=0),
        ]
        comparator = ContractComparator()
        result = comparator.compare(
            draft,
            standard,
            draft_types={"art1": "confidentiality"},
            standard_types={"art1": "confidentiality", "art2": "payment"},
        )

        assert len(result.matched_clauses) == 1
        assert len(result.missing_standard) == 1
        assert result.missing_standard[0].clause_id == "art2"

    def test_compare_empty_inputs(self) -> None:
        comparator = ContractComparator()
        result = comparator.compare([], [])

        assert result.overall_similarity == 0.0
        assert len(result.matched_clauses) == 0
        assert result.high_risk_count == 0

    def test_compare_type_matching_priority(self) -> None:
        """Clause type matching takes priority over text similarity."""
        draft = [
            Clause(id="d1", heading="Conf", text="Keep everything secret.", level=0),
            Clause(id="d2", heading="Pay", text="Pay within 30 days of invoice.", level=0),
        ]
        standard = [
            Clause(id="s1", heading="Pay", text="Payment due in 30 days.", level=0),
            Clause(id="s2", heading="Conf", text="Maintain confidentiality.", level=0),
        ]
        comparator = ContractComparator()
        result = comparator.compare(
            draft,
            standard,
            draft_types={"d1": "confidentiality", "d2": "payment"},
            standard_types={"s1": "payment", "s2": "confidentiality"},
        )

        assert len(result.matched_clauses) == 2
        # d1 should match s2 (both confidentiality)
        conf_match = next(m for m in result.matched_clauses if m.draft_clause_id == "d1")
        assert conf_match.standard_clause_id == "s2"
        # d2 should match s1 (both payment)
        pay_match = next(m for m in result.matched_clauses if m.draft_clause_id == "d2")
        assert pay_match.standard_clause_id == "s1"

    def test_risk_level_high_for_very_different(self) -> None:
        draft = [
            Clause(id="art1", heading="Liability", text="Unlimited liability for all damages.", level=0),
        ]
        standard = [
            Clause(
                id="art1",
                heading="Liability",
                text="Liability limited to contract value. Consequential damages excluded.",
                level=0,
            ),
        ]
        comparator = ContractComparator()
        result = comparator.compare(
            draft,
            standard,
            draft_types={"art1": "liability"},
            standard_types={"art1": "liability"},
        )

        assert len(result.matched_clauses) == 1
        # Very different text → high risk
        assert result.matched_clauses[0].similarity < 0.5
        assert result.matched_clauses[0].risk_level == "high"
