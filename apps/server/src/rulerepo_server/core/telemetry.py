"""OpenTelemetry setup for distributed tracing and metrics.

This module provides graceful degradation: if opentelemetry packages
are not installed, all functions become no-ops. This allows the
application to run without observability infrastructure during
local development.

To enable telemetry, install the required packages:
    uv add opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

Configuration is driven by environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    OTEL_SERVICE_NAME: Override service name (default: rulerepo-server)
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_OTEL_AVAILABLE = False
_tracer_provider: Any = None
_meter_provider: Any = None

# Pre-defined metric instruments (populated by init_telemetry)
evaluation_counter: Any = None
evaluation_latency: Any = None
llm_call_counter: Any = None
llm_token_counter: Any = None
llm_cost_gauge: Any = None
cache_hit_counter: Any = None
rule_count_gauge: Any = None
connector_health_gauge: Any = None

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:
    pass


class _NoOpSpan:
    """Minimal no-op span for use when OpenTelemetry is not installed."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op attribute setter."""

    def set_status(self, status: Any) -> None:
        """No-op status setter."""

    def record_exception(self, exception: BaseException) -> None:
        """No-op exception recorder."""


class _NoOpTracer:
    """Minimal no-op tracer for use when OpenTelemetry is not installed."""

    def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        """Return a no-op span.

        Args:
            name: Span name (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            A no-op span context manager.
        """
        return _NoOpSpan()

    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        """Return a no-op span as context manager.

        Args:
            name: Span name (ignored).
            **kwargs: Additional arguments (ignored).

        Returns:
            A no-op span context manager.
        """
        return _NoOpSpan()


class _NoOpMetricInstrument:
    """No-op metric instrument when OpenTelemetry is unavailable."""

    def add(self, amount: int | float, attributes: dict[str, str] | None = None) -> None:
        """No-op add."""

    def record(self, amount: int | float, attributes: dict[str, str] | None = None) -> None:
        """No-op record."""

    def set(self, amount: int | float, attributes: dict[str, str] | None = None) -> None:
        """No-op set (for observable gauges this is a callback, but we keep it simple)."""


class _NoOpMeter:
    """No-op meter when OpenTelemetry is unavailable."""

    def create_counter(self, name: str, **kwargs: Any) -> _NoOpMetricInstrument:
        """Return a no-op counter."""
        return _NoOpMetricInstrument()

    def create_histogram(self, name: str, **kwargs: Any) -> _NoOpMetricInstrument:
        """Return a no-op histogram."""
        return _NoOpMetricInstrument()

    def create_up_down_counter(self, name: str, **kwargs: Any) -> _NoOpMetricInstrument:
        """Return a no-op up-down counter."""
        return _NoOpMetricInstrument()

    def create_observable_gauge(self, name: str, **kwargs: Any) -> _NoOpMetricInstrument:
        """Return a no-op observable gauge."""
        return _NoOpMetricInstrument()


def init_telemetry(service_name: str = "rulerepo-server", otlp_endpoint: str | None = None) -> None:
    """Initialize OpenTelemetry tracing and metrics with OTLP exporter.

    Sets up tracer and meter providers, configures OTLP export, and creates
    all pre-defined metric instruments for the Rule Repository.

    If opentelemetry packages are not installed, this function logs a
    warning and creates no-op instruments so callers can operate without
    guards.

    Args:
        service_name: The service name to report in traces and metrics.
        otlp_endpoint: OTLP collector endpoint. If None, uses the
            OTEL_EXPORTER_OTLP_ENDPOINT environment variable default.
    """
    global _tracer_provider, _meter_provider
    global evaluation_counter, evaluation_latency
    global llm_call_counter, llm_token_counter, llm_cost_gauge
    global cache_hit_counter, rule_count_gauge, connector_health_gauge

    if not _OTEL_AVAILABLE:
        logger.info(
            "OpenTelemetry packages not installed. "
            "Telemetry is disabled. Install opentelemetry-api, "
            "opentelemetry-sdk, and opentelemetry-exporter-otlp to enable."
        )
        # Create no-op instruments so callers never need to check
        noop = _NoOpMeter()
        evaluation_counter = noop.create_counter("evaluation_counter")
        evaluation_latency = noop.create_histogram("evaluation_latency")
        llm_call_counter = noop.create_counter("llm_call_counter")
        llm_token_counter = noop.create_counter("llm_token_counter")
        llm_cost_gauge = noop.create_up_down_counter("llm_cost_gauge")
        cache_hit_counter = noop.create_counter("cache_hit_counter")
        rule_count_gauge = noop.create_up_down_counter("rule_count_gauge")
        connector_health_gauge = noop.create_up_down_counter("connector_health_gauge")
        return

    resource = Resource.create({"service.name": service_name})

    # Trace provider
    exporter_kwargs: dict[str, Any] = {}
    if otlp_endpoint:
        exporter_kwargs["endpoint"] = otlp_endpoint

    _tracer_provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter(**exporter_kwargs)
    _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
    trace.set_tracer_provider(_tracer_provider)

    # Meter provider
    otlp_metric_exporter = OTLPMetricExporter(**exporter_kwargs)
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=30000)
    _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(_meter_provider)

    # Create pre-defined instruments
    meter = metrics.get_meter(service_name)

    evaluation_counter = meter.create_counter(
        name="rulerepo.evaluations.total",
        description="Total evaluations by domain, verdict, and tenant",
        unit="1",
    )
    evaluation_latency = meter.create_histogram(
        name="rulerepo.evaluations.latency",
        description="Evaluation latency in milliseconds",
        unit="ms",
    )
    llm_call_counter = meter.create_counter(
        name="rulerepo.llm.calls.total",
        description="Total LLM calls by model and domain",
        unit="1",
    )
    llm_token_counter = meter.create_counter(
        name="rulerepo.llm.tokens.total",
        description="Total tokens consumed by model and direction",
        unit="1",
    )
    llm_cost_gauge = meter.create_counter(
        name="rulerepo.llm.cost.usd",
        description="Cumulative LLM cost in USD",
        unit="usd",
    )
    cache_hit_counter = meter.create_counter(
        name="rulerepo.cache.events.total",
        description="Cache hit and miss events",
        unit="1",
    )
    rule_count_gauge = meter.create_up_down_counter(
        name="rulerepo.rules.active",
        description="Active rules by domain and tenant",
        unit="1",
    )
    connector_health_gauge = meter.create_up_down_counter(
        name="rulerepo.connectors.health",
        description="Connector health status (1=healthy, 0=unhealthy)",
        unit="1",
    )

    logger.info(
        "OpenTelemetry tracing and metrics initialized for service=%s",
        service_name,
    )


# Backwards-compatible alias
setup_telemetry = init_telemetry


def get_tracer(name: str) -> Any:
    """Return a tracer instance for the given module name.

    If OpenTelemetry is not installed, returns a no-op tracer
    that silently ignores all tracing calls.

    Args:
        name: The name of the module requesting a tracer,
              typically __name__.

    Returns:
        An OpenTelemetry Tracer if available, otherwise a no-op tracer.
    """
    if _OTEL_AVAILABLE and _tracer_provider is not None:
        return trace.get_tracer(name)
    return _NoOpTracer()


def get_meter(name: str) -> Any:
    """Return a meter instance for the given module name.

    If OpenTelemetry is not installed, returns a no-op meter
    that silently ignores all metric recording calls.

    Args:
        name: The name of the module requesting a meter,
              typically __name__.

    Returns:
        An OpenTelemetry Meter if available, otherwise a no-op meter.
    """
    if _OTEL_AVAILABLE and _meter_provider is not None:
        return metrics.get_meter(name)
    return _NoOpMeter()


def trace_llm_call(
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    domain: str,
    tenant_id: str,
) -> None:
    """Record telemetry for a single LLM call.

    Updates counters for LLM calls, token usage, and cost estimation.
    This is the canonical entry point for LLM observability; all
    adapters should call this after each LLM interaction.

    Args:
        model: Model identifier (e.g. ``gemini-3-flash-preview``).
        tokens_in: Number of input tokens consumed.
        tokens_out: Number of output tokens generated.
        latency_ms: Wall-clock latency in milliseconds.
        domain: Business domain of the call (e.g. ``evaluation``, ``extraction``).
        tenant_id: Tenant or organization identifier.
    """
    if llm_call_counter is None:
        return

    attrs = {"model": model, "domain": domain, "tenant_id": tenant_id}
    llm_call_counter.add(1, attributes=attrs)

    llm_token_counter.add(tokens_in, attributes={**attrs, "direction": "input"})
    llm_token_counter.add(tokens_out, attributes={**attrs, "direction": "output"})

    # Rough cost estimation per model (USD per 1M tokens)
    cost_per_million: dict[str, dict[str, float]] = {
        "gemini-3-flash-preview": {"input": 0.10, "output": 0.40},
        "gemini-3.1-pro-preview": {"input": 1.25, "output": 5.00},
    }
    rates = cost_per_million.get(model, {"input": 0.50, "output": 2.00})
    cost = (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000
    llm_cost_gauge.add(cost, attributes=attrs)


def trace_evaluation(
    domain: str,
    verdict: str,
    latency_ms: float,
    tenant_id: str,
    rules_count: int,
) -> None:
    """Record telemetry for a completed evaluation.

    Args:
        domain: Subject domain (e.g. ``code_diff``, ``clause_set``).
        verdict: Outcome verdict (e.g. ``pass``, ``fail``, ``warn``).
        latency_ms: Total evaluation latency in milliseconds.
        tenant_id: Tenant or organization identifier.
        rules_count: Number of rules evaluated in this run.
    """
    if evaluation_counter is None:
        return

    attrs = {"domain": domain, "verdict": verdict, "tenant_id": tenant_id}
    evaluation_counter.add(1, attributes=attrs)
    evaluation_latency.record(latency_ms, attributes={"domain": domain, "tenant_id": tenant_id})


def current_time_ms() -> float:
    """Return current monotonic time in milliseconds for latency measurement."""
    return time.monotonic() * 1000
