"""Gemini embedding generation for rule statements."""

from __future__ import annotations

from google import genai

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL = "gemini-embedding-exp-03-07"
EMBEDDING_DIMENSION = 768


async def generate_embedding(client: genai.Client, text: str) -> list[float]:
    """Generate an embedding vector for a text string.

    Args:
        client: The google-genai Client instance.
        text: Text to embed (typically a rule statement).

    Returns:
        A list of floats representing the embedding vector.
    """
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        embedding = list(result.embeddings[0].values)
        logger.info("embedding_generated", text_length=len(text), dim=len(embedding))
        return embedding
    except Exception as exc:
        logger.warning("embedding_generation_failed", error=str(exc))
        return []


async def generate_embeddings_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Args:
        client: The google-genai Client instance.
        texts: List of texts to embed.

    Returns:
        List of embedding vectors, one per input text.
    """
    if not texts:
        return []

    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
        )
        embeddings = [list(e.values) for e in result.embeddings]
        logger.info("batch_embeddings_generated", count=len(embeddings))
        return embeddings
    except Exception as exc:
        logger.warning("batch_embedding_failed", error=str(exc))
        return [[] for _ in texts]
