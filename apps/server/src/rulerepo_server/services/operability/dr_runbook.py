"""Disaster recovery runbook and drill tracking (RR-028).

Defines recovery procedures for each tier component and tracks
when drills were last executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RecoveryProcedure:
    """A single component's disaster recovery procedure."""

    component: str  # e.g., "postgres", "elasticsearch", "neo4j"
    rto_hours: int  # Recovery Time Objective
    rpo_hours: int  # Recovery Point Objective
    steps: list[str] = field(default_factory=list)
    last_drill: datetime | None = None
    last_drill_result: str = ""  # "pass" or "fail"


DEFAULT_PROCEDURES: list[RecoveryProcedure] = [
    RecoveryProcedure(
        component="postgres",
        rto_hours=1,
        rpo_hours=0,
        steps=[
            "1. Verify backup availability in configured backup location",
            "2. Provision new Postgres instance from latest WAL-G backup",
            "3. Verify data integrity with pg_checksums",
            "4. Update DATABASE_URL and restart server",
            "5. Run smoke test: POST /api/v1/health",
        ],
    ),
    RecoveryProcedure(
        component="elasticsearch",
        rto_hours=2,
        rpo_hours=1,
        steps=[
            "1. Provision new ES cluster",
            "2. Trigger full re-index from Postgres",
            "3. Verify index template and mappings",
            "4. Update ELASTICSEARCH_URL and restart server",
        ],
    ),
    RecoveryProcedure(
        component="neo4j",
        rto_hours=2,
        rpo_hours=4,
        steps=[
            "1. Provision new Neo4j instance",
            "2. Run reconcile_graph.py to rebuild from Postgres",
            "3. Verify constraint and index creation",
            "4. Update NEO4J_URI and restart server",
        ],
    ),
    RecoveryProcedure(
        component="redis",
        rto_hours=0,
        rpo_hours=0,
        steps=[
            "1. Provision new Redis instance",
            "2. Update REDIS_URL",
            "3. Queue will auto-recover; no data loss (jobs re-enqueue)",
        ],
    ),
    RecoveryProcedure(
        component="llm_provider",
        rto_hours=0,
        rpo_hours=0,
        steps=[
            "1. Check LLM_PROVIDER_PRIMARY availability",
            "2. If down, fallback chain in router.py auto-activates",
            "3. Verify with: POST /api/v1/evaluate with test input",
        ],
    ),
]


class DRRunbookService:
    """Manages disaster recovery runbook and drill history."""

    def __init__(self) -> None:
        self._procedures = {p.component: p for p in DEFAULT_PROCEDURES}
        self._drill_history: list[dict[str, Any]] = []

    def get_runbook(self) -> list[RecoveryProcedure]:
        """Return all recovery procedures."""
        return list(self._procedures.values())

    def get_procedure(self, component: str) -> RecoveryProcedure | None:
        """Return the recovery procedure for a specific component."""
        return self._procedures.get(component)

    def record_drill(self, component: str, result: str, notes: str = "") -> dict[str, Any]:
        """Record the execution of a DR drill.

        Args:
            component: The component that was drilled.
            result: "pass" or "fail".
            notes: Optional free-text notes.

        Returns:
            The drill record.
        """
        now = datetime.now(tz=UTC)
        if component in self._procedures:
            proc = self._procedures[component]
            self._procedures[component] = RecoveryProcedure(
                component=proc.component,
                rto_hours=proc.rto_hours,
                rpo_hours=proc.rpo_hours,
                steps=proc.steps,
                last_drill=now,
                last_drill_result=result,
            )
        record: dict[str, Any] = {
            "component": component,
            "result": result,
            "notes": notes,
            "timestamp": now.isoformat(),
        }
        self._drill_history.append(record)
        logger.info("dr_drill_recorded", component=component, result=result)
        return record

    def get_drill_history(self) -> list[dict[str, Any]]:
        """Return all recorded drill results."""
        return list(self._drill_history)

    def get_overdue_drills(self, max_days: int = 90) -> list[str]:
        """Return components whose last drill is older than *max_days*.

        Components that have never been drilled are always included.
        """
        now = datetime.now(tz=UTC)
        overdue: list[str] = []
        for proc in self._procedures.values():
            if proc.last_drill is None or (now - proc.last_drill).days > max_days:
                overdue.append(proc.component)
        return overdue
