"""Intent API service — classifies natural-language queries and routes to handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from rulerepo_server.core.llm import get_default_config
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.search import SearchService

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "intent_prompts"

CLASSIFY_PROMPT = """Classify the user's intent into exactly one of these categories:
- lookup_rule: The user wants to find a specific rule or set of rules.
- check_compliance: The user wants to check if an action complies with rules.
- find_conflicts: The user wants to find conflicting rules.
- explain_rule: The user wants an explanation of a specific rule.
- search_rules: The user wants to search for rules by topic or keyword.
- simulate_change: The user wants to understand the impact of a rule change.

User query: {query}

Return a JSON object with:
- "intent": the classified intent (one of the above)
- "keywords": array of key terms extracted from the query
- "scope": array of inferred scope labels (if any)
- "explanation": brief explanation of why you chose this intent
"""


class IntentClassifier:
    """Classifies natural-language queries into intent types using Gemini."""

    def __init__(self, gemini_client: genai.Client) -> None:
        self._client = gemini_client
        self._config = get_default_config()

    async def classify(self, query: str) -> dict[str, Any]:
        """Classify a natural-language query into an intent with parameters.

        Args:
            query: The user's natural-language question.

        Returns:
            Dictionary with intent type, keywords, scope, and explanation.
        """
        prompt = CLASSIFY_PROMPT.format(query=query)

        intent_schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "lookup_rule",
                        "check_compliance",
                        "find_conflicts",
                        "explain_rule",
                        "search_rules",
                        "simulate_change",
                    ],
                },
                "keywords": {"type": "array", "items": {"type": "string"}},
                "scope": {"type": "array", "items": {"type": "string"}},
                "explanation": {"type": "string"},
            },
            "required": ["intent", "keywords"],
        }

        try:
            response = self._client.models.generate_content(
                model=self._config.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=intent_schema,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low",
                    ),
                ),
            )
            result = json.loads(response.text) if response.text else {}
            logger.info("intent_classified", intent=result.get("intent"), query=query[:100])
            return result
        except Exception as exc:
            logger.warning("intent_classification_failed", error=str(exc))
            return {
                "intent": "search_rules",
                "keywords": query.split()[:5],
                "scope": [],
                "explanation": "Fallback to search due to classification error",
            }


class IntentRouter:
    """Routes classified intents to the appropriate service handlers."""

    def __init__(
        self,
        classifier: IntentClassifier,
        search_service: SearchService,
    ) -> None:
        self._classifier = classifier
        self._search = search_service

    async def handle(self, query: str, context: dict | None = None) -> dict[str, Any]:
        """Classify a query and route to the appropriate handler.

        Args:
            query: The user's natural-language question.
            context: Optional additional context.

        Returns:
            Response with intent, result data, and explanation.
        """
        classification = await self._classifier.classify(query)
        intent = classification.get("intent", "search_rules")
        keywords = classification.get("keywords", [])
        scope = classification.get("scope", [])
        explanation = classification.get("explanation", "")

        # Route to handler
        match intent:
            case "lookup_rule" | "search_rules":
                search_query = " ".join(keywords) if keywords else query
                filters = {"scope": scope} if scope else {}
                result = await self._search.hybrid_search(search_query, filters=filters, page=1, page_size=10)
            case "find_conflicts":
                search_query = " ".join(keywords) if keywords else query
                result = await self._search.fulltext_search(search_query, page=1, page_size=20)
            case "check_compliance":
                # Route to the evaluation engine
                result = {
                    "evaluation_endpoint": "/api/v1/evaluate",
                    "suggestion": ("Use POST /api/v1/evaluate with your context for a full compliance check."),
                    "quick_search": (
                        await self._search.hybrid_search(" ".join(keywords) if keywords else query, page=1, page_size=5)
                    ),
                }
            case "explain_rule" | "simulate_change":
                search_query = " ".join(keywords) if keywords else query
                result = await self._search.hybrid_search(search_query, page=1, page_size=5)
            case _:
                result = await self._search.fulltext_search(query, page=1, page_size=10)

        return {
            "intent": intent,
            "result": result,
            "explanation": explanation,
        }
