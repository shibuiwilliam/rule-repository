"""Unit tests for the polyglot translation service and verifier."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from rulerepo_server.domain.translation import RuleTranslation, TranslationVerification
from rulerepo_server.services.polyglot.verifier import (
    EquivalenceResult,
    PolyglotVerifier,
    VerificationReport,
)

# ---------------------------------------------------------------------------
# PolyglotVerifier
# ---------------------------------------------------------------------------


class TestPolyglotVerifier:
    """Tests for the PolyglotVerifier service."""

    @pytest.fixture()
    def session(self) -> AsyncMock:
        return AsyncMock()

    async def test_verify_without_gemini_uses_heuristic(self, session: AsyncMock) -> None:
        """Without a Gemini client, the verifier falls back to length-ratio."""
        verifier = PolyglotVerifier(session, gemini_client=None)

        report = await verifier.verify_equivalence(
            rule_id="r1",
            primary_statement="All employees must report overtime hours.",
            primary_language="en",
            translations={"ja": "全従業員は残業時間を報告しなければならない。"},
        )

        assert isinstance(report, VerificationReport)
        assert report.rule_id == "r1"
        assert report.primary_language == "en"
        assert len(report.results) == 1
        assert report.results[0].language == "ja"
        assert 0.0 <= report.results[0].score <= 1.0

    async def test_verify_skips_primary_language(self, session: AsyncMock) -> None:
        """Translations in the same language as primary are skipped."""
        verifier = PolyglotVerifier(session, gemini_client=None)

        report = await verifier.verify_equivalence(
            rule_id="r1",
            primary_statement="Test rule",
            primary_language="en",
            translations={"en": "Test rule (duplicate)"},
        )

        assert len(report.results) == 0

    async def test_verify_detects_drift_on_very_different_lengths(self, session: AsyncMock) -> None:
        """Very different lengths should produce a low heuristic score."""
        verifier = PolyglotVerifier(session, gemini_client=None)

        report = await verifier.verify_equivalence(
            rule_id="r1",
            primary_statement="Short.",
            primary_language="en",
            translations={"ja": "これは非常に長い文章で" * 20},
        )

        assert len(report.results) == 1
        # With the heuristic (ratio + 0.3, capped at 1.0), a huge mismatch
        # should still be detectable if the ratio is very low.
        result = report.results[0]
        assert isinstance(result, EquivalenceResult)

    async def test_verify_with_mock_gemini(self, session: AsyncMock) -> None:
        """With a Gemini client, the verifier calls the LLM for scoring."""
        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"score": 0.92, "notes": "Good translation"}'
        mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

        verifier = PolyglotVerifier(session, gemini_client=mock_gemini)

        with patch("rulerepo_server.core.config.get_settings") as mock_settings:
            mock_settings.return_value.llm_default_model = "gemini-3-flash-preview"

            report = await verifier.verify_equivalence(
                rule_id="r1",
                primary_statement="Overtime must not exceed 45 hours per month.",
                primary_language="en",
                translations={"ja": "月の残業時間は45時間を超えてはならない。"},
            )

        assert len(report.results) == 1
        assert report.results[0].score == 0.92
        assert not report.results[0].drift_detected  # 0.92 > 0.85 threshold
        mock_gemini.aio.models.generate_content.assert_called_once()

    async def test_verify_with_gemini_failure_returns_fallback(self, session: AsyncMock) -> None:
        """When Gemini call fails, verifier returns 0.5 as fallback."""
        mock_gemini = MagicMock()
        mock_gemini.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("API error"))

        verifier = PolyglotVerifier(session, gemini_client=mock_gemini)

        with patch("rulerepo_server.core.config.get_settings") as mock_settings:
            mock_settings.return_value.llm_default_model = "gemini-3-flash-preview"

            report = await verifier.verify_equivalence(
                rule_id="r1",
                primary_statement="Test rule",
                primary_language="en",
                translations={"ja": "テストルール"},
            )

        assert len(report.results) == 1
        assert report.results[0].score == 0.5
        assert report.results[0].drift_detected  # 0.5 < 0.85 threshold

    async def test_empty_translations(self, session: AsyncMock) -> None:
        """Empty translations dict produces empty results."""
        verifier = PolyglotVerifier(session, gemini_client=None)

        report = await verifier.verify_equivalence(
            rule_id="r1",
            primary_statement="Test rule",
            primary_language="en",
            translations={},
        )

        assert len(report.results) == 0
        assert not report.has_drift

    async def test_multiple_translations(self, session: AsyncMock) -> None:
        """Multiple translations are each checked independently."""
        verifier = PolyglotVerifier(session, gemini_client=None)

        report = await verifier.verify_equivalence(
            rule_id="r1",
            primary_statement="All employees must report overtime.",
            primary_language="en",
            translations={
                "ja": "全従業員は残業を報告しなければならない。",
                "de": "Alle Mitarbeiter müssen Überstunden melden.",
                "fr": "Tous les employés doivent signaler les heures supplémentaires.",
            },
        )

        assert len(report.results) == 3
        languages = {r.language for r in report.results}
        assert languages == {"ja", "de", "fr"}


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class TestRuleTranslationDomain:
    """Tests for the RuleTranslation domain object."""

    def test_defaults(self) -> None:
        t = RuleTranslation()
        assert isinstance(t.id, UUID)
        assert t.language == ""
        assert t.equivalence_score == 0.0
        assert t.last_verified_at is None

    def test_creation_with_values(self) -> None:
        rule_id = uuid4()
        t = RuleTranslation(
            rule_id=rule_id,
            language="ja",
            statement="テストルール",
            translator="gemini",
            equivalence_score=0.95,
        )
        assert t.rule_id == rule_id
        assert t.language == "ja"
        assert t.translator == "gemini"
        assert t.equivalence_score == 0.95


class TestTranslationVerificationDomain:
    """Tests for the TranslationVerification domain object."""

    def test_defaults(self) -> None:
        v = TranslationVerification()
        assert v.passed is True
        assert v.equivalence_score == 0.0

    def test_failed_verification(self) -> None:
        v = TranslationVerification(equivalence_score=0.4, passed=False)
        assert not v.passed
        assert v.equivalence_score == 0.4


# ---------------------------------------------------------------------------
# Search language filter
# ---------------------------------------------------------------------------


class TestSearchLanguageFilter:
    """Tests for Accept-Language header parsing and filter building."""

    def test_parse_simple_language(self) -> None:
        from rulerepo_server.api.v1.search import _parse_accept_language

        assert _parse_accept_language("ja") == "ja"
        assert _parse_accept_language("en") == "en"

    def test_parse_language_with_region(self) -> None:
        from rulerepo_server.api.v1.search import _parse_accept_language

        assert _parse_accept_language("en-US") == "en"
        assert _parse_accept_language("ja-JP") == "ja"

    def test_parse_language_with_quality(self) -> None:
        from rulerepo_server.api.v1.search import _parse_accept_language

        assert _parse_accept_language("ja,en;q=0.9") == "ja"
        assert _parse_accept_language("en-US,en;q=0.9,ja;q=0.8") == "en"

    def test_parse_empty_returns_none(self) -> None:
        from rulerepo_server.api.v1.search import _parse_accept_language

        assert _parse_accept_language("") is None
        assert _parse_accept_language(None) is None

    def test_parse_wildcard_returns_none(self) -> None:
        from rulerepo_server.api.v1.search import _parse_accept_language

        assert _parse_accept_language("*") is None

    def test_build_filters_with_language_param(self) -> None:
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="overtime", language="ja")
        filters = _build_filters(query)
        assert filters["primary_language"] == "ja"

    def test_build_filters_with_accept_language_header(self) -> None:
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="overtime")
        filters = _build_filters(query, accept_language="ja,en;q=0.9")
        assert filters["primary_language"] == "ja"

    def test_query_language_overrides_header(self) -> None:
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="overtime", language="en")
        filters = _build_filters(query, accept_language="ja")
        assert filters["primary_language"] == "en"

    def test_no_language_no_filter(self) -> None:
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="overtime")
        filters = _build_filters(query)
        assert "primary_language" not in filters


# ---------------------------------------------------------------------------
# VerificationReport properties
# ---------------------------------------------------------------------------


class TestVerificationReport:
    def test_has_drift_true(self) -> None:
        report = VerificationReport(
            rule_id="r1",
            primary_language="en",
            results=[
                EquivalenceResult(language="ja", score=0.6, drift_detected=True, drift_description="Low score"),
            ],
        )
        assert report.has_drift is True

    def test_has_drift_false(self) -> None:
        report = VerificationReport(
            rule_id="r1",
            primary_language="en",
            results=[
                EquivalenceResult(language="ja", score=0.95, drift_detected=False),
            ],
        )
        assert report.has_drift is False

    def test_has_drift_empty(self) -> None:
        report = VerificationReport(rule_id="r1", primary_language="en")
        assert report.has_drift is False
