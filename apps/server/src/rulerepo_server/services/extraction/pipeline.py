"""Rule extraction pipeline — ingests documents and proposes candidate rules via Gemini.

Per CLAUDE.md §9.6: every LLM call that produces a candidate rule must log
model ID, prompt version, inputs, outputs, latency, and timestamp to the audit log.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types

from rulerepo_server.adapters.gemini.documents import (
    create_inline_part,
    upload_to_files_api,
)
from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository
from rulerepo_server.core.llm import get_default_config
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def _hash_content(content: str) -> str:
    """Hash content for audit and caching purposes."""
    return hashlib.sha256(content.encode()).hexdigest()


class ExtractionPipeline:
    """Multi-stage pipeline for extracting rules from documents.

    Stages: document parsing -> rule extraction -> metadata inference.
    All LLM calls use structured output and are logged to the audit table.
    """

    def __init__(
        self,
        gemini_client: genai.Client,
        audit_repo: AuditLogRepository | None = None,
        cache_repo: LLMCacheRepository | None = None,
    ) -> None:
        self._client = gemini_client
        self._config = get_default_config()
        self._audit_repo = audit_repo
        self._cache_repo = cache_repo

    async def extract_from_document(
        self,
        file_bytes: bytes,
        mime_type: str,
        filename: str,
        document_id: str = "",
    ) -> dict[str, Any]:
        """Run the full extraction pipeline on a document.

        Args:
            file_bytes: Raw document content.
            mime_type: MIME type of the document.
            filename: Original filename.
            document_id: ID of the document in Postgres (for audit trail).

        Returns:
            Dictionary with extraction_id, document info, and candidate rules.
        """
        extraction_id = uuid4()
        start_time = time.time()

        # Prepare document for Gemini
        if mime_type == "application/pdf" and len(file_bytes) > 50_000:
            file_ref = await upload_to_files_api(self._client, file_bytes, mime_type, filename)
            content_parts: list[types.Part] = [types.Part.from_uri(file_uri=file_ref.uri, mime_type=mime_type)]
        elif mime_type == "application/pdf":
            content_parts = [create_inline_part(file_bytes, mime_type)]
        else:
            text_content = file_bytes.decode("utf-8", errors="replace")
            content_parts = [types.Part.from_text(text=text_content)]

        # Stage 1: Extract rules
        extract_prompt = _load_prompt("extract_rules.txt")
        candidates = await self._extract_rules(content_parts, extract_prompt, extraction_id=str(extraction_id))

        latency_s = round(time.time() - start_time, 2)
        logger.info(
            "extraction_completed",
            extraction_id=str(extraction_id),
            document_id=document_id,
            candidates_count=len(candidates),
            latency_s=latency_s,
            model=self._config.model_id,
        )

        # Stage 2: Resolve intra-document dependencies from depends_on_indices
        for candidate in candidates:
            dep_indices = candidate.get("depends_on_indices", [])
            candidate["suggested_relationships"] = []
            for dep_idx in dep_indices:
                if isinstance(dep_idx, int) and 0 <= dep_idx < len(candidates) and dep_idx != candidate.get("index"):
                    candidate["suggested_relationships"].append(
                        {
                            "target_candidate_index": dep_idx,
                            "relationship_type": "DEPENDS_ON",
                            "reason": f"Rule depends on rule #{dep_idx} from the same document",
                        }
                    )

        return {
            "extraction_id": str(extraction_id),
            "candidates": candidates,
            "model_id": self._config.model_id,
        }

    async def _extract_rules(
        self,
        content_parts: list[types.Part],
        system_prompt: str,
        extraction_id: str = "",
    ) -> list[dict[str, Any]]:
        """Call Gemini to extract rules from document content.

        Uses structured output (JSON) to get parseable results.
        Logs the call to the audit table per CLAUDE.md §9.6.

        Args:
            content_parts: Document content as Gemini Parts.
            system_prompt: The extraction prompt.
            extraction_id: ID for audit trail linking.

        Returns:
            List of candidate rule dictionaries.
        """
        prompt_version = _hash_content(system_prompt)[:16]
        start_time = time.time()

        candidate_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "modality": {
                        "type": "string",
                        "enum": ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    },
                    "scope": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                    "context": {"type": "string"},
                    "preconditions": {"type": "array", "items": {"type": "string"}},
                    "exceptions": {"type": "array", "items": {"type": "string"}},
                    "following_examples": {"type": "array", "items": {"type": "string"}},
                    "violation_examples": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "source_section": {"type": "string"},
                    "source_page": {"type": "integer"},
                    "depends_on_indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Indices of other rules this rule depends on",
                    },
                },
                "required": ["statement", "modality", "confidence"],
            },
        }

        try:
            response = self._client.models.generate_content(
                model=self._config.model_id,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=system_prompt)] + content_parts,
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=candidate_schema,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=self._config.thinking_level,
                    ),
                    # Temperature stays at default 1.0 per CLAUDE.md §9.3
                ),
            )

            latency_ms = int((time.time() - start_time) * 1000)
            result_text = response.text or "[]"
            candidates = json.loads(result_text)

            for i, candidate in enumerate(candidates):
                candidate["index"] = i

            # Audit log: record the LLM call (CLAUDE.md §9.6)
            if self._audit_repo:
                await self._audit_repo.append(
                    action="llm_extraction_call",
                    actor="extraction_pipeline",
                    resource_type="extraction",
                    resource_id=extraction_id,
                    details={
                        "model_id": self._config.model_id,
                        "prompt_version": prompt_version,
                        "thinking_level": self._config.thinking_level,
                        "candidates_count": len(candidates),
                        "latency_ms": latency_ms,
                        "output_hash": _hash_content(result_text)[:16],
                    },
                )

            return candidates

        except Exception as exc:
            logger.warning("rule_extraction_failed", error=str(exc))
            # Log failure to audit as well
            if self._audit_repo:
                try:
                    await self._audit_repo.append(
                        action="llm_extraction_error",
                        actor="extraction_pipeline",
                        resource_type="extraction",
                        resource_id=extraction_id,
                        details={"error": str(exc), "model_id": self._config.model_id},
                    )
                except Exception:
                    logger.warning("audit_log_write_failed_on_error")
            return []
