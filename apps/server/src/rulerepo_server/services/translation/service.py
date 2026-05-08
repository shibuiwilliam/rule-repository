"""Polyglot translation service -- manages rule translations and verification.

See IMPROVEMENT.md RR-020.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.translation import RuleTranslation, TranslationVerification

logger = get_logger(__name__)

EQUIVALENCE_THRESHOLD = 0.85


class TranslationService:
    """In-memory translation service.

    Stores translations keyed by their ID. Will be replaced by
    Postgres-backed persistence once the data layer migration lands.
    """

    def __init__(self) -> None:
        self._translations: dict[str, RuleTranslation] = {}

    async def create_translation(
        self,
        rule_id: UUID,
        language: str,
        statement: str,
        translator: str = "human",
    ) -> RuleTranslation:
        """Create a new translation for a rule.

        Args:
            rule_id: The UUID of the original rule.
            language: BCP-47 language tag (e.g. "ja", "de").
            statement: The translated rule statement text.
            translator: Who or what produced the translation.

        Returns:
            The newly created RuleTranslation.
        """
        translation = RuleTranslation(
            rule_id=rule_id,
            language=language,
            statement=statement,
            translator=translator,
        )
        self._translations[str(translation.id)] = translation
        logger.info(
            "translation_created",
            translation_id=str(translation.id),
            rule_id=str(rule_id),
            language=language,
            translator=translator,
        )
        return translation

    async def get_translations(self, rule_id: UUID) -> list[RuleTranslation]:
        """Return all translations for a given rule.

        Args:
            rule_id: The UUID of the rule.

        Returns:
            List of translations ordered by creation time.
        """
        return sorted(
            [t for t in self._translations.values() if t.rule_id == rule_id],
            key=lambda t: t.created_at,
        )

    async def get_translation(self, translation_id: UUID) -> RuleTranslation:
        """Fetch a single translation by ID.

        Args:
            translation_id: UUID of the translation.

        Returns:
            The matching RuleTranslation.

        Raises:
            NotFoundError: If no translation with that ID exists.
        """
        key = str(translation_id)
        if key not in self._translations:
            raise NotFoundError(f"Translation {translation_id} not found")
        return self._translations[key]

    async def verify_translation(
        self,
        translation_id: UUID,
    ) -> TranslationVerification:
        """Verify a translation's accuracy.

        In production this will back-translate via the LLM provider
        abstraction and compute semantic similarity. For now it returns
        a placeholder verification with a high equivalence score.

        Args:
            translation_id: UUID of the translation to verify.

        Returns:
            A TranslationVerification result.

        Raises:
            NotFoundError: If the translation does not exist.
        """
        translation = await self.get_translation(translation_id)

        # Placeholder: in production, call LLM provider for back-translation
        # and compute embedding cosine similarity.
        score = 0.95
        verification = TranslationVerification(
            translation_id=translation.id,
            original_statement="(original rule statement)",
            translated_statement=translation.statement,
            back_translated="(back-translated placeholder)",
            equivalence_score=score,
            passed=score >= EQUIVALENCE_THRESHOLD,
        )

        # Update the translation record with verification results.
        translation.equivalence_score = score
        translation.last_verified_at = verification.verified_at
        translation.updated_at = datetime.now(tz=UTC)

        logger.info(
            "translation_verified",
            translation_id=str(translation_id),
            equivalence_score=score,
            passed=verification.passed,
        )
        return verification

    async def list_stale_translations(
        self,
        days_threshold: int = 30,
    ) -> list[RuleTranslation]:
        """Return translations that have not been verified recently.

        A translation is considered stale if it has never been verified
        or was last verified more than ``days_threshold`` days ago.

        Args:
            days_threshold: Number of days after which a verification
                is considered stale.

        Returns:
            List of stale translations ordered by last verification time.
        """
        cutoff = datetime.now(tz=UTC) - timedelta(days=days_threshold)
        stale = [t for t in self._translations.values() if t.last_verified_at is None or t.last_verified_at < cutoff]
        return sorted(stale, key=lambda t: t.last_verified_at or t.created_at)
