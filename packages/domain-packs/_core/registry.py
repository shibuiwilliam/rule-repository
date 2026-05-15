"""Registry types for Domain Pack contributions.

Domain Packs register their prompts, analyzers, templates, and metadata
extensions here at server startup.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PromptEntry:
    """A registered prompt template."""

    domain: str
    purpose: str  # "extract", "evaluate", "infer_metadata"
    template_path: Path

    def load(self) -> str:
        """Load the prompt template text."""
        return self.template_path.read_text()


@dataclass
class AnalyzerEntry:
    """A registered document analyzer."""

    domain: str
    name: str
    analyzer_fn: Callable[..., Any] | None = None
    module_path: str = ""


@dataclass
class TemplateEntry:
    """A registered rule template."""

    domain: str
    name: str
    template_path: Path
    rule_count: int = 0


@dataclass
class DomainPackRegistry:
    """Central registry for all Domain Pack contributions.

    Populated at server startup by the loader.
    """

    prompts: dict[tuple[str, str], PromptEntry] = field(default_factory=dict)
    analyzers: dict[tuple[str, str], AnalyzerEntry] = field(default_factory=dict)
    templates: dict[tuple[str, str], TemplateEntry] = field(default_factory=dict)
    metadata_schemas: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register_prompt(self, entry: PromptEntry) -> None:
        """Register a prompt template keyed by (domain, purpose)."""
        self.prompts[(entry.domain, entry.purpose)] = entry

    def register_analyzer(self, entry: AnalyzerEntry) -> None:
        """Register an analyzer keyed by (domain, name)."""
        self.analyzers[(entry.domain, entry.name)] = entry

    def register_template(self, entry: TemplateEntry) -> None:
        """Register a template keyed by (domain, name)."""
        self.templates[(entry.domain, entry.name)] = entry

    def register_metadata_schema(self, domain: str, schema: dict[str, Any]) -> None:
        """Register a metadata extension schema for a domain."""
        self.metadata_schemas[domain] = schema

    def get_prompt(self, domain: str, purpose: str) -> PromptEntry | None:
        """Get a prompt by domain and purpose."""
        return self.prompts.get((domain, purpose))

    def get_analyzer(self, domain: str, name: str) -> AnalyzerEntry | None:
        """Get an analyzer by domain and name."""
        return self.analyzers.get((domain, name))

    def list_domains(self) -> list[str]:
        """List all registered domains."""
        domains: set[str] = set()
        for domain, _ in self.prompts:
            domains.add(domain)
        for domain, _ in self.analyzers:
            domains.add(domain)
        for domain, _ in self.templates:
            domains.add(domain)
        domains.update(self.metadata_schemas.keys())
        return sorted(domains)


# Module-level singleton
_registry = DomainPackRegistry()


def get_pack_registry() -> DomainPackRegistry:
    """Return the global Domain Pack registry singleton."""
    return _registry
