"""Tests for multilingual rule support."""

import pytest

from rulerepo_server.domain.translation import TranslationLink
from rulerepo_server.workers.verify_translations import (
    TranslationVerificationResult,
    verify_all_translations,
    verify_translation_pair,
)


class TestTranslationLink:
    def test_create_link(self):
        link = TranslationLink(
            sibling_rule_id="rule_002",
            language="ja",
            equivalence_score=0.95,
        )
        assert link.sibling_rule_id == "rule_002"
        assert link.language == "ja"
        assert link.equivalence_score == 0.95

    def test_default_values(self):
        link = TranslationLink(sibling_rule_id="r1", language="en")
        assert link.equivalence_verified_at is None
        assert link.equivalence_score == 0.0


class TestVerifyTranslationPair:
    @pytest.mark.asyncio
    async def test_verify_non_empty_pair(self):
        result = await verify_translation_pair(
            rule_statement="Employees must take 5 days of paid leave per year.",
            rule_language="en",
            sibling_statement="従業員は年間5日の有給休暇を取得しなければならない。",
            sibling_language="ja",
            rule_id="rule_001",
            sibling_rule_id="rule_001_ja",
        )
        assert isinstance(result, TranslationVerificationResult)
        assert result.equivalence_score > 0
        assert result.verified_at is not None

    @pytest.mark.asyncio
    async def test_verify_empty_statement(self):
        result = await verify_translation_pair(
            rule_statement="",
            rule_language="en",
            sibling_statement="テスト",
            sibling_language="ja",
        )
        assert result.equivalence_score == 0.0
        assert result.below_threshold is True

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        result = await verify_translation_pair(
            rule_statement="Test rule",
            rule_language="en",
            sibling_statement="テストルール",
            sibling_language="ja",
            threshold=0.95,
        )
        # Stub returns 0.9, so it should be below 0.95 threshold
        assert result.below_threshold is True


class TestVerifyAllTranslations:
    @pytest.mark.asyncio
    async def test_verify_multiple_pairs(self):
        pairs = [
            {
                "rule_id": "r1",
                "sibling_rule_id": "r1_ja",
                "rule_statement": "Rule one",
                "rule_language": "en",
                "sibling_statement": "ルール1",
                "sibling_language": "ja",
            },
            {
                "rule_id": "r2",
                "sibling_rule_id": "r2_ja",
                "rule_statement": "Rule two",
                "rule_language": "en",
                "sibling_statement": "ルール2",
                "sibling_language": "ja",
            },
        ]
        results = await verify_all_translations(translation_pairs=pairs)
        assert len(results) == 2
        assert all(isinstance(r, TranslationVerificationResult) for r in results)

    @pytest.mark.asyncio
    async def test_empty_pairs(self):
        results = await verify_all_translations(translation_pairs=[])
        assert len(results) == 0
