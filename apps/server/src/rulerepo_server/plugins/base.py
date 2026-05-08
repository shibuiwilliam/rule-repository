"""Base protocols and registries for domain plugins.

A domain plugin registers evaluators, extractors, feedback sources,
fact providers, and persona views with the core. The core never
imports from plugins -- plugins register themselves at startup.

See: PROJECT.md SS6.4, CLAUDE.md SS7
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from rulerepo_server.core.errors import RuleRepoError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PluginError(RuleRepoError):
    """Base exception for plugin-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="PLUGIN_ERROR", status_code=500)


class DuplicateRegistrationError(PluginError):
    """Raised when a plugin component is registered twice under the same key."""

    def __init__(self, registry_name: str, key: str) -> None:
        super().__init__(
            message=(f"Duplicate registration in {registry_name}: '{key}' is already registered"),
        )


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin or component is not registered."""

    def __init__(self, component_type: str, key: str) -> None:
        super().__init__(
            message=f"{component_type} not found: '{key}'",
        )
        self.status_code = 404
        self.code = "PLUGIN_NOT_FOUND"


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class Evaluator(Protocol):
    """Protocol for domain-specific rule evaluators.

    An evaluator receives a subject payload and a set of rules, then
    produces per-rule verdicts using LLM-backed reasoning.
    """

    @property
    def name(self) -> str:
        """Unique name of this evaluator within its domain."""
        ...

    @property
    def domain(self) -> str:
        """Domain identifier (e.g. 'engineering', 'hr', 'legal')."""
        ...

    @property
    def supported_subject_kinds(self) -> list[str]:
        """SubjectKind values this evaluator can handle."""
        ...

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate the subject against the given rules.

        Args:
            subject_payload: Domain-specific subject data.
            rules: List of rule dicts (id, statement, modality, severity, ...).
            context: Additional context (locale, jurisdiction, user info, ...).

        Returns:
            List of verdict dicts, one per rule evaluated. Each dict contains
            at minimum: rule_id, verdict, confidence, reasoning.
        """
        ...


@runtime_checkable
class Extractor(Protocol):
    """Protocol for rule extraction from domain-specific sources.

    An extractor parses raw content (documents, configs, code) and
    produces candidate rules for human review.
    """

    @property
    def name(self) -> str:
        """Unique name of this extractor within its domain."""
        ...

    @property
    def domain(self) -> str:
        """Domain identifier."""
        ...

    @property
    def supported_source_types(self) -> list[str]:
        """Source types this extractor can process (e.g. 'claude_md', 'pdf')."""
        ...

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract candidate rules from raw content.

        Args:
            content: Raw bytes of the source document.
            source_type: Type of source (must be in supported_source_types).
            metadata: Additional metadata (filename, URL, author, ...).

        Returns:
            List of candidate rule dicts, each containing at minimum:
            statement, modality, severity, scope, rationale.
        """
        ...


@runtime_checkable
class FeedbackSource(Protocol):
    """Protocol for capturing feedback events from domain-specific signals.

    Feedback sources detect corrections, overrides, and exceptions
    that feed the rule improvement flywheel.
    """

    @property
    def name(self) -> str:
        """Unique name of this feedback source."""
        ...

    @property
    def domain(self) -> str:
        """Domain identifier."""
        ...

    async def capture(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Capture feedback events from a domain-specific signal.

        Args:
            event: Raw event data from the source system.

        Returns:
            List of feedback event dicts, each containing at minimum:
            kind, subject_kind, original_verdict, corrected_verdict, reason.
        """
        ...


@runtime_checkable
class FactProvider(Protocol):
    """Protocol for providing domain-specific facts to the evaluation context.

    Fact providers enrich the evaluation context with external data
    (e.g. employee records from HR systems, transaction history from ERP).
    """

    @property
    def name(self) -> str:
        """Unique name of this fact provider."""
        ...

    @property
    def domain(self) -> str:
        """Domain identifier."""
        ...

    @property
    def fact_types(self) -> list[str]:
        """Types of facts this provider can supply."""
        ...

    async def provide(
        self,
        fact_type: str,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        """Provide facts for the given query.

        Args:
            fact_type: Type of fact requested (must be in fact_types).
            query: Query parameters for the fact lookup.

        Returns:
            Dict of facts keyed by field name.
        """
        ...


@runtime_checkable
class PersonaView(Protocol):
    """Protocol for department-specific UI surface configuration.

    Persona views define which dashboard widgets, navigation items,
    and evaluation summaries a department sees.
    """

    @property
    def name(self) -> str:
        """View name (e.g. 'engineering_dashboard')."""
        ...

    @property
    def domain(self) -> str:
        """Domain identifier."""
        ...

    @property
    def route_group(self) -> str:
        """Next.js route group (e.g. '(engineering)')."""
        ...

    def get_navigation_items(self) -> list[dict[str, str]]:
        """Return navigation items for this persona.

        Returns:
            List of dicts with 'label', 'href', 'icon' keys.
        """
        ...

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return dashboard widget configurations.

        Returns:
            List of widget config dicts with 'type', 'title', 'config' keys.
        """
        ...


@runtime_checkable
class DomainPlugin(Protocol):
    """Protocol for a complete domain plugin.

    A domain plugin bundles evaluators, extractors, feedback sources,
    fact providers, API routes, and persona views for a single domain.
    Plugins register their components with the plugin registry at startup.
    """

    @property
    def name(self) -> str:
        """Human-readable plugin name."""
        ...

    @property
    def domain(self) -> str:
        """Domain identifier (must be unique across plugins)."""
        ...

    @property
    def description(self) -> str:
        """Brief description of what this plugin provides."""
        ...

    def get_evaluators(self) -> list[Evaluator]:
        """Return all evaluators provided by this plugin."""
        ...

    def get_extractors(self) -> list[Extractor]:
        """Return all extractors provided by this plugin."""
        ...

    def get_feedback_sources(self) -> list[FeedbackSource]:
        """Return all feedback sources provided by this plugin."""
        ...

    def get_fact_providers(self) -> list[FactProvider]:
        """Return all fact providers provided by this plugin."""
        ...

    def get_persona_views(self) -> list[PersonaView]:
        """Return all persona views provided by this plugin."""
        ...


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------


class EvaluatorRegistry:
    """Registry for domain evaluators, keyed by (domain, name)."""

    def __init__(self) -> None:
        self._evaluators: dict[tuple[str, str], Evaluator] = {}

    def register(self, evaluator: Evaluator) -> None:
        """Register an evaluator.

        Args:
            evaluator: The evaluator to register.

        Raises:
            DuplicateRegistrationError: If an evaluator with the same
                (domain, name) is already registered.
        """
        key = (evaluator.domain, evaluator.name)
        if key in self._evaluators:
            raise DuplicateRegistrationError("EvaluatorRegistry", f"{key[0]}/{key[1]}")
        self._evaluators[key] = evaluator
        logger.info(
            "Registered evaluator: %s/%s (subjects: %s)",
            evaluator.domain,
            evaluator.name,
            evaluator.supported_subject_kinds,
        )

    def get(self, domain: str, name: str) -> Evaluator:
        """Get a registered evaluator by domain and name.

        Args:
            domain: Domain identifier.
            name: Evaluator name.

        Returns:
            The registered evaluator.

        Raises:
            PluginNotFoundError: If no evaluator is registered for the key.
        """
        key = (domain, name)
        if key not in self._evaluators:
            raise PluginNotFoundError("Evaluator", f"{domain}/{name}")
        return self._evaluators[key]

    def get_for_domain(self, domain: str) -> list[Evaluator]:
        """Get all evaluators registered for a domain.

        Args:
            domain: Domain identifier.

        Returns:
            List of evaluators for the domain.
        """
        return [e for (d, _), e in self._evaluators.items() if d == domain]

    def get_for_subject_kind(self, subject_kind: str) -> list[Evaluator]:
        """Get all evaluators that support a given subject kind.

        Args:
            subject_kind: The SubjectKind value to match.

        Returns:
            List of evaluators supporting that subject kind.
        """
        return [e for e in self._evaluators.values() if subject_kind in e.supported_subject_kinds]

    def list_all(self) -> list[Evaluator]:
        """Return all registered evaluators."""
        return list(self._evaluators.values())


class ExtractorRegistry:
    """Registry for domain extractors, keyed by (domain, name)."""

    def __init__(self) -> None:
        self._extractors: dict[tuple[str, str], Extractor] = {}

    def register(self, extractor: Extractor) -> None:
        """Register an extractor.

        Args:
            extractor: The extractor to register.

        Raises:
            DuplicateRegistrationError: If an extractor with the same
                (domain, name) is already registered.
        """
        key = (extractor.domain, extractor.name)
        if key in self._extractors:
            raise DuplicateRegistrationError("ExtractorRegistry", f"{key[0]}/{key[1]}")
        self._extractors[key] = extractor
        logger.info(
            "Registered extractor: %s/%s (sources: %s)",
            extractor.domain,
            extractor.name,
            extractor.supported_source_types,
        )

    def get(self, domain: str, name: str) -> Extractor:
        """Get a registered extractor by domain and name.

        Args:
            domain: Domain identifier.
            name: Extractor name.

        Returns:
            The registered extractor.

        Raises:
            PluginNotFoundError: If no extractor is registered for the key.
        """
        key = (domain, name)
        if key not in self._extractors:
            raise PluginNotFoundError("Extractor", f"{domain}/{name}")
        return self._extractors[key]

    def get_for_source_type(self, source_type: str) -> list[Extractor]:
        """Get all extractors that support a given source type.

        Args:
            source_type: Source type to match.

        Returns:
            List of extractors supporting that source type.
        """
        return [e for e in self._extractors.values() if source_type in e.supported_source_types]

    def get_for_domain(self, domain: str) -> list[Extractor]:
        """Get all extractors registered for a domain.

        Args:
            domain: Domain identifier.

        Returns:
            List of extractors for the domain.
        """
        return [e for (d, _), e in self._extractors.items() if d == domain]

    def list_all(self) -> list[Extractor]:
        """Return all registered extractors."""
        return list(self._extractors.values())


class FeedbackRegistry:
    """Registry for feedback sources, keyed by (domain, name)."""

    def __init__(self) -> None:
        self._sources: dict[tuple[str, str], FeedbackSource] = {}

    def register(self, source: FeedbackSource) -> None:
        """Register a feedback source.

        Args:
            source: The feedback source to register.

        Raises:
            DuplicateRegistrationError: If a source with the same
                (domain, name) is already registered.
        """
        key = (source.domain, source.name)
        if key in self._sources:
            raise DuplicateRegistrationError("FeedbackRegistry", f"{key[0]}/{key[1]}")
        self._sources[key] = source
        logger.info("Registered feedback source: %s/%s", source.domain, source.name)

    def get(self, domain: str, name: str) -> FeedbackSource:
        """Get a registered feedback source.

        Args:
            domain: Domain identifier.
            name: Feedback source name.

        Returns:
            The registered feedback source.

        Raises:
            PluginNotFoundError: If no source is registered for the key.
        """
        key = (domain, name)
        if key not in self._sources:
            raise PluginNotFoundError("FeedbackSource", f"{domain}/{name}")
        return self._sources[key]

    def get_for_domain(self, domain: str) -> list[FeedbackSource]:
        """Get all feedback sources for a domain.

        Args:
            domain: Domain identifier.

        Returns:
            List of feedback sources for the domain.
        """
        return [s for (d, _), s in self._sources.items() if d == domain]

    def list_all(self) -> list[FeedbackSource]:
        """Return all registered feedback sources."""
        return list(self._sources.values())


class FactProviderRegistry:
    """Registry for fact providers, keyed by (domain, name)."""

    def __init__(self) -> None:
        self._providers: dict[tuple[str, str], FactProvider] = {}

    def register(self, provider: FactProvider) -> None:
        """Register a fact provider.

        Args:
            provider: The fact provider to register.

        Raises:
            DuplicateRegistrationError: If a provider with the same
                (domain, name) is already registered.
        """
        key = (provider.domain, provider.name)
        if key in self._providers:
            raise DuplicateRegistrationError("FactProviderRegistry", f"{key[0]}/{key[1]}")
        self._providers[key] = provider
        logger.info(
            "Registered fact provider: %s/%s (facts: %s)",
            provider.domain,
            provider.name,
            provider.fact_types,
        )

    def get(self, domain: str, name: str) -> FactProvider:
        """Get a registered fact provider.

        Args:
            domain: Domain identifier.
            name: Provider name.

        Returns:
            The registered fact provider.

        Raises:
            PluginNotFoundError: If no provider is registered for the key.
        """
        key = (domain, name)
        if key not in self._providers:
            raise PluginNotFoundError("FactProvider", f"{domain}/{name}")
        return self._providers[key]

    def get_for_fact_type(self, fact_type: str) -> list[FactProvider]:
        """Get all providers that supply a given fact type.

        Args:
            fact_type: Fact type to match.

        Returns:
            List of providers supporting that fact type.
        """
        return [p for p in self._providers.values() if fact_type in p.fact_types]

    def list_all(self) -> list[FactProvider]:
        """Return all registered fact providers."""
        return list(self._providers.values())


class PersonaViewRegistry:
    """Registry for persona views, keyed by (domain, name)."""

    def __init__(self) -> None:
        self._views: dict[tuple[str, str], PersonaView] = {}

    def register(self, view: PersonaView) -> None:
        """Register a persona view.

        Args:
            view: The persona view to register.

        Raises:
            DuplicateRegistrationError: If a view with the same
                (domain, name) is already registered.
        """
        key = (view.domain, view.name)
        if key in self._views:
            raise DuplicateRegistrationError("PersonaViewRegistry", f"{key[0]}/{key[1]}")
        self._views[key] = view
        logger.info("Registered persona view: %s/%s", view.domain, view.name)

    def get(self, domain: str, name: str) -> PersonaView:
        """Get a registered persona view.

        Args:
            domain: Domain identifier.
            name: View name.

        Returns:
            The registered persona view.

        Raises:
            PluginNotFoundError: If no view is registered for the key.
        """
        key = (domain, name)
        if key not in self._views:
            raise PluginNotFoundError("PersonaView", f"{domain}/{name}")
        return self._views[key]

    def get_for_domain(self, domain: str) -> list[PersonaView]:
        """Get all persona views for a domain.

        Args:
            domain: Domain identifier.

        Returns:
            List of persona views for the domain.
        """
        return [v for (d, _), v in self._views.items() if d == domain]

    def list_all(self) -> list[PersonaView]:
        """Return all registered persona views."""
        return list(self._views.values())


class PluginRegistry:
    """Top-level registry holding all sub-registries and loaded plugins.

    This is the single entry point for the core to discover plugin
    capabilities. The core accesses evaluators, extractors, and other
    components exclusively through this registry.
    """

    def __init__(self) -> None:
        self.evaluators = EvaluatorRegistry()
        self.extractors = ExtractorRegistry()
        self.feedback = FeedbackRegistry()
        self.fact_providers = FactProviderRegistry()
        self.persona_views = PersonaViewRegistry()
        self._plugins: dict[str, DomainPlugin] = {}

    def register_plugin(self, plugin: DomainPlugin) -> None:
        """Register a domain plugin and all its components.

        Discovers evaluators, extractors, feedback sources, fact providers,
        and persona views from the plugin and registers each in the
        appropriate sub-registry.

        Args:
            plugin: The domain plugin to register.

        Raises:
            DuplicateRegistrationError: If the plugin domain is already
                registered.
        """
        if plugin.domain in self._plugins:
            raise DuplicateRegistrationError("PluginRegistry", plugin.domain)

        self._plugins[plugin.domain] = plugin
        logger.info(
            "Loading plugin: %s (domain=%s) - %s",
            plugin.name,
            plugin.domain,
            plugin.description,
        )

        for evaluator in plugin.get_evaluators():
            self.evaluators.register(evaluator)

        for extractor in plugin.get_extractors():
            self.extractors.register(extractor)

        for source in plugin.get_feedback_sources():
            self.feedback.register(source)

        for provider in plugin.get_fact_providers():
            self.fact_providers.register(provider)

        for view in plugin.get_persona_views():
            self.persona_views.register(view)

        logger.info("Plugin loaded: %s", plugin.name)

    def get_plugin(self, domain: str) -> DomainPlugin:
        """Get a loaded plugin by domain.

        Args:
            domain: Domain identifier.

        Returns:
            The loaded plugin.

        Raises:
            PluginNotFoundError: If no plugin is loaded for the domain.
        """
        if domain not in self._plugins:
            raise PluginNotFoundError("Plugin", domain)
        return self._plugins[domain]

    def list_plugins(self) -> list[DomainPlugin]:
        """Return all loaded plugins."""
        return list(self._plugins.values())

    def list_domains(self) -> list[str]:
        """Return all registered domain identifiers."""
        return list(self._plugins.keys())

    def summary(self) -> dict[str, Any]:
        """Return a summary of all registered components.

        Returns:
            Dict with counts and listings of all plugin components.
        """
        return {
            "plugins": [
                {
                    "name": p.name,
                    "domain": p.domain,
                    "description": p.description,
                }
                for p in self._plugins.values()
            ],
            "evaluators": [
                {"domain": e.domain, "name": e.name, "subjects": e.supported_subject_kinds}
                for e in self.evaluators.list_all()
            ],
            "extractors": [
                {"domain": e.domain, "name": e.name, "sources": e.supported_source_types}
                for e in self.extractors.list_all()
            ],
            "feedback_sources": [{"domain": s.domain, "name": s.name} for s in self.feedback.list_all()],
            "fact_providers": [
                {"domain": p.domain, "name": p.name, "facts": p.fact_types} for p in self.fact_providers.list_all()
            ],
            "persona_views": [
                {"domain": v.domain, "name": v.name, "route_group": v.route_group}
                for v in self.persona_views.list_all()
            ],
        }
