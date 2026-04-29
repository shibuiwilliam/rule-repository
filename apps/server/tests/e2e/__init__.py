"""End-to-end tests — require docker-compose stack + GEMINI_API_KEY.

Run with:
    RULEREPO_LIVE_LLM=1 uv run python -m pytest apps/server/tests/e2e/ -v

These tests call the REAL Gemini API and the REAL database stack.
They are NOT part of the default test suite (gated behind RULEREPO_LIVE_LLM=1).
"""
