"""Tests for the domain-adaptive extraction pipeline components.

Tests structural parsers, normative detection, and coref resolution.
"""

from __future__ import annotations

from rulerepo_server.services.extraction.coref_resolution import resolve_references
from rulerepo_server.services.extraction.normative_detection import (
    detect_normative_sentences,
)
from rulerepo_server.services.extraction.structural.markdown_structure import (
    extract_markdown_structure,
)
from rulerepo_server.services.extraction.structural.pdf_structure import (
    DocumentSection,
)
from rulerepo_server.services.extraction.structural.text_structure import (
    extract_text_structure,
)

# ── Structural parsers: markdown ──────────────────────────────────────


class TestMarkdownStructure:
    def test_markdown_structure_extraction(self) -> None:
        md = (
            "# Introduction\n"
            "Some intro text.\n"
            "\n"
            "## Background\n"
            "Background details here.\n"
            "\n"
            "## Requirements\n"
            "All users must comply.\n"
        )
        result = extract_markdown_structure(md)
        assert result.document_type == "markdown"
        assert len(result.sections) == 3
        assert result.sections[0].title == "Introduction"
        assert result.sections[0].level == 1
        assert "intro text" in result.sections[0].content
        assert result.sections[1].title == "Background"
        assert result.sections[1].level == 2
        assert result.sections[2].title == "Requirements"

    def test_markdown_empty_document(self) -> None:
        result = extract_markdown_structure("")
        assert result.document_type == "markdown"
        assert len(result.sections) == 0

    def test_markdown_no_headings(self) -> None:
        result = extract_markdown_structure("Just some plain text without any headings.")
        assert len(result.sections) == 1
        assert result.sections[0].title == "(untitled)"
        assert result.sections[0].level == 0
        assert "plain text" in result.sections[0].content


# ── Structural parsers: text ──────────────────────────────────────────


class TestTextStructure:
    def test_text_structure_extraction(self) -> None:
        text = (
            "First paragraph of the document.\n\nSecond paragraph with more content.\n\nThird paragraph wrapping up.\n"
        )
        result = extract_text_structure(text)
        assert result.document_type == "text"
        assert len(result.sections) == 3
        assert result.sections[0].section_id == "para_1"
        assert "First paragraph" in result.sections[0].content
        assert result.sections[2].section_id == "para_3"


# ── Normative detection ──────────────────────────────────────────────


class TestNormativeDetection:
    def test_detect_must_sentences(self) -> None:
        text = "All employees must wear safety equipment. The sky is blue."
        results = detect_normative_sentences(text, section_id="sec_1")
        assert len(results) == 1
        assert results[0].modality_hint == "MUST"
        assert results[0].confidence == 0.8
        assert "must wear" in results[0].text

    def test_detect_should_sentences(self) -> None:
        text = "Developers should write tests for all new features."
        results = detect_normative_sentences(text, section_id="sec_1")
        assert len(results) == 1
        assert results[0].modality_hint == "SHOULD"
        assert results[0].confidence == 0.6

    def test_detect_japanese_normative(self) -> None:
        text = "従業員は安全装備を着用しなければならない"
        results = detect_normative_sentences(text, section_id="sec_1", language="ja")
        assert len(results) == 1
        assert results[0].modality_hint == "MUST"
        assert results[0].language == "ja"

    def test_no_normative_sentences(self) -> None:
        text = "The company was founded in 2020. It has offices in Tokyo and London."
        results = detect_normative_sentences(text, section_id="sec_1")
        assert len(results) == 0


# ── Coref resolution ─────────────────────────────────────────────────


class TestCorefResolution:
    def test_resolve_section_reference(self) -> None:
        sections = [
            DocumentSection(section_id="sec_1", title="Section 1", level=1, content=""),
            DocumentSection(section_id="sec_2", title="Section 2.1 Requirements", level=2, content=""),
        ]
        refs = resolve_references("See Section 2.1 for details.", sections)
        assert len(refs) == 1
        assert refs[0].resolved is True
        assert refs[0].target_section_id == "sec_2"
        assert refs[0].reference_text == "Section 2.1"

    def test_resolve_japanese_article(self) -> None:
        sections = [
            DocumentSection(section_id="art_1", title="第1条 総則", level=1, content=""),
            DocumentSection(section_id="art_3", title="第3条 義務", level=1, content=""),
        ]
        refs = resolve_references("第3条に基づき対応すること。", sections)
        assert len(refs) == 1
        assert refs[0].resolved is True
        assert refs[0].target_section_id == "art_3"
        assert refs[0].reference_text == "第3条"
