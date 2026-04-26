"""REST API route for the Intent API — natural-language query interface."""

from fastapi import APIRouter, Depends

from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.core.deps import get_search_service
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.intent import IntentRequest
from rulerepo_server.services.intent import IntentClassifier, IntentRouter
from rulerepo_server.services.search import SearchService

logger = get_logger(__name__)

router = APIRouter(prefix="/intent", tags=["intent"])


@router.post("")
async def handle_intent(
    request: IntentRequest,
    search_service: SearchService = Depends(get_search_service),
) -> dict:
    """Accept a natural-language query, classify intent, and route to handler.

    This endpoint interprets what the user wants (lookup, compliance check,
    conflict search, explanation, etc.) and delegates to the appropriate
    backend service.
    """
    try:
        gemini = get_gemini_client()
        classifier = IntentClassifier(gemini)
    except Exception:
        # Fallback: treat everything as search if Gemini is unavailable
        result = await search_service.fulltext_search(request.query, page=1, page_size=10)
        return {
            "intent": "search_rules",
            "result": result,
            "explanation": "Gemini unavailable — defaulting to fulltext search",
        }

    intent_router = IntentRouter(classifier, search_service)
    return await intent_router.handle(request.query, request.context)
