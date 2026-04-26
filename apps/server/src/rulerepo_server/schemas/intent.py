"""Pydantic schemas for the Intent API."""

from typing import Any

from pydantic import BaseModel, Field


class IntentRequest(BaseModel):
    """Natural-language query to the Intent API."""

    query: str = Field(..., min_length=1, max_length=5000, description="Natural-language question")
    context: dict[str, Any] | None = Field(
        default=None, description="Optional context for the query"
    )


class IntentResponse(BaseModel):
    """Response from the Intent API after classifying and routing a query."""

    intent: str = Field(..., description="Classified intent type")
    result: dict[str, Any] = Field(default_factory=dict, description="Intent-specific result data")
    explanation: str = Field(default="", description="Human-readable explanation")
