"""Acceptance test: Multilingual rule management.

Scenario (IMPROVEMENT.md Proposal 8):
    1. Create a rule in Japanese
    2. Link an English translation
    3. Verify equivalence check works (mock LLM)
    4. Evaluate a subject against the Japanese version
    5. Verify search filters by Accept-Language

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rulerepo_server.domain.evaluation import Verdict
from rulerepo_server.domain.rule import Rule, RuleKind
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.domain.translation import RuleTranslation, TranslationVerification
from rulerepo_server.services.evaluation.context_assembler import assemble_context_from_subject
from rulerepo_server.services.evaluation.kind_dispatch import evaluate_local
from rulerepo_server.services.polyglot.verifier import PolyglotVerifier, VerificationReport


class TestMultilingualRule:
    """End-to-end multilingual rule management acceptance test."""

    # ------------------------------------------------------------------
    # 1. Japanese rule creation
    # ------------------------------------------------------------------

    def test_japanese_rule_creation(self) -> None:
        """A rule can be created with Japanese statement and locale='ja'."""
        rule = Rule(
            statement="月の残業時間は45時間を超えてはならない。",
            locale="ja",
            jurisdiction="JP",
            legal_force="statutory",
            kind=RuleKind.COMPUTATIONAL,
        )
        assert rule.locale == "ja"
        assert rule.statement.startswith("月の残業時間")
        assert rule.kind == RuleKind.COMPUTATIONAL

    # ------------------------------------------------------------------
    # 2. Translation linking
    # ------------------------------------------------------------------

    def test_translation_domain_model(self) -> None:
        """RuleTranslation domain object can link JA and EN rules."""
        translation = RuleTranslation(
            rule_id=Rule().id,
            language="en",
            statement="Monthly overtime hours must not exceed 45 hours.",
            translator="human",
            equivalence_score=0.0,
        )
        assert translation.language == "en"
        assert "45 hours" in translation.statement

    # ------------------------------------------------------------------
    # 3. Equivalence verification (mock LLM)
    # ------------------------------------------------------------------

    @pytest.fixture()
    def session(self) -> AsyncMock:
        return AsyncMock()

    async def test_equivalence_check_without_llm(self, session: AsyncMock) -> None:
        """Verifier uses length-ratio heuristic when no Gemini client."""
        verifier = PolyglotVerifier(session, gemini_client=None)

        report = await verifier.verify_equivalence(
            rule_id="r-overtime-ja",
            primary_statement="月の残業時間は45時間を超えてはならない。",
            primary_language="ja",
            translations={"en": "Monthly overtime hours must not exceed 45 hours."},
        )

        assert isinstance(report, VerificationReport)
        assert len(report.results) == 1
        assert report.results[0].language == "en"
        assert 0.0 <= report.results[0].score <= 1.0

    async def test_equivalence_check_with_mock_llm(self, session: AsyncMock) -> None:
        """Verifier calls LLM for semantic scoring when available."""
        from unittest.mock import patch

        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"score": 0.95, "notes": "Accurate translation"}'
        mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

        verifier = PolyglotVerifier(session, gemini_client=mock_gemini)

        with patch("rulerepo_server.core.config.get_settings") as mock_settings:
            mock_settings.return_value.llm_default_model = "gemini-3-flash-preview"

            report = await verifier.verify_equivalence(
                rule_id="r-overtime-ja",
                primary_statement="月の残業時間は45時間を超えてはならない。",
                primary_language="ja",
                translations={"en": "Monthly overtime hours must not exceed 45 hours."},
            )

        assert report.results[0].score == 0.95
        assert not report.results[0].drift_detected

    async def test_drift_detection_on_divergent_translation(self, session: AsyncMock) -> None:
        """Verifier flags drift when translation diverges significantly."""
        from unittest.mock import patch

        mock_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"score": 0.4, "notes": "Translation is about a different topic"}'
        mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

        verifier = PolyglotVerifier(session, gemini_client=mock_gemini)

        with patch("rulerepo_server.core.config.get_settings") as mock_settings:
            mock_settings.return_value.llm_default_model = "gemini-3-flash-preview"

            report = await verifier.verify_equivalence(
                rule_id="r-overtime-ja",
                primary_statement="月の残業時間は45時間を超えてはならない。",
                primary_language="ja",
                translations={"en": "All employees must wear safety helmets."},
            )

        assert report.has_drift is True
        assert report.results[0].drift_detected is True
        assert report.results[0].score < 0.85

    # ------------------------------------------------------------------
    # 4. Evaluate subject against Japanese rule
    # ------------------------------------------------------------------

    def test_evaluate_japanese_computational_rule(self) -> None:
        """A Japanese computational rule evaluates correctly via kind dispatch."""
        rule = {
            "id": "r-overtime-ja",
            "kind": "computational",
            "statement": "月の残業時間は45時間を超えてはならない。",
            "modality": "MUST_NOT",
            "severity": "HIGH",
        }

        # Subject: employee with 60h overtime
        subject = EvaluationSubject(
            kind=SubjectKind.TRANSACTION,
            payload={"overtime_hours": 60, "employee_id": "E001"},
        )
        ctx = assemble_context_from_subject(subject)

        verdict, model_id, _ = evaluate_local(rule, ctx)
        assert verdict.verdict == Verdict.DENY
        assert model_id == "local/kind-dispatch"

    def test_evaluate_english_translation_gives_same_result(self) -> None:
        """The English translation of the same rule produces the same verdict."""
        rule_en = {
            "id": "r-overtime-en",
            "kind": "computational",
            "statement": "Monthly overtime hours MUST NOT exceed 45 hours.",
            "modality": "MUST_NOT",
            "severity": "HIGH",
        }

        subject = EvaluationSubject(
            kind=SubjectKind.TRANSACTION,
            payload={"overtime_hours": 60, "employee_id": "E001"},
        )
        ctx = assemble_context_from_subject(subject)

        verdict, _, _ = evaluate_local(rule_en, ctx)
        assert verdict.verdict == Verdict.DENY

    # ------------------------------------------------------------------
    # 5. Search language filtering
    # ------------------------------------------------------------------

    def test_accept_language_header_parsing(self) -> None:
        """Accept-Language header is correctly parsed for search filtering."""
        from rulerepo_server.api.v1.search import _parse_accept_language

        assert _parse_accept_language("ja") == "ja"
        assert _parse_accept_language("ja-JP") == "ja"
        assert _parse_accept_language("en-US,en;q=0.9,ja;q=0.8") == "en"

    def test_search_filter_includes_language(self) -> None:
        """Search query with language filter produces primary_language ES filter."""
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="残業", language="ja")
        filters = _build_filters(query)
        assert filters["primary_language"] == "ja"

    def test_accept_language_header_applied_to_search(self) -> None:
        """Accept-Language header is applied when no explicit language param."""
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="overtime")
        filters = _build_filters(query, accept_language="ja,en;q=0.9")
        assert filters["primary_language"] == "ja"

    def test_explicit_language_overrides_header(self) -> None:
        """Explicit language param takes precedence over Accept-Language header."""
        from rulerepo_server.api.v1.search import _build_filters
        from rulerepo_server.schemas.search import SearchQuery

        query = SearchQuery(query="overtime", language="en")
        filters = _build_filters(query, accept_language="ja")
        assert filters["primary_language"] == "en"

    # ------------------------------------------------------------------
    # Translation verification domain model
    # ------------------------------------------------------------------

    def test_verification_result_pass(self) -> None:
        """TranslationVerification records a passing result."""
        v = TranslationVerification(
            original_statement="月の残業時間は45時間を超えてはならない。",
            translated_statement="Monthly overtime must not exceed 45 hours.",
            equivalence_score=0.95,
            passed=True,
        )
        assert v.passed is True
        assert v.equivalence_score >= 0.85

    def test_verification_result_fail(self) -> None:
        """TranslationVerification records a failing result."""
        v = TranslationVerification(
            original_statement="月の残業時間は45時間を超えてはならない。",
            translated_statement="All employees must wear safety helmets.",
            equivalence_score=0.3,
            passed=False,
        )
        assert v.passed is False
        assert v.equivalence_score < 0.85
