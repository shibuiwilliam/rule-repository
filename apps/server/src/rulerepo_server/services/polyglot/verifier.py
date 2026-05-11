"""Polyglot rule verification — semantic equivalence checking.

Maintains semantically equivalent rule statements across languages.
Weekly cron checks each translation against the primary statement;
drift triggers a proposal. See PROJECT.md §6.21 and CLAUDE.md §14.12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EquivalenceResult:
    """Result of checking one translation against the primary."""

    language: str
    score: float  # 0.0 to 1.0
    drift_detected: bool
    drift_description: str = ""


@dataclass
class VerificationReport:
    """Result of verifying all translations for a rule."""

    rule_id: str
    primary_language: str
    results: list[EquivalenceResult] = field(default_factory=list)
    verified_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def has_drift(self) -> bool:
        return any(r.drift_detected for r in self.results)


class PolyglotVerifier:
    """Verifies semantic equivalence of rule translations.

    Uses the LLM to compare each translation against the primary
    statement and detect semantic drift.
    """

    DRIFT_THRESHOLD = 0.85

    def __init__(self, session: AsyncSession, gemini_client: Any | None = None) -> None:
        self._session = session
        self._gemini = gemini_client

    async def verify_equivalence(
        self,
        rule_id: str,
        primary_statement: str,
        primary_language: str,
        translations: dict[str, str],
    ) -> VerificationReport:
        """Verify each translation against the primary statement.

        Args:
            rule_id: The rule being verified.
            primary_statement: The canonical statement.
            primary_language: Language code of the primary.
            translations: Map of language code to translated statement.

        Returns:
            VerificationReport with per-language results.
        """
        logger.info(
            "polyglot_verification_started",
            rule_id=rule_id,
            primary_language=primary_language,
            languages=list(translations.keys()),
        )

        results: list[EquivalenceResult] = []

        for lang, translation in translations.items():
            if lang == primary_language:
                continue

            score = await self._check_pair(primary_statement, translation, primary_language, lang)
            drift = score < self.DRIFT_THRESHOLD

            results.append(
                EquivalenceResult(
                    language=lang,
                    score=score,
                    drift_detected=drift,
                    drift_description=f"Score {score:.2f} below threshold {self.DRIFT_THRESHOLD}" if drift else "",
                )
            )

            if drift:
                logger.warning(
                    "polyglot_drift_detected",
                    rule_id=rule_id,
                    language=lang,
                    score=score,
                )

        report = VerificationReport(
            rule_id=rule_id,
            primary_language=primary_language,
            results=results,
        )

        logger.info(
            "polyglot_verification_complete",
            rule_id=rule_id,
            has_drift=report.has_drift,
            languages_checked=len(results),
        )

        return report

    async def _check_pair(
        self,
        primary: str,
        translation: str,
        primary_lang: str,
        target_lang: str,
    ) -> float:
        """Check semantic equivalence of a primary/translation pair.

        Returns a score between 0.0 and 1.0.
        """
        if not self._gemini:
            # Without LLM, do a basic length-ratio heuristic
            ratio = min(len(primary), len(translation)) / max(len(primary), len(translation), 1)
            return min(ratio + 0.3, 1.0)

        # With LLM, use structured output for scoring
        try:
            from google.genai import types

            prompt = (
                f"Compare these two rule statements for semantic equivalence.\n\n"
                f"Primary ({primary_lang}): {primary}\n\n"
                f"Translation ({target_lang}): {translation}\n\n"
                f"Return a JSON object with 'score' (0.0-1.0) and 'notes' (string)."
            )

            from rulerepo_server.core.config import get_settings

            settings = get_settings()
            response = await self._gemini.aio.models.generate_content(
                model=settings.llm_default_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                ),
            )

            import json

            result = json.loads(response.text)
            return float(result.get("score", 0.5))
        except Exception as exc:
            logger.warning("polyglot_llm_check_failed", error=str(exc))
            return 0.5
