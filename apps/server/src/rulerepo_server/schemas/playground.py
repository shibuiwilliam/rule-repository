"""Pydantic v2 schemas for the Rule Playground & Testing Framework."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PlaygroundEvalRequest(BaseModel):
    """Request body for sandbox rule evaluation."""

    rule_statement: str
    rule_modality: str = "MUST"
    rule_severity: str = "MEDIUM"
    sample_code: str | None = None
    sample_facts: dict[str, Any] | None = None


class PlaygroundEvalResponse(BaseModel):
    """Response from a sandbox rule evaluation."""

    verdict: str
    confidence: float
    reasoning: str
    issue_description: str
    fix_suggestion: str | None = None
    locations: list[dict[str, Any]] = []


class TestCaseCreate(BaseModel):
    """Request body for creating a test case."""

    name: str
    sample_input: str
    input_type: str = "code"
    expected_verdict: str


class TestCaseResponse(BaseModel):
    """Serialized test case."""

    id: str
    name: str
    sample_input: str
    input_type: str
    expected_verdict: str
    last_result: str | None = None
    passing: bool | None = None
    last_run_at: str | None = None


class TestRunResult(BaseModel):
    """Summary of running all test cases for a rule."""

    total: int
    passing: int
    failing: int
    results: list[TestCaseResponse]


class TestGenerateRequest(BaseModel):
    """Request body for generating test cases via LLM."""

    count: int = 6
