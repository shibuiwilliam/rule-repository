"""REST API routes for rule CRUD operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import get_graph_repo, get_rule_service
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.rule import RuleCreate, RulesImportRequest, RuleUpdate
from rulerepo_server.services.provenance.lineage_resolver import (
    MAX_LINEAGE_DEPTH,
    resolve_lineage,
)
from rulerepo_server.services.rule_service import RuleService

logger = get_logger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", status_code=201)
async def create_rule(
    data: RuleCreate,
    project_id: str | None = Query(default=None),
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Create a new rule."""
    return await service.create_rule(data, project_id=project_id)


@router.get("")
async def list_rules(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_id: str | None = Query(default=None),
    modality: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """List rules with optional filters and pagination."""
    return await service.list_rules(
        page=page,
        page_size=page_size,
        project_id=project_id,
        modality=modality,
        severity=severity,
        status=status,
    )


@router.get("/context")
async def get_session_context(
    files: str = Query(description="Comma-separated file paths"),
    format: str = Query(default="instructions", description="Output format: instructions, checklist, detailed"),
    project_id: str | None = Query(default=None),
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Lightweight endpoint for agent session startup.

    Resolves scopes from file paths, fetches matching rules,
    and returns formatted context optimized for LLM consumption.
    """
    from rulerepo_server.services.context_delivery.formatter import format_rules
    from rulerepo_server.services.context_delivery.scope_registry import (
        ScopeRegistry,
        resolve_scopes,
    )

    file_list = [f.strip() for f in files.split(",") if f.strip()]

    # Resolve scopes from file paths
    all_scopes: list[str] = []
    for fp in file_list:
        all_scopes.extend(resolve_scopes(fp))
    scopes = list(dict.fromkeys(all_scopes))

    # Load rules and match
    registry = ScopeRegistry()
    await registry.load(service._session)

    ext_to_lang = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
    }
    languages: list[str] = []
    for fp in file_list:
        for ext, lang in ext_to_lang.items():
            if fp.endswith(ext) and lang not in languages:
                languages.append(lang)

    matched_rules = registry.get_rules_for_paths(file_list, languages=languages, max_rules=20)
    rules_text = format_rules(matched_rules, format_type=format) if matched_rules else ""

    return {
        "rules_text": rules_text,
        "rule_count": len(matched_rules),
        "scopes_resolved": scopes,
        "files_analyzed": len(file_list),
    }


@router.get("/{rule_id}/why")
async def get_rule_why(
    rule_id: UUID,
    depth: int = Query(default=3, ge=1, le=MAX_LINEAGE_DEPTH),
    session: AsyncSession = Depends(get_db_session),
    graph_repo: Neo4jGraphRepository = Depends(get_graph_repo),
) -> dict:
    """Get multi-level rationale and provenance lineage for a rule.

    Walks the DERIVES_FROM chain in Neo4j up to ``depth`` levels,
    returning the rule's rationale and its derivation tree.
    """
    try:
        graph = graph_repo
    except Exception:
        graph = None

    lineage = await resolve_lineage(
        rule_id=str(rule_id),
        session=session,
        graph_repo=graph,
        depth=depth,
    )
    return lineage


@router.get("/{rule_id}")
async def get_rule(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Get a single rule by ID."""
    return await service.get_rule(rule_id)


@router.patch("/{rule_id}")
async def update_rule(
    rule_id: UUID,
    data: RuleUpdate,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Update an existing rule."""
    return await service.update_rule(rule_id, data)


@router.post("/{rule_id}/retire")
async def retire_rule(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Retire a rule (soft-delete via effective_period.valid_until)."""
    return await service.retire_rule(rule_id)


@router.get("/{rule_id}/revisions")
async def get_revisions(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> list[dict]:
    """Get the revision history for a rule."""
    return await service.get_revisions(rule_id)


@router.get("/{rule_id}/relationships")
async def get_relationships(
    rule_id: UUID,
    service: RuleService = Depends(get_rule_service),
) -> list[dict]:
    """Get all relationships involving a rule."""
    return await service.get_relationships(rule_id)


@router.get("/{rule_id}/graph")
async def get_graph(
    rule_id: UUID,
    depth: int = Query(default=1, ge=1, le=5),
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Get the relationship subgraph around a rule."""
    return await service.get_graph(rule_id, depth=depth)


@router.post("/import", status_code=201)
async def import_rules(
    body: RulesImportRequest,
    project_id: str | None = Query(default=None),
    service: RuleService = Depends(get_rule_service),
) -> dict:
    """Bulk import rules from a rules.yaml-style payload.

    Creates multiple rules at once. Each rule starts in DRAFT status
    with experimental maturity (shadow mode).
    """
    created = 0
    errors = 0
    rule_ids: list[str] = []

    for item in body.rules:
        try:
            create_kwargs: dict = {
                "statement": item.statement,
                "modality": item.modality,
                "severity": item.severity,
                "scope": item.scope,
                "tags": item.tags + (["imported"] if "imported" not in item.tags else []),
                "rationale": item.rationale or "",
            }
            if item.following_examples:
                create_kwargs["following_examples"] = item.following_examples
            if item.violation_examples:
                create_kwargs["violation_examples"] = item.violation_examples
            if item.applicable_subject_types:
                create_kwargs["applicable_subject_types"] = item.applicable_subject_types
            if item.jurisdiction:
                create_kwargs["jurisdiction"] = item.jurisdiction
            if item.legal_force:
                create_kwargs["legal_force"] = item.legal_force
            if item.review_cadence:
                create_kwargs["review_cadence"] = item.review_cadence
            data = RuleCreate(**create_kwargs)
            result = await service.create_rule(data, project_id=project_id)
            rule_ids.append(str(result["id"]))
            created += 1
        except Exception as exc:
            logger.warning(
                "import_rule_failed",
                statement=item.statement[:80],
                error=str(exc),
            )
            errors += 1

    logger.info("rules_imported", created=created, errors=errors)
    return {
        "created": created,
        "errors": errors,
        "rule_ids": rule_ids,
    }
