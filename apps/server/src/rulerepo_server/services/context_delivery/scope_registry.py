"""Scope-to-Rule Mapping Registry — fast file-path-to-rules lookup.

Per CLAUDE_ENHANCE.md §2.3: pre-computed mapping from file glob patterns
to rule IDs. Cached in memory, refreshed on rule changes.
Enables sub-10ms rule selection for the common case.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Default file-path → scope mapping for common project structures.
# Teams can override this via project metadata or rules.yaml scope_map.
DEFAULT_SCOPE_MAP: dict[str, list[str]] = {
    "**/*.py": ["engineering/python"],
    "src/api/**/*.py": ["engineering/python/api"],
    "src/api/**": ["engineering/api"],
    "tests/**": ["engineering/testing"],
    "test/**": ["engineering/testing"],
    "migrations/**": ["engineering/database/migrations"],
    "alembic/**": ["engineering/database/migrations"],
    "**/*.ts": ["engineering/typescript"],
    "**/*.tsx": ["engineering/typescript/react"],
    "**/*.js": ["engineering/javascript"],
    "**/*.jsx": ["engineering/javascript/react"],
    "**/*.go": ["engineering/go"],
    "**/*.rs": ["engineering/rust"],
    "**/*.java": ["engineering/java"],
    "*.md": ["engineering/documentation"],
    "docs/**": ["engineering/documentation"],
    "Dockerfile*": ["engineering/docker"],
    "docker-compose*": ["engineering/docker"],
    ".github/**": ["engineering/ci"],
}


def resolve_scopes(
    file_path: str,
    custom_map: dict[str, list[str]] | None = None,
) -> list[str]:
    """Resolve all matching scopes for a file path using fnmatch.

    Checks the custom scope map first (if provided), then the default map.
    Returns deduplicated list of scopes ordered from most specific to general.

    Args:
        file_path: Relative file path (e.g., "src/api/payments.py").
        custom_map: Optional project-specific scope overrides.

    Returns:
        List of matching scope strings.
    """
    scope_map = {**(DEFAULT_SCOPE_MAP), **(custom_map or {})}
    matched: list[str] = []

    for pattern, scopes in scope_map.items():
        if fnmatch(file_path, pattern) or fnmatch(file_path.lower(), pattern.lower()):
            matched.extend(scopes)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for s in matched:
        if s not in seen:
            seen.add(s)
            result.append(s)

    return result


class ScopeRegistry:
    """Fast file-path-to-rules lookup, cached in memory.

    Scope mappings are derived from rule scope and tags fields:
    - Rule with scope "engineering/python" → matches language "python"
    - Rule with scope "engineering/api" → matches file glob "src/api/**"
    - Rule with scope "repo:payments-api" → matches repository "payments-api"
    """

    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []
        self._loaded = False

    async def load(self, session: AsyncSession) -> None:
        """Load all active rules from the database.

        Args:
            session: Async database session.
        """
        result = await session.execute(select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"])))
        self._rules = [
            {
                "id": str(r.id),
                "statement": r.statement,
                "modality": r.modality,
                "severity": r.severity,
                "scope": r.scope if isinstance(r.scope, list) else [],
                "tags": r.tags if isinstance(r.tags, list) else [],
                "rationale": r.rationale,
                "status": r.status,
            }
            for r in result.scalars().all()
        ]
        self._loaded = True
        logger.info("scope_registry_loaded", rules_count=len(self._rules))

    def get_rules_for_paths(
        self,
        file_paths: list[str],
        *,
        repository: str | None = None,
        languages: list[str] | None = None,
        max_rules: int = 15,
    ) -> list[dict[str, Any]]:
        """Return rules whose scope matches the given file paths.

        Uses scope/tag matching for fast, in-memory lookup.

        Args:
            file_paths: File paths being worked on.
            repository: Repository identifier.
            languages: Programming languages detected.
            max_rules: Maximum rules to return.

        Returns:
            List of matching rule dicts, ranked by relevance.
        """
        scored: list[tuple[dict[str, Any], float]] = []

        for rule in self._rules:
            score = self._compute_match_score(rule, file_paths, repository, languages)
            if score > 0:
                scored.append((rule, score))

        # Sort by score (descending), then by severity
        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        scored.sort(
            key=lambda x: (x[1], severity_order.get(x[0].get("severity", "LOW"), 0)),
            reverse=True,
        )

        return [r for r, _ in scored[:max_rules]]

    @staticmethod
    def _compute_match_score(
        rule: dict[str, Any],
        file_paths: list[str],
        repository: str | None,
        languages: list[str] | None,
    ) -> float:
        """Compute how well a rule matches the given context."""
        score = 0.0
        scope = rule.get("scope", [])
        tags = rule.get("tags", [])

        for scope_item in scope:
            s_lower = scope_item.lower()

            # Repository match: "repo:payments-api"
            if s_lower.startswith("repo:") and repository:
                if repository.lower() in s_lower:
                    score += 20.0
                continue

            # Language match: "engineering/python"
            for lang in languages or []:
                if lang.lower() in s_lower:
                    score += 10.0

            # File path match
            for fp in file_paths:
                fp_lower = fp.lower()
                if s_lower in fp_lower or fnmatch(fp_lower, f"*{s_lower}*"):
                    score += 15.0

        # Tag-based matching
        for tag in tags:
            tag_lower = tag.lower()
            for lang in languages or []:
                if lang.lower() == tag_lower:
                    score += 5.0
            for fp in file_paths:
                if tag_lower in fp.lower():
                    score += 3.0

        # If no specific match but rule has broad scope, give small score
        if score == 0 and not scope:
            score = 0.5  # Universal rules with no scope restriction

        return score
