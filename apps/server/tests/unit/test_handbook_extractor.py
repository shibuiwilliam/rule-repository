"""Tests for the handbook extractor — HR-specific scope and labor agreement references."""

from __future__ import annotations

from pathlib import Path

import pytest

from rulerepo_server.services.extraction.extractors import SourceFile
from rulerepo_server.services.extraction.extractors.handbook import (
    HandbookExtractor,
    _detect_employment_types,
    _detect_labor_agreement_refs,
    _detect_position_levels,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JP_HANDBOOK = """\
# 就業規則

## 第1章 適用範囲

正社員および契約社員は、本規則を遵守しなければならない。パートタイムについては別途定める。

## 第2章 勤務時間

従業員は、所定労働時間を遵守しなければならない。

管理職は、労使協定に基づき裁量労働制を適用するものとする。

## 第3章 禁止事項

従業員は、就業時間中に私的な活動をしてはならない。

## 第4章 懲戒

36協定に違反した場合、懲戒処分の対象としなければならない。
"""

EN_HANDBOOK = """\
# Employee Handbook

## Chapter 1. Scope

This handbook applies to all full-time and part-time employees.
Contract employees are subject to separate terms.

## Chapter 2. Work Hours

Employees must adhere to scheduled work hours.

Managers are expected to comply with the collective bargaining agreement.

## Chapter 3. Prohibited Conduct

Employees shall not engage in personal activities during work hours.
"""


# ---------------------------------------------------------------------------
# Employment Type Detection
# ---------------------------------------------------------------------------


class TestDetectEmploymentTypes:
    def test_japanese_types(self) -> None:
        types = _detect_employment_types("正社員および契約社員に適用する")
        assert "正社員" in types
        assert "契約社員" in types

    def test_part_time(self) -> None:
        types = _detect_employment_types("パートタイムについては別途定める")
        assert any("パート" in t for t in types)

    def test_english_types(self) -> None:
        types = _detect_employment_types("full-time and part-time employees")
        assert "full-time" in types
        assert "part-time" in types

    def test_no_types(self) -> None:
        types = _detect_employment_types("This is generic text.")
        assert len(types) == 0


# ---------------------------------------------------------------------------
# Position Level Detection
# ---------------------------------------------------------------------------


class TestDetectPositionLevels:
    def test_japanese_levels(self) -> None:
        levels = _detect_position_levels("管理職には適用しない")
        assert "管理職" in levels

    def test_english_levels(self) -> None:
        levels = _detect_position_levels("Managers and directors must comply")
        assert "manager" in levels
        assert "director" in levels

    def test_no_levels(self) -> None:
        levels = _detect_position_levels("All staff must comply.")
        assert len(levels) == 0


# ---------------------------------------------------------------------------
# Labor Agreement Reference Detection
# ---------------------------------------------------------------------------


class TestDetectLaborAgreementRefs:
    def test_japanese_refs(self) -> None:
        refs = _detect_labor_agreement_refs("労使協定に基づき裁量労働制を適用する")
        assert "労使協定" in refs

    def test_36_agreement(self) -> None:
        refs = _detect_labor_agreement_refs("36協定に違反した場合")
        assert "36協定" in refs

    def test_employment_regulations(self) -> None:
        refs = _detect_labor_agreement_refs("就業規則に定める")
        assert "就業規則" in refs

    def test_english_refs(self) -> None:
        refs = _detect_labor_agreement_refs("per the collective bargaining agreement")
        assert "collective bargaining agreement" in refs

    def test_no_refs(self) -> None:
        refs = _detect_labor_agreement_refs("Normal business text.")
        assert len(refs) == 0


# ---------------------------------------------------------------------------
# Full Extractor Integration
# ---------------------------------------------------------------------------


class TestHandbookExtractorFull:
    @pytest.mark.asyncio
    async def test_japanese_handbook(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_handbook.txt"),
            source_type="handbook",
            content=JP_HANDBOOK,
            metadata={"department": "hr"},
        )
        extractor = HandbookExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) >= 3

        # Check employment types are detected
        emp_type_candidates = [c for c in candidates if c.source_refs.get("employment_types")]
        assert len(emp_type_candidates) >= 1

        # Check labor agreement references
        labor_ref_candidates = [c for c in candidates if c.source_refs.get("labor_agreement_refs")]
        assert len(labor_ref_candidates) >= 1

    @pytest.mark.asyncio
    async def test_english_handbook(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_handbook_en.txt"),
            source_type="handbook",
            content=EN_HANDBOOK,
            metadata={"department": "hr"},
        )
        extractor = HandbookExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) >= 2

    @pytest.mark.asyncio
    async def test_position_levels_from_section(self) -> None:
        """Position levels detected in section headings are propagated to candidates."""
        content = "## 管理職向け規定\n\n管理職は、部下の勤怠を管理しなければならない。"
        source = SourceFile(
            path=Path("/tmp/test_pos.txt"),
            source_type="handbook",
            content=content,
            metadata={},
        )
        extractor = HandbookExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 1
        assert "管理職" in candidates[0].source_refs.get("position_levels", [])

    @pytest.mark.asyncio
    async def test_tags_include_scoped_marker(self) -> None:
        content = "正社員は、所定労働時間を遵守しなければならない。"
        source = SourceFile(
            path=Path("/tmp/test_tags.txt"),
            source_type="handbook",
            content=content,
            metadata={},
        )
        extractor = HandbookExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 1
        assert "scoped_by_employment_type" in candidates[0].tags

    @pytest.mark.asyncio
    async def test_labor_ref_tag(self) -> None:
        content = "36協定に基づき、残業は月45時間を超えてはならない。"
        source = SourceFile(
            path=Path("/tmp/test_labor_tag.txt"),
            source_type="handbook",
            content=content,
            metadata={},
        )
        extractor = HandbookExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 1
        assert "labor_agreement_ref" in candidates[0].tags
