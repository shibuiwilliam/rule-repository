"""Gemini API client management using the google-genai SDK."""

from google import genai

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

_client: genai.Client | None = None


def create_gemini_client() -> genai.Client:
    """Create and store the Gemini API client.

    Returns:
        A configured google-genai Client instance.
    """
    global _client
    settings = get_settings()
    _client = genai.Client(api_key=settings.gemini_api_key)
    logger.info("gemini_client_created")
    return _client


def get_gemini_client() -> genai.Client:
    """Return the current Gemini client, creating it if needed.

    Returns:
        The google-genai Client instance.
    """
    global _client
    if _client is None:
        _client = create_gemini_client()
    return _client
