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
from typing import Any

logger = logging.getLogger(__name__)

_OTEL_AVAILABLE = False
_tracer_provider: Any = None

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
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


def setup_telemetry(service_name: str = "rulerepo-server") -> None:
    """Initialize OpenTelemetry tracing with OTLP exporter.

    If opentelemetry packages are not installed, this function
    logs a warning and returns silently. The application continues
    to function without tracing.

    Args:
        service_name: The service name to report in traces.
    """
    global _tracer_provider

    if not _OTEL_AVAILABLE:
        logger.info(
            "OpenTelemetry packages not installed. "
            "Telemetry is disabled. Install opentelemetry-api, "
            "opentelemetry-sdk, and opentelemetry-exporter-otlp to enable."
        )
        return

    resource = Resource.create({"service.name": service_name})
    _tracer_provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(otlp_exporter)
    _tracer_provider.add_span_processor(span_processor)

    trace.set_tracer_provider(_tracer_provider)

    logger.info("OpenTelemetry tracing initialized for service=%s", service_name)


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
