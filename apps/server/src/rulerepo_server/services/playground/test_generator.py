"""Test case generator — uses Gemini to create test cases for a rule.

Per CLAUDE.md section 9.3: uses structured output, thinking_level="low",
and default temperature (1.0).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.genai import types

from rulerepo_server.core.llm import get_default_config
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt() -> str:
    """Load the test-case generation prompt template.

    Returns:
        The prompt template string.
    """
    return (PROMPTS_DIR / "generate_test_cases.txt").read_text()


async def generate_test_cases(
    rule: dict[str, Any],
    gemini_client: Any,
    count: int = 6,
) -> list[dict[str, Any]]:
    """Generate test cases for a rule via the Gemini API.

    Args:
        rule: Dict with statement, modality, severity fields.
        gemini_client: A google-genai Client instance.
        count: Number of test cases to generate (default 6).

    Returns:
        List of dicts with name, sample_input, expected_verdict, input_type.
    """
    config = get_default_config()
    template = _load_prompt()
    prompt = template.format(
        statement=rule["statement"],
        modality=rule["modality"],
        severity=rule["severity"],
        count=count,
    )

    _json_schema = {
        "type": "object",
        "properties": {
            "test_cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "sample_input": {"type": "string"},
                        "expected_verdict": {"type": "string", "enum": ["ALLOW", "DENY"]},
                    },
                    "required": ["name", "sample_input", "expected_verdict"],
                },
            },
        },
        "required": ["test_cases"],
    }

    try:
        response = await gemini_client.aio.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=_json_schema,
                thinking_config=types.ThinkingConfig(
                    thinking_level="low",
                ),
                # Temperature stays at default 1.0 per CLAUDE.md §9.3
            ),
        )

        data = json.loads(response.text or "{}") if response.text else {}
        raw_cases = data.get("test_cases", [])

        result: list[dict[str, Any]] = []
        for tc in raw_cases:
            if isinstance(tc, dict) and "name" in tc and "sample_input" in tc:
                result.append(
                    {
                        "name": tc["name"],
                        "sample_input": tc["sample_input"],
                        "expected_verdict": tc.get("expected_verdict", "ALLOW"),
                        "input_type": "code",
                    }
                )

        logger.info("test_cases_generated", count=len(result))
        return result

    except Exception as exc:
        logger.warning("test_case_generation_failed", error=str(exc))
        return []
