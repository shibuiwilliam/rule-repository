"""Documentation evaluation domain adapter.

Handles markdown documentation content or diffs, extracting structure
information for compliance evaluation against documentation standards.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext

# Mapping from doc path patterns to scopes
DOC_PATH_SCOPE_MAP: dict[str, str] = {
    "api": "documentation/api",
    "user-guide": "documentation/user-guide",
    "developer": "documentation/developer",
    "architecture": "documentation/architecture",
    "operations": "documentation/operations",
    "runbook": "documentation/operations",
    "readme": "documentation/readme",
    "changelog": "documentation/changelog",
    "migration": "documentation/migration",
    "tutorial": "documentation/tutorial",
    "reference": "documentation/reference",
    "faq": "documentation/faq",
    "onboarding": "documentation/onboarding",
}


class DocumentationAdapter:
    """Adapter for documentation evaluation.

    Parses markdown content or diffs, extracts document structure,
    and resolves scopes from document paths and types.
    """

    domain: str = "documentation"

    async def parse(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse a documentation evaluation payload into EvaluationContext.

        Expected payload keys:
            - content: str (markdown content)
            - diff: str (optional unified diff of documentation changes)
            - doc_path: str (path of the document, e.g., "docs/api/endpoints.md")
            - doc_type: str (e.g., "api", "user-guide", "readme")
            - title: str (document title)
            - description: str (description of the change)
            - actor: str

        Args:
            payload: Documentation evaluation payload dict.

        Returns:
            EvaluationContext with documentation metadata in facts.
        """
        content = payload.get("content", "")
        diff_text = payload.get("diff")

        # Extract structure from markdown
        facts: dict[str, Any] = {}
        if content:
            facts["content"] = content
            structure = _extract_markdown_structure(content)
            facts["headings"] = structure["headings"]
            facts["has_code_blocks"] = structure["has_code_blocks"]
            facts["has_links"] = structure["has_links"]
            facts["word_count"] = structure["word_count"]

        doc_path = payload.get("doc_path", "")
        if doc_path:
            facts["doc_path"] = doc_path

        doc_type = payload.get("doc_type", "")
        if doc_type:
            facts["doc_type"] = doc_type

        title = payload.get("title", "")
        if title:
            facts["title"] = title

        # Build narrative
        description = payload.get("description", "")
        narrative = description or f"Documentation evaluation for {doc_path or title or 'document'}"

        return EvaluationContext(
            diff=diff_text,
            facts=facts,
            narrative=narrative,
            intent=description or None,
            actor=payload.get("actor"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from document path and type.

        Args:
            payload: Dict with 'doc_path' and/or 'doc_type' keys.

        Returns:
            Deduplicated list of scope strings.
        """
        scopes: set[str] = set()

        # From explicit doc_type
        doc_type = payload.get("doc_type", "").lower()
        if doc_type and doc_type in DOC_PATH_SCOPE_MAP:
            scopes.add(DOC_PATH_SCOPE_MAP[doc_type])

        # From doc_path
        doc_path = payload.get("doc_path", "").lower()
        if doc_path:
            for keyword, scope in DOC_PATH_SCOPE_MAP.items():
                if keyword in doc_path:
                    scopes.add(scope)

        return sorted(scopes) if scopes else ["documentation/general"]

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return documentation-specific prompt fragments.

        Returns:
            Dict with domain_intro and context_format keys.
        """
        return {
            "domain_intro": (
                "You are evaluating documentation for compliance with documentation "
                "standards. Focus on completeness, clarity, structure, accuracy, "
                "consistency, and adherence to style guidelines."
            ),
            "context_format": (
                "The input contains markdown documentation content and/or a diff "
                "showing changes. Metadata includes the document path, type, title, "
                "and structural analysis (headings, code blocks, links). Evaluate "
                "whether the documentation meets the given quality and style rules."
            ),
        }


def _extract_markdown_structure(content: str) -> dict[str, Any]:
    """Extract basic structural information from markdown content.

    Args:
        content: Markdown text to analyze.

    Returns:
        Dict with headings, has_code_blocks, has_links, word_count.
    """
    headings: list[str] = []
    has_code_blocks = False
    has_links = False
    word_count = 0

    in_code_block = False
    for line in content.split("\n"):
        stripped = line.strip()

        # Track code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            has_code_blocks = True
            continue

        if in_code_block:
            continue

        # Extract headings
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            if heading_text:
                headings.append(heading_text)

        # Check for links
        if "[" in stripped and "](" in stripped:
            has_links = True

        # Count words (excluding code blocks)
        word_count += len(stripped.split())

    return {
        "headings": headings,
        "has_code_blocks": has_code_blocks,
        "has_links": has_links,
        "word_count": word_count,
    }
