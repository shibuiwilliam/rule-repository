"""E2E test fixtures — connect to REAL services (Postgres, ES, Neo4j, Gemini).

These tests require:
1. docker compose up (all services running)
2. RULEREPO_LIVE_LLM=1 environment variable
3. GEMINI_API_KEY set in .env

Usage:
    RULEREPO_LIVE_LLM=1 uv run python -m pytest apps/server/tests/e2e/ -v
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

# Base URL of the running server
SERVER_URL = os.environ.get("RULEREPO_SERVER_URL", "http://localhost:8000")

# Path to sample rules
REPO_ROOT = Path(__file__).resolve().parents[4]  # apps/server/tests/e2e → repo root
COMPANY_RULES_DIR = REPO_ROOT / "sample_rules" / "company_rules"
CODING_RULES_DIR = REPO_ROOT / "sample_rules" / "coding_rules"


@pytest.fixture(scope="session")
def server_url() -> str:
    """Base URL of the running Rule Repository server."""
    return SERVER_URL


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    """Async HTTP client for the running server."""
    async with httpx.AsyncClient(base_url=SERVER_URL, timeout=120) as client:
        # Verify server is reachable
        try:
            resp = await client.get("/healthz")
            assert resp.status_code == 200, f"Server not healthy: {resp.status_code}"
        except httpx.ConnectError:
            pytest.skip(f"Cannot connect to server at {SERVER_URL}")
        yield client


@pytest.fixture
def company_rules_dir() -> Path:
    """Path to sample_rules/company_rules/."""
    assert COMPANY_RULES_DIR.exists(), f"Sample rules not found at {COMPANY_RULES_DIR}"
    return COMPANY_RULES_DIR


@pytest.fixture
def coding_rules_dir() -> Path:
    """Path to sample_rules/coding_rules/."""
    assert CODING_RULES_DIR.exists(), f"Sample rules not found at {CODING_RULES_DIR}"
    return CODING_RULES_DIR


@pytest.fixture
def sample_python_code_good() -> str:
    """Sample Python code that follows coding standards (should ALLOW)."""
    return '''"""User profile API handlers."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.deps import get_db_session
from app.core.errors import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    """User profile response model."""

    id: UUID
    username: str
    display_name: str
    bio: str = ""


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    session=Depends(get_db_session),
) -> UserResponse:
    """Get a user profile by ID.

    Args:
        user_id: The user's UUID.
        session: Database session.

    Returns:
        User profile data.

    Raises:
        NotFoundError: If user does not exist.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User", str(user_id))
    logger.info("user_fetched", user_id=str(user_id))
    return UserResponse.model_validate(user)
'''


@pytest.fixture
def sample_python_code_bad() -> str:
    """Sample Python code with violations (should DENY)."""
    return """import os
import sys

def get_user(id):
    # no type hints, no docstring, bare exception
    try:
        conn = psycopg2.connect("postgresql://admin:password123@localhost/mydb")
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM users WHERE id = {id}")  # SQL injection!
        user = cursor.fetchone()
        print(f"Found user: {user}")  # using print instead of logger
        return user
    except:
        pass  # bare except, swallowing errors
"""


@pytest.fixture
def sample_diff_bad() -> str:
    """A unified diff that introduces violations."""
    return """diff --git a/src/api/handlers/payment.py b/src/api/handlers/payment.py
new file mode 100644
--- /dev/null
+++ b/src/api/handlers/payment.py
@@ -0,0 +1,20 @@
+import os
+
+def process_refund(data):
+    # No type hints, no docstring, no Pydantic validation
+    amount = data["amount"]
+    user_id = data["user_id"]
+
+    # Hardcoded database password
+    db_pass = "supersecret123"
+
+    # SQL injection vulnerability
+    query = f"UPDATE accounts SET balance = balance + {amount} WHERE user_id = '{user_id}'"
+
+    # Using print instead of structured logging
+    print(f"Processing refund of {amount} for user {user_id}")
+
+    # No error handling
+    result = execute_query(query)
+
+    return {"status": "ok", "amount": amount}
"""
