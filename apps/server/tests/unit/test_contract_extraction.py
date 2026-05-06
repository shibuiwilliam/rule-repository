"""Tests for the contract extraction sub-pipeline.

Covers clause segmentation, classification, and reference resolution.
"""

from __future__ import annotations

from rulerepo_server.services.extraction.contract.clause_classifier import classify_all, classify_clause
from rulerepo_server.services.extraction.contract.clause_segmenter import Clause, segment_contract
from rulerepo_server.services.extraction.contract.reference_resolver import resolve_references

# ---------------------------------------------------------------------------
# Clause Segmenter
# ---------------------------------------------------------------------------


class TestClauseSegmenter:
    def test_segment_western_articles(self) -> None:
        text = (
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "Article 1. Definitions\n"
            "Confidential Information means...\n\n"
            "Article 2. Obligations\n"
            "The Receiving Party shall...\n\n"
            "Article 3. Term\n"
            "This Agreement shall remain in effect for two years.\n"
        )
        doc = segment_contract(text, title="NDA")
        assert doc.title == "NDA"
        assert doc.clause_count == 3
        assert doc.clauses[0].id == "art1"
        assert doc.clauses[1].id == "art2"
        assert doc.clauses[2].id == "art3"
        assert "Confidential Information" in doc.clauses[0].text

    def test_segment_japanese_articles(self) -> None:
        text = "秘密保持契約書\n\n第1条 定義\n秘密情報とは...\n\n第2条 義務\n受領者は...\n"
        doc = segment_contract(text)
        assert doc.clause_count == 2
        assert doc.clauses[0].id == "art1"
        assert doc.clauses[1].id == "art2"

    def test_segment_preamble(self) -> None:
        text = "This is the preamble.\nParties agree as follows:\n\nArticle 1. Scope\nThis agreement covers...\n"
        doc = segment_contract(text)
        assert "preamble" in doc.preamble.lower() or "parties" in doc.preamble.lower()
        assert doc.clause_count == 1

    def test_segment_empty_text(self) -> None:
        doc = segment_contract("")
        assert doc.clause_count == 0

    def test_segment_no_articles(self) -> None:
        doc = segment_contract("Just some plain text without any structure.")
        assert doc.clause_count == 0
        assert doc.preamble != ""


# ---------------------------------------------------------------------------
# Clause Classifier
# ---------------------------------------------------------------------------


class TestClauseClassifier:
    def test_classify_confidentiality(self) -> None:
        clause = Clause(id="art1", heading="Confidentiality", text="All confidential information...", level=0)
        result = classify_clause(clause)
        assert result.clause_type == "confidentiality"
        assert result.confidence > 0.4

    def test_classify_payment(self) -> None:
        clause = Clause(
            id="art5",
            heading="Payment Terms",
            text="Payment shall be due within 30 days of invoice.",
            level=0,
        )
        result = classify_clause(clause)
        assert result.clause_type == "payment"

    def test_classify_governing_law(self) -> None:
        clause = Clause(
            id="art10",
            heading="Governing Law",
            text="This agreement shall be governed by the laws of Japan.",
            level=0,
        )
        result = classify_clause(clause)
        assert result.clause_type == "governing_law"

    def test_classify_general_fallback(self) -> None:
        clause = Clause(id="art99", heading="Miscellaneous", text="Other provisions apply.", level=0)
        result = classify_clause(clause)
        assert result.clause_type == "general"
        assert result.confidence < 0.5

    def test_classify_all(self) -> None:
        clauses = [
            Clause(id="art1", heading="Confidentiality", text="秘密情報...", level=0),
            Clause(id="art2", heading="Payment", text="支払い条件...", level=0),
        ]
        results = classify_all(clauses)
        assert len(results) == 2
        assert results[0].clause_type == "confidentiality"
        assert results[1].clause_type == "payment"


# ---------------------------------------------------------------------------
# Reference Resolver
# ---------------------------------------------------------------------------


class TestReferenceResolver:
    def test_resolve_western_reference(self) -> None:
        text1 = "Article 1. Definitions\nConfidential Information means..."
        text2 = "Article 2. Obligations\nAs defined in Article 1, the Receiving Party shall..."
        doc = segment_contract(f"{text1}\n\n{text2}")
        ref_map = resolve_references(doc)
        assert len(ref_map.references) >= 1
        internal_refs = [r for r in ref_map.references if r.reference_type == "internal"]
        assert any(r.target_clause_id == "art1" for r in internal_refs)

    def test_resolve_japanese_reference(self) -> None:
        text = (
            "第1条 定義\n秘密情報とは以下を指す。\n\n"
            "第2条 義務\n受領者は、第1条に定める秘密情報を厳に管理しなければならない。"
        )
        doc = segment_contract(text)
        ref_map = resolve_references(doc)
        internal_refs = [r for r in ref_map.references if r.reference_type == "internal"]
        assert any(r.target_clause_id == "art1" for r in internal_refs)

    def test_resolve_preceding_reference(self) -> None:
        text = "Article 1. Scope\nThis covers...\n\nArticle 2. Details\nIn addition to the preceding section, ..."
        doc = segment_contract(text)
        ref_map = resolve_references(doc)
        preceding_refs = [r for r in ref_map.references if r.reference_type == "preceding"]
        assert len(preceding_refs) >= 1
        assert preceding_refs[0].target_clause_id == "art1"

    def test_resolve_appendix_reference(self) -> None:
        text = "Article 1. Scope\nSee Appendix A for details."
        doc = segment_contract(text)
        ref_map = resolve_references(doc)
        appendix_refs = [r for r in ref_map.references if r.reference_type == "appendix"]
        assert len(appendix_refs) >= 1

    def test_unresolved_count(self) -> None:
        text = "Article 1. Scope\nSee Article 99 for details."
        doc = segment_contract(text)
        ref_map = resolve_references(doc)
        # Article 99 doesn't exist, so it should be unresolved
        assert ref_map.unresolved_count >= 1
