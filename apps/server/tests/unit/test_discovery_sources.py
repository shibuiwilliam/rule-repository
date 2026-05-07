"""Tests for Phase 7c discovery source extractors."""

from __future__ import annotations

import pytest

from rulerepo_server.services.discovery.sources.policy_handbook import (
    extract_from_handbook,
)
from rulerepo_server.services.discovery.sources.regulation_pdf import (
    extract_articles_from_text,
)


class TestRegulationTextExtraction:
    def test_extract_japanese_articles(self) -> None:
        text = (
            "第1条 この法律は、労働条件の最低基準を定めるものとする。\n"
            "\n"
            "第2条 労働者及び使用者は、労働条件について対等の立場において決定しなければならない。\n"
            "\n"
            "第3条 使用者は、労働者の国籍を理由として差別的取扱をしてはならない。\n"
        )
        candidates = extract_articles_from_text(text, statute_name="Labor Standards Act")
        assert len(candidates) == 3
        assert candidates[0].article_ref.article == "1"
        assert candidates[0].article_ref.statute_name == "Labor Standards Act"
        assert candidates[2].modality == "MUST_NOT"  # してはならない

    def test_extract_western_articles(self) -> None:
        text = (
            "Article 1. Purpose\n"
            "This regulation shall establish minimum standards.\n"
            "\n"
            "Article 2. Scope\n"
            "All employees must comply with these standards.\n"
        )
        candidates = extract_articles_from_text(text, statute_name="Test Regulation")
        assert len(candidates) == 2
        assert candidates[0].article_ref.article == "1"

    def test_detect_modality_must_not(self) -> None:
        text = "第5条 使用者は労働者に対して強制労働を行わせてはならないものとする。何人もこれに違反してはならない。"
        candidates = extract_articles_from_text(text, statute_name="test")
        assert len(candidates) == 1
        assert candidates[0].modality == "MUST_NOT"

    def test_empty_text(self) -> None:
        candidates = extract_articles_from_text("")
        assert candidates == []

    def test_scope_prefix(self) -> None:
        text = (
            "Article 1. All workers must be granted sufficient rest periods"
            " between shifts according to the applicable regulations.\n"
        )
        candidates = extract_articles_from_text(text, scope_prefix="hr/attendance/jp")
        assert len(candidates) == 1
        assert "hr/attendance/jp" in candidates[0].scope


class TestPolicyHandbookExtraction:
    @pytest.mark.asyncio
    async def test_extract_normative_sentences(self) -> None:
        text = (
            "# Expense Policy\n"
            "\n"
            "## Submission\n"
            "Employees must submit expense reports within 30 days.\n"
            "This is just informational text.\n"
            "All claims shall be accompanied by receipts.\n"
        )
        candidates = await extract_from_handbook(text, document_title="Expense Policy")
        assert len(candidates) == 2
        assert candidates[0].modality == "MUST"
        assert candidates[0].section == "Submission"

    @pytest.mark.asyncio
    async def test_extract_prohibition(self) -> None:
        text = "# Code of Conduct\nEmployees must not share confidential information.\n"
        candidates = await extract_from_handbook(text, document_title="CoC")
        assert len(candidates) == 1
        assert candidates[0].modality == "MUST_NOT"

    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        candidates = await extract_from_handbook("")
        assert candidates == []

    @pytest.mark.asyncio
    async def test_scope_prefix(self) -> None:
        text = "Staff must complete training annually.\n"
        candidates = await extract_from_handbook(text, scope_prefix="hr/training")
        assert len(candidates) == 1
        assert "hr/training" in candidates[0].scope

    @pytest.mark.asyncio
    async def test_japanese_normative(self) -> None:
        text = "# 就業規則\n全ての従業員は出勤時に所定の方法で打刻しなければならない。退勤時も同様とする。\n"
        candidates = await extract_from_handbook(text, document_title="Work Regulations")
        assert len(candidates) >= 1
