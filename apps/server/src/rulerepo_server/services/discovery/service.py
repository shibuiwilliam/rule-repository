"""Discovery service — orchestrates automatic rule discovery scans.

Coordinates source analyzers, pattern deduplication, LLM-based candidate
generation, and persistence of scan results to Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    DEFAULT_PROJECT_ID,
    DiscoveryCandidateModel,
    DiscoveryScanModel,
    RuleModel,
)
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import DiscoveryContext
from rulerepo_server.services.discovery.analyzers.claude_md import ClaudeMdAnalyzer
from rulerepo_server.services.discovery.analyzers.code_patterns import CodePatternsAnalyzer
from rulerepo_server.services.discovery.analyzers.communication_standard import (
    CommunicationStandardAnalyzer,
)
from rulerepo_server.services.discovery.analyzers.contract_corpus import (
    ContractCorpusAnalyzer,
)
from rulerepo_server.services.discovery.analyzers.expense_guideline import (
    ExpenseGuidelineAnalyzer,
)
from rulerepo_server.services.discovery.analyzers.hr_policy import HrPolicyAnalyzer
from rulerepo_server.services.discovery.analyzers.linter_config import LinterConfigAnalyzer
from rulerepo_server.services.discovery.analyzers.policy_document import PolicyDocumentAnalyzer
from rulerepo_server.services.discovery.candidate_generator import generate_candidates
from rulerepo_server.services.discovery.pattern_detector import deduplicate_and_score

logger = get_logger(__name__)


class DiscoveryService:
    """Orchestrates rule discovery scans across source analyzers.

    Runs all registered analyzers against the provided file contents,
    deduplicates and scores patterns, optionally refines them via Gemini,
    and persists the results as discovery candidates.
    """

    def __init__(self, session: AsyncSession, gemini: Any | None = None) -> None:
        """Initialize the discovery service.

        Args:
            session: Async SQLAlchemy session for database operations.
            gemini: Optional Gemini client for LLM-based candidate refinement.
        """
        self._session = session
        self._gemini = gemini
        self._analyzers = [
            ClaudeMdAnalyzer(),
            LinterConfigAnalyzer(),
            CodePatternsAnalyzer(),
            PolicyDocumentAnalyzer(),
            ContractCorpusAnalyzer(),
            HrPolicyAnalyzer(),
            ExpenseGuidelineAnalyzer(),
            CommunicationStandardAnalyzer(),
        ]

    async def start_scan(
        self,
        sources: list[str],
        file_contents: dict[str, str],
        repository: str | None = None,
        project_id: str | None = None,
    ) -> str:
        """Start a discovery scan and return the scan ID.

        Creates a scan record, runs all analyzers, deduplicates patterns,
        generates refined candidates, and stores them in the database.

        Args:
            sources: List of source type identifiers (e.g., ["claude_md", "linter_config"]).
            file_contents: Mapping of file path to file content.
            repository: Optional repository name or URL.

        Returns:
            The UUID string of the created scan.
        """
        scan_id = uuid4()

        # Create scan record
        scan = DiscoveryScanModel(
            id=scan_id,
            status="running",
            sources={"types": sources},
            repository=repository,
            project_id=project_id or DEFAULT_PROJECT_ID,
        )
        self._session.add(scan)
        await self._session.flush()

        logger.info("discovery_scan_started", scan_id=str(scan_id), sources=sources)

        try:
            # Build context
            context = DiscoveryContext(
                file_paths=list(file_contents.keys()),
                file_contents=file_contents,
                repository=repository,
            )

            # Run all analyzers
            all_patterns = []
            for analyzer in self._analyzers:
                try:
                    patterns = await analyzer.analyze(context)
                    all_patterns.extend(patterns)
                except Exception:
                    logger.warning(
                        "analyzer_failed",
                        analyzer=type(analyzer).__name__,
                        exc_info=True,
                    )

            # Deduplicate and score
            deduped = deduplicate_and_score(all_patterns)

            # Generate refined candidates
            candidates = await generate_candidates(deduped, self._gemini)

            # Persist candidates
            for candidate in candidates:
                candidate_model = DiscoveryCandidateModel(
                    id=uuid4(),
                    scan_id=scan_id,
                    statement=candidate["statement"],
                    modality=candidate["modality"],
                    severity=candidate["severity"],
                    scope=candidate.get("scope", []),
                    tags=candidate.get("tags", []),
                    rationale=candidate.get("rationale"),
                    source_type=candidate["source_type"],
                    source_evidence=candidate.get("source_evidence"),
                    confidence=candidate["confidence"],
                    status="pending",
                )
                self._session.add(candidate_model)

            # Update scan status
            await self._session.execute(
                update(DiscoveryScanModel)
                .where(DiscoveryScanModel.id == scan_id)
                .values(
                    status="completed",
                    candidates_found=len(candidates),
                    completed_at=datetime.now(UTC),
                )
            )
            await self._session.flush()

            logger.info(
                "discovery_scan_completed",
                scan_id=str(scan_id),
                candidates_found=len(candidates),
            )

        except Exception:
            await self._session.execute(
                update(DiscoveryScanModel)
                .where(DiscoveryScanModel.id == scan_id)
                .values(
                    status="failed",
                    completed_at=datetime.now(UTC),
                )
            )
            await self._session.flush()
            logger.error("discovery_scan_failed", scan_id=str(scan_id), exc_info=True)
            raise

        return str(scan_id)

    async def get_scan(self, scan_id: str) -> dict:
        """Retrieve a scan record by ID.

        Args:
            scan_id: The UUID string of the scan.

        Returns:
            Dict with scan details.

        Raises:
            ValueError: If the scan is not found.
        """
        result = await self._session.execute(select(DiscoveryScanModel).where(DiscoveryScanModel.id == UUID(scan_id)))
        scan = result.scalar_one_or_none()
        if scan is None:
            msg = f"Scan not found: {scan_id}"
            raise ValueError(msg)

        return {
            "scan_id": str(scan.id),
            "status": scan.status,
            "sources": scan.sources,
            "repository": scan.repository,
            "candidates_found": scan.candidates_found,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        }

    async def get_candidates(
        self,
        scan_id: str,
        status: str | None = None,
    ) -> list[dict]:
        """Retrieve candidates for a given scan.

        Args:
            scan_id: The UUID string of the scan.
            status: Optional filter by candidate status (pending, approved, dismissed).

        Returns:
            List of candidate dicts.
        """
        query = select(DiscoveryCandidateModel).where(DiscoveryCandidateModel.scan_id == UUID(scan_id))
        if status is not None:
            query = query.where(DiscoveryCandidateModel.status == status)

        query = query.order_by(DiscoveryCandidateModel.confidence.desc())

        result = await self._session.execute(query)
        candidates = result.scalars().all()

        return [
            {
                "id": str(c.id),
                "statement": c.statement,
                "modality": c.modality,
                "severity": c.severity,
                "scope": c.scope or [],
                "tags": c.tags or [],
                "rationale": c.rationale,
                "source_type": c.source_type,
                "source_evidence": c.source_evidence,
                "confidence": c.confidence,
                "status": c.status,
            }
            for c in candidates
        ]

    async def approve_candidate(self, candidate_id: str) -> dict:
        """Approve a candidate and create a rule from it.

        Args:
            candidate_id: The UUID string of the candidate.

        Returns:
            Dict with the created rule info and updated candidate status.

        Raises:
            ValueError: If the candidate is not found or already processed.
        """
        result = await self._session.execute(
            select(DiscoveryCandidateModel).where(DiscoveryCandidateModel.id == UUID(candidate_id))
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            msg = f"Candidate not found: {candidate_id}"
            raise ValueError(msg)

        if candidate.status != "pending":
            msg = f"Candidate already processed: {candidate.status}"
            raise ValueError(msg)

        # Inherit project_id from the scan
        scan_result = await self._session.execute(
            select(DiscoveryScanModel).where(DiscoveryScanModel.id == candidate.scan_id)
        )
        scan = scan_result.scalar_one()

        # Create a rule from the candidate
        rule_id = uuid4()
        rule = RuleModel(
            id=rule_id,
            project_id=scan.project_id,
            statement=candidate.statement,
            modality=candidate.modality,
            severity=candidate.severity,
            scope=candidate.scope or [],
            tags=candidate.tags or [],
            rationale=candidate.rationale or "",
        )
        self._session.add(rule)

        # Update candidate
        candidate.status = "approved"
        candidate.created_rule_id = rule_id
        await self._session.flush()

        logger.info(
            "candidate_approved",
            candidate_id=candidate_id,
            rule_id=str(rule_id),
        )

        return {
            "candidate_id": candidate_id,
            "status": "approved",
            "created_rule_id": str(rule_id),
            "statement": candidate.statement,
        }

    async def dismiss_candidate(self, candidate_id: str) -> dict:
        """Dismiss a candidate, marking it as not useful.

        Args:
            candidate_id: The UUID string of the candidate.

        Returns:
            Dict confirming the dismissal.

        Raises:
            ValueError: If the candidate is not found or already processed.
        """
        result = await self._session.execute(
            select(DiscoveryCandidateModel).where(DiscoveryCandidateModel.id == UUID(candidate_id))
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            msg = f"Candidate not found: {candidate_id}"
            raise ValueError(msg)

        if candidate.status != "pending":
            msg = f"Candidate already processed: {candidate.status}"
            raise ValueError(msg)

        candidate.status = "dismissed"
        await self._session.flush()

        logger.info("candidate_dismissed", candidate_id=candidate_id)

        return {
            "candidate_id": candidate_id,
            "status": "dismissed",
        }
