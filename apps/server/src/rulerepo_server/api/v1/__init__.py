"""API v1 router assembly — includes all sub-routers."""

from fastapi import APIRouter

from rulerepo_server.api.v1.agent_governance import router as agent_governance_router
from rulerepo_server.api.v1.alerts import router as alerts_router
from rulerepo_server.api.v1.discovery import router as discovery_router
from rulerepo_server.api.v1.evaluation import router as evaluation_router
from rulerepo_server.api.v1.extraction import router as extraction_router
from rulerepo_server.api.v1.federation import router as federation_router
from rulerepo_server.api.v1.feedback import router as feedback_router
from rulerepo_server.api.v1.intelligence import router as intelligence_router
from rulerepo_server.api.v1.intent import router as intent_router
from rulerepo_server.api.v1.playground import router as playground_router
from rulerepo_server.api.v1.projects import router as projects_router
from rulerepo_server.api.v1.proposals import router as proposals_router
from rulerepo_server.api.v1.relationships import router as relationships_router
from rulerepo_server.api.v1.review import router as review_router
from rulerepo_server.api.v1.rules import router as rules_router
from rulerepo_server.api.v1.search import router as search_router
from rulerepo_server.api.v1.snapshots import router as snapshots_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(agent_governance_router)
v1_router.include_router(alerts_router)
v1_router.include_router(rules_router)
v1_router.include_router(search_router)
v1_router.include_router(evaluation_router)
v1_router.include_router(review_router)
v1_router.include_router(relationships_router)
v1_router.include_router(extraction_router)
v1_router.include_router(intent_router)
v1_router.include_router(intelligence_router)
v1_router.include_router(discovery_router)
v1_router.include_router(federation_router)
v1_router.include_router(feedback_router)
v1_router.include_router(playground_router)
v1_router.include_router(projects_router)
v1_router.include_router(proposals_router)
v1_router.include_router(snapshots_router)


@v1_router.get("/health", tags=["health"])
async def api_health() -> dict[str, str]:
    """API-level health check."""
    return {"status": "ok", "version": "v1"}
