"""Polyglot translation service — manages rule translation links and verification.

Backed by the ``rule_translations`` Postgres table.  Each translation link
connects a source rule to a target rule in a different language.  The
``PolyglotVerifier`` is used for real LLM-based equivalence scoring.

See IMPROVEMENT.md Proposal 8 / RR-020.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.translation import RuleTranslation, TranslationVerification

logger = get_logger(__name__)

EQUIVALENCE_THRESHOLD = 0.85


class TranslationService:
    """Postgres-backed translation service.

    Manages translation links between rules in different languages,
    and coordinates equivalence verification via the PolyglotVerifier.
    """

    def __init__(
        self,
        session: AsyncSession,
        gemini_client: Any | None = None,
    ) -> None:
        self._session = session
        self._gemini = gemini_client

    async def create_translation(
        self,
        rule_id: UUID,
        language: str,
        statement: str,
        translator: str = "human",
    ) -> RuleTranslation:
        """Create a translated rule and link it to the source rule.

        Creates a new rule in the ``rules`` table with the translated
        statement and the target ``locale``, then creates a link row
        in ``rule_translations``.

        Args:
            rule_id: The UUID of the source (primary-language) rule.
            language: BCP-47 language tag for the translation.
            statement: The translated rule statement text.
            translator: Who/what produced the translation.

        Returns:
            A domain RuleTranslation representing the link.
        """
        from rulerepo_server.adapters.postgres.models import (
            RuleModel,
            RuleTranslationModel,
        )

        # Verify source rule exists.
        source = await self._session.get(RuleModel, str(rule_id))
        if source is None:
            raise NotFoundError(f"Source rule {rule_id} not found")

        # Create the target rule with the same metadata but translated statement.
        target_id = uuid4()
        now = datetime.now(tz=UTC)
        target = RuleModel(
            id=target_id,
            project_id=source.project_id,
            statement=statement,
            modality=source.modality,
            severity=source.severity,
            status=source.status,
            scope=source.scope,
            tags=source.tags,
            rationale=source.rationale,
            locale=language,
            equivalence_id=source.equivalence_id or str(rule_id),
            applicable_subject_types=source.applicable_subject_types,
            jurisdiction=source.jurisdiction,
            legal_force=source.legal_force,
            created_at=now,
            updated_at=now,
        )
        self._session.add(target)

        # Update source equivalence_id if not already set.
        if not source.equivalence_id:
            source.equivalence_id = str(rule_id)
            source.updated_at = now

        # Create the link.
        link_id = uuid4()
        link = RuleTranslationModel(
            id=link_id,
            source_rule_id=str(rule_id),
            target_rule_id=str(target_id),
            target_language=language,
            verified_by=translator,
            created_at=now,
            updated_at=now,
        )
        self._session.add(link)
        await self._session.flush()

        logger.info(
            "translation_created",
            link_id=str(link_id),
            source_rule_id=str(rule_id),
            target_rule_id=str(target_id),
            language=language,
            translator=translator,
        )

        return RuleTranslation(
            id=link_id,
            rule_id=rule_id,
            language=language,
            statement=statement,
            translator=translator,
        )

    async def get_translations(self, rule_id: UUID) -> list[RuleTranslation]:
        """Return all translations linked to a rule.

        Args:
            rule_id: UUID of the source rule.

        Returns:
            List of RuleTranslation domain objects.
        """
        from rulerepo_server.adapters.postgres.models import (
            RuleModel,
            RuleTranslationModel,
        )

        result = await self._session.execute(
            select(RuleTranslationModel, RuleModel)
            .join(RuleModel, RuleTranslationModel.target_rule_id == RuleModel.id)
            .where(RuleTranslationModel.source_rule_id == str(rule_id))
            .order_by(RuleTranslationModel.created_at)
        )

        translations: list[RuleTranslation] = []
        for link, target_rule in result.all():
            translations.append(
                RuleTranslation(
                    id=link.id if isinstance(link.id, UUID) else UUID(str(link.id)),
                    rule_id=rule_id,
                    language=link.target_language,
                    statement=target_rule.statement,
                    translator=link.verified_by,
                    equivalence_score=link.equivalence_score or 0.0,
                    last_verified_at=link.verified_at,
                    created_at=link.created_at,
                    updated_at=link.updated_at,
                )
            )
        return translations

    async def get_translation(self, translation_id: UUID) -> RuleTranslation:
        """Fetch a single translation link by its ID.

        Args:
            translation_id: UUID of the translation link.

        Returns:
            The matching RuleTranslation.

        Raises:
            NotFoundError: If no link with that ID exists.
        """
        from rulerepo_server.adapters.postgres.models import (
            RuleModel,
            RuleTranslationModel,
        )

        result = await self._session.execute(
            select(RuleTranslationModel, RuleModel)
            .join(RuleModel, RuleTranslationModel.target_rule_id == RuleModel.id)
            .where(RuleTranslationModel.id == str(translation_id))
        )
        row = result.one_or_none()
        if row is None:
            raise NotFoundError(f"Translation {translation_id} not found")

        link, target_rule = row
        return RuleTranslation(
            id=link.id if isinstance(link.id, UUID) else UUID(str(link.id)),
            rule_id=UUID(str(link.source_rule_id)),
            language=link.target_language,
            statement=target_rule.statement,
            translator=link.verified_by,
            equivalence_score=link.equivalence_score or 0.0,
            last_verified_at=link.verified_at,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )

    async def verify_translation(
        self,
        translation_id: UUID,
    ) -> TranslationVerification:
        """Verify a translation's semantic equivalence against the source rule.

        Uses the PolyglotVerifier for LLM-based scoring, falling back to
        a length-ratio heuristic when no Gemini client is available.

        Args:
            translation_id: UUID of the translation link to verify.

        Returns:
            A TranslationVerification result.

        Raises:
            NotFoundError: If the translation does not exist.
        """
        from rulerepo_server.adapters.postgres.models import (
            RuleModel,
            RuleTranslationModel,
        )

        # Fetch link + both rules.
        result = await self._session.execute(
            select(RuleTranslationModel).where(RuleTranslationModel.id == str(translation_id))
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise NotFoundError(f"Translation {translation_id} not found")

        source_rule = await self._session.get(RuleModel, str(link.source_rule_id))
        target_rule = await self._session.get(RuleModel, str(link.target_rule_id))
        if source_rule is None or target_rule is None:
            raise NotFoundError(f"Linked rules not found for translation {translation_id}")

        # Run equivalence check.
        from rulerepo_server.services.polyglot.verifier import PolyglotVerifier

        verifier = PolyglotVerifier(self._session, self._gemini)
        report = await verifier.verify_equivalence(
            rule_id=str(link.source_rule_id),
            primary_statement=source_rule.statement,
            primary_language=source_rule.locale or "en",
            translations={link.target_language: target_rule.statement},
        )

        # Extract score from the report.
        score = 0.5
        if report.results:
            score = report.results[0].score

        now = datetime.now(tz=UTC)
        passed = score >= EQUIVALENCE_THRESHOLD

        # Persist verification results.
        link.equivalence_score = score
        link.verified_at = now
        link.updated_at = now
        await self._session.flush()

        verification = TranslationVerification(
            translation_id=link.id if isinstance(link.id, UUID) else UUID(str(link.id)),
            original_statement=source_rule.statement,
            translated_statement=target_rule.statement,
            back_translated="",
            equivalence_score=score,
            verified_at=now,
            passed=passed,
        )

        logger.info(
            "translation_verified",
            translation_id=str(translation_id),
            equivalence_score=score,
            passed=passed,
        )
        return verification

    async def verify_all_for_rule(self, rule_id: UUID) -> list[TranslationVerification]:
        """Verify all translations linked to a rule.

        Args:
            rule_id: UUID of the source rule.

        Returns:
            List of TranslationVerification results.
        """
        from rulerepo_server.adapters.postgres.models import RuleTranslationModel

        result = await self._session.execute(
            select(RuleTranslationModel).where(RuleTranslationModel.source_rule_id == str(rule_id))
        )
        links = list(result.scalars().all())

        verifications: list[TranslationVerification] = []
        for link in links:
            link_uuid = link.id if isinstance(link.id, UUID) else UUID(str(link.id))
            v = await self.verify_translation(link_uuid)
            verifications.append(v)
        return verifications

    async def list_stale_translations(
        self,
        days_threshold: int = 30,
    ) -> list[RuleTranslation]:
        """Return translation links that need reverification.

        Args:
            days_threshold: Days after which a verification is stale.

        Returns:
            List of stale RuleTranslation domain objects.
        """
        from sqlalchemy import or_

        from rulerepo_server.adapters.postgres.models import (
            RuleModel,
            RuleTranslationModel,
        )

        cutoff = datetime.now(tz=UTC) - timedelta(days=days_threshold)
        result = await self._session.execute(
            select(RuleTranslationModel, RuleModel)
            .join(RuleModel, RuleTranslationModel.target_rule_id == RuleModel.id)
            .where(
                or_(
                    RuleTranslationModel.verified_at.is_(None),
                    RuleTranslationModel.verified_at < cutoff,
                )
            )
            .order_by(RuleTranslationModel.verified_at.asc().nullsfirst())
        )

        translations: list[RuleTranslation] = []
        for link, target_rule in result.all():
            translations.append(
                RuleTranslation(
                    id=link.id if isinstance(link.id, UUID) else UUID(str(link.id)),
                    rule_id=UUID(str(link.source_rule_id)),
                    language=link.target_language,
                    statement=target_rule.statement,
                    translator=link.verified_by,
                    equivalence_score=link.equivalence_score or 0.0,
                    last_verified_at=link.verified_at,
                    created_at=link.created_at,
                    updated_at=link.updated_at,
                )
            )
        return translations
