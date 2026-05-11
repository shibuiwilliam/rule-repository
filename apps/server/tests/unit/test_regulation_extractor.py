"""Tests for the regulation extractor — Japanese legal hierarchy, references, metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

from rulerepo_server.services.extraction.extractors import SourceFile
from rulerepo_server.services.extraction.extractors.regulation import (
    RegulationExtractor,
    _build_hierarchy_path,
    _extract_document_metadata,
    _resolve_references,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JP_REGULATION = """\
就業規則

平成29年法律第45号

施行日：2024年4月1日

第1条 本規則は、全従業員に適用するものとする。

第2条 従業員は、就業時間中に業務に専念しなければならない。

第3条 従業員は、会社の許可なく副業をしてはならない。

第4条
第1項 残業は、月45時間を超えてはならない。
第2項 前項の規定にかかわらず、繁忙期は月60時間まで認めることができる。
第3号 労使協定に基づくものとする。

第5条 第3条に定める規定は、管理職には適用しないものとする。
"""

EN_REGULATION = """\
Employment Regulations

Effective date: 2025-01-15

Amended on 2025-06-01

Article 1. All employees shall comply with this regulation.

Article 2. Employees must not disclose confidential information.

Article 3.
Section 1. Overtime must not exceed 45 hours per month.
Section 2. In addition to the preceding section, managers may authorize extensions.

Article 4. As defined in Article 2, confidential information shall be protected.
"""


# ---------------------------------------------------------------------------
# Hierarchy Path
# ---------------------------------------------------------------------------


class TestBuildHierarchyPath:
    def test_article_only(self) -> None:
        path = _build_hierarchy_path("従業員は業務に専念しなければならない", "第2条", 2, 0)
        assert path == "第2条"

    def test_article_and_paragraph(self) -> None:
        path = _build_hierarchy_path("第1項 残業は月45時間を超えてはならない", "第4条", 4, 0)
        assert path == "第4条.第1項"

    def test_article_paragraph_and_item(self) -> None:
        path = _build_hierarchy_path("第3号 労使協定に基づくものとする", "第4条", 4, 1)
        assert path == "第4条.第3号"

    def test_english_article_section(self) -> None:
        path = _build_hierarchy_path(
            "Section 1. Overtime must not exceed 45 hours.",
            "Article 3",
            3,
            0,
        )
        assert path == "Article 3.Section 1"

    def test_empty_when_no_context(self) -> None:
        path = _build_hierarchy_path("Some plain text", "", 0, 0)
        assert path == ""


# ---------------------------------------------------------------------------
# Reference Resolution
# ---------------------------------------------------------------------------


class TestResolveReferences:
    def test_preceding_article(self) -> None:
        refs = _resolve_references("前条の規定に従い処理するものとする", 3, 0)
        assert len(refs) == 1
        assert refs[0].reference_type == "preceding"
        assert refs[0].target_path == "第2条"
        assert refs[0].match_text == "前条"

    def test_preceding_paragraph(self) -> None:
        refs = _resolve_references("前項の規定にかかわらず認めることができる", 4, 2)
        assert len(refs) == 1
        assert refs[0].reference_type == "preceding"
        assert refs[0].target_path == "第4条.第1項"

    def test_forward_article(self) -> None:
        refs = _resolve_references("詳細は次条に定める", 5, 0)
        assert len(refs) == 1
        assert refs[0].reference_type == "forward"
        assert refs[0].target_path == "第6条"

    def test_cross_reference(self) -> None:
        refs = _resolve_references("第3条第2項の規定により処理する", 5, 0)
        assert len(refs) == 1
        assert refs[0].reference_type == "internal"
        assert refs[0].target_path == "第3条.第2項"

    def test_cross_reference_with_item(self) -> None:
        refs = _resolve_references("第4条第1項第3号に基づく", 6, 0)
        assert len(refs) == 1
        assert refs[0].target_path == "第4条.第1項.第3号"

    def test_self_reference_skipped(self) -> None:
        """A reference to the current article number without paragraph is skipped."""
        refs = _resolve_references("第5条 この規定は...", 5, 0)
        assert len(refs) == 0

    def test_english_preceding(self) -> None:
        refs = _resolve_references("In addition to the preceding section, managers may...", 3, 1)
        assert len(refs) == 1
        assert refs[0].reference_type == "preceding"
        assert refs[0].target_path == "Article 2"

    def test_multiple_references(self) -> None:
        text = "前条および第2条第1項の規定にかかわらず認めることができる"
        refs = _resolve_references(text, 4, 1)
        types = {r.reference_type for r in refs}
        assert "preceding" in types
        assert "internal" in types


# ---------------------------------------------------------------------------
# Document-Level Metadata
# ---------------------------------------------------------------------------


class TestExtractDocumentMetadata:
    def test_statute_number(self) -> None:
        meta = _extract_document_metadata("平成29年法律第45号に基づく就業規則")
        assert "平成29年法律第45号" in meta.statute_numbers

    def test_multiple_statute_numbers(self) -> None:
        text = "平成29年法律第45号および令和5年政令第12号に基づく"
        meta = _extract_document_metadata(text)
        assert len(meta.statute_numbers) == 2

    def test_effective_date_jp(self) -> None:
        meta = _extract_document_metadata("施行日：2024年4月1日")
        assert "2024年4月1日" in meta.effective_dates

    def test_effective_date_en(self) -> None:
        meta = _extract_document_metadata("Effective date: 2025-01-15")
        assert "2025-01-15" in meta.effective_dates

    def test_amendment_date_jp(self) -> None:
        meta = _extract_document_metadata("一部改正：令和6年10月1日")
        assert "令和6年10月1日" in meta.amendment_dates

    def test_amendment_date_en(self) -> None:
        meta = _extract_document_metadata("Amended on 2025-06-01")
        assert "2025-06-01" in meta.amendment_dates

    def test_no_metadata(self) -> None:
        meta = _extract_document_metadata("This is plain text.")
        assert meta.statute_numbers == []
        assert meta.effective_dates == []
        assert meta.amendment_dates == []


# ---------------------------------------------------------------------------
# Full Extractor Integration
# ---------------------------------------------------------------------------


class TestRegulationExtractorFullDoc:
    @pytest.mark.asyncio
    async def test_japanese_regulation(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_regulation.txt"),
            source_type="regulation_doc",
            content=JP_REGULATION,
            metadata={"scope": ["hr/attendance"], "department": "hr"},
        )
        extractor = RegulationExtractor()
        candidates = await extractor.extract(source)

        # Should find normative statements
        assert len(candidates) >= 3

        # Check hierarchy in source_refs
        paths = [c.source_refs.get("path", "") for c in candidates]
        assert any("第2条" in p for p in paths)
        assert any("第3条" in p for p in paths)

        # Check statute numbers are attached
        assert any("平成29年法律第45号" in (c.source_refs.get("statute_numbers") or []) for c in candidates)

        # Check effective dates
        assert any("2024年4月1日" in (c.source_refs.get("effective_dates") or []) for c in candidates)

    @pytest.mark.asyncio
    async def test_english_regulation(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_regulation_en.txt"),
            source_type="regulation_doc",
            content=EN_REGULATION,
            metadata={},
        )
        extractor = RegulationExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) >= 3

        # Check effective date extracted
        assert any("2025-01-15" in (c.source_refs.get("effective_dates") or []) for c in candidates)

        # Check amendment date
        assert any("2025-06-01" in (c.source_refs.get("amendment_dates") or []) for c in candidates)

    @pytest.mark.asyncio
    async def test_references_attached(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_ref.txt"),
            source_type="regulation_doc",
            content=JP_REGULATION,
            metadata={},
        )
        extractor = RegulationExtractor()
        candidates = await extractor.extract(source)

        # Find the candidate with 前項 reference
        ref_candidates = [c for c in candidates if c.source_refs.get("references")]
        assert len(ref_candidates) >= 1

    @pytest.mark.asyncio
    async def test_modality_detection(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_mod.txt"),
            source_type="regulation_doc",
            content=JP_REGULATION,
            metadata={},
        )
        extractor = RegulationExtractor()
        candidates = await extractor.extract(source)

        modalities = {c.modality for c in candidates}
        # しなければならない → MUST, してはならない → MUST_NOT, できる → MAY
        assert "MUST" in modalities
        assert "MUST_NOT" in modalities
