"""LLM fallback strategy and circuit breaker.

Handles LLM provider failures gracefully by returning cached results,
queuing retries, or failing with appropriate signals depending on the
severity of the originating evaluation.

The circuit breaker tracks consecutive failures per provider and
transitions through CLOSED -> OPEN -> HALF_OPEN states to prevent
cascading failures.

Usage::

    from rulerepo_server.services.operability.llm_fallback import llm_fallback_handler

    result = await llm_fallback_handler.handle_failure(
        error=exc,
        severity="high",
        original_request={"prompt": "...", "model": "gemini-3-flash-preview"},
    )
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class FallbackStrategy(StrEnum):
    """Strategy used when an LLM call fails."""

    CACHE_STALE = "cache_stale"
    QUEUE_RETRY = "queue_retry"
    FAIL_OPEN = "fail_open"
    FAIL_CLOSED = "fail_closed"


class CircuitState(StrEnum):
    """Circuit breaker state."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class FallbackResult:
    """Outcome of a fallback handling attempt.

    Attributes:
        strategy_used: The fallback strategy that was applied.
        result: The cached or synthesized result, if available.
        stale: True if the result came from a stale cache entry.
        retry_queued: True if the request was queued for later retry.
        message: Human-readable description of what happened.
    """

    strategy_used: FallbackStrategy
    result: dict | None
    stale: bool
    retry_queued: bool
    message: str


@dataclass(frozen=True)
class CircuitBreakerStatus:
    """Current state of a circuit breaker for a provider.

    Attributes:
        provider: The LLM provider name.
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN).
        failure_count: Number of consecutive failures.
        last_failure_at: Timestamp of the last failure, or None.
        next_retry_at: Timestamp when HALF_OPEN probe will be attempted.
    """

    provider: str
    state: CircuitState
    failure_count: int
    last_failure_at: float | None
    next_retry_at: float | None


@dataclass
class _CircuitBreaker:
    """Internal circuit breaker state for a single provider."""

    provider: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: float | None = None
    last_success_at: float | None = None
    # Configuration
    failure_threshold: int = 5
    recovery_timeout_s: float = 60.0
    half_open_max_calls: int = 3

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_at = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                provider=self.provider,
                failure_count=self.failure_count,
            )

    def record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        self.success_count += 1
        self.last_success_at = time.time()

        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("circuit_breaker_closed", provider=self.provider)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def should_allow_request(self) -> bool:
        """Check whether a request should be allowed through."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_at is None:
                return True
            elapsed = time.time() - self.last_failure_at
            if elapsed >= self.recovery_timeout_s:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("circuit_breaker_half_open", provider=self.provider)
                return True
            return False

        # HALF_OPEN: allow limited probes
        return True

    @property
    def next_retry_at(self) -> float | None:
        """Compute the next retry timestamp if circuit is open."""
        if self.state != CircuitState.OPEN or self.last_failure_at is None:
            return None
        return self.last_failure_at + self.recovery_timeout_s

    def to_status(self) -> CircuitBreakerStatus:
        """Convert to an external status representation."""
        return CircuitBreakerStatus(
            provider=self.provider,
            state=self.state,
            failure_count=self.failure_count,
            last_failure_at=self.last_failure_at,
            next_retry_at=self.next_retry_at,
        )


class LLMFallbackHandler:
    """Handles LLM call failures with fallback strategies and circuit breaking.

    For non-CRITICAL evaluations, returns stale cached results when
    available. For CRITICAL evaluations or when no cache exists, queues
    the request for retry and returns a ``NEEDS_CONFIRMATION`` signal.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._breakers: dict[str, _CircuitBreaker] = {}
        # In-memory stale cache: key -> result dict
        self._stale_cache: dict[str, dict] = {}
        # Retry queue: request_id -> original request
        self._retry_queue: dict[str, dict] = {}

    def _get_breaker(self, provider: str) -> _CircuitBreaker:
        """Get or create a circuit breaker for a provider."""
        with self._lock:
            if provider not in self._breakers:
                self._breakers[provider] = _CircuitBreaker(provider=provider)
            return self._breakers[provider]

    def cache_result(self, cache_key: str, result: dict) -> None:
        """Store a successful result for potential stale fallback.

        Args:
            cache_key: Unique key for the request (e.g. hash of inputs).
            result: The successful LLM result to cache.
        """
        with self._lock:
            self._stale_cache[cache_key] = result

    def record_success(self, provider: str) -> None:
        """Record a successful LLM call for circuit breaker tracking.

        Args:
            provider: The LLM provider name.
        """
        breaker = self._get_breaker(provider)
        with self._lock:
            breaker.record_success()

    async def handle_failure(
        self,
        error: Exception,
        severity: str,
        original_request: dict,
        cache_key: str | None = None,
        provider: str = "gemini",
    ) -> FallbackResult:
        """Handle an LLM call failure with the appropriate fallback strategy.

        Decision logic:
        - If severity is not CRITICAL and a cached result exists: return stale cache.
        - If severity is CRITICAL: queue for retry, return NEEDS_CONFIRMATION.
        - If no cache exists for non-CRITICAL: queue for retry.

        Args:
            error: The exception that caused the failure.
            severity: Evaluation severity (e.g. ``low``, ``medium``, ``high``, ``critical``).
            original_request: The original request payload for potential retry.
            cache_key: Optional cache key to look up stale results.
            provider: The LLM provider name for circuit breaker tracking.

        Returns:
            A FallbackResult describing the fallback action taken.
        """
        breaker = self._get_breaker(provider)
        with self._lock:
            breaker.record_failure()

        is_critical = severity.lower() == "critical"
        error_msg = str(error)

        logger.warning(
            "llm_call_failed",
            provider=provider,
            severity=severity,
            error=error_msg,
            circuit_state=breaker.state,
        )

        # Try stale cache for non-critical requests
        if not is_critical and cache_key:
            with self._lock:
                cached = self._stale_cache.get(cache_key)
            if cached is not None:
                logger.info(
                    "fallback_stale_cache",
                    cache_key=cache_key,
                    severity=severity,
                )
                return FallbackResult(
                    strategy_used=FallbackStrategy.CACHE_STALE,
                    result=cached,
                    stale=True,
                    retry_queued=False,
                    message=f"Returned stale cached result due to LLM failure: {error_msg}",
                )

        # Queue for retry
        request_id = str(uuid.uuid4())
        with self._lock:
            self._retry_queue[request_id] = {
                "request_id": request_id,
                "original_request": original_request,
                "severity": severity,
                "provider": provider,
                "error": error_msg,
                "queued_at": time.time(),
            }

        strategy = FallbackStrategy.FAIL_CLOSED if is_critical else FallbackStrategy.QUEUE_RETRY
        message = (
            f"CRITICAL evaluation queued for retry (id={request_id}). Manual confirmation required. Error: {error_msg}"
            if is_critical
            else f"Evaluation queued for retry (id={request_id}). Error: {error_msg}"
        )

        return FallbackResult(
            strategy_used=strategy,
            result=None,
            stale=False,
            retry_queued=True,
            message=message,
        )

    async def retry_queued(self, request_id: str) -> dict | None:
        """Retrieve a queued request for retry.

        Args:
            request_id: The ID returned by ``handle_failure``.

        Returns:
            The original request payload, or None if not found.
        """
        with self._lock:
            entry = self._retry_queue.pop(request_id, None)
        if entry is None:
            return None
        return entry.get("original_request")

    def get_circuit_breaker_status(self, provider: str) -> CircuitBreakerStatus:
        """Return the current circuit breaker status for a provider.

        Args:
            provider: The LLM provider name.

        Returns:
            A CircuitBreakerStatus snapshot.
        """
        breaker = self._get_breaker(provider)
        with self._lock:
            return breaker.to_status()

    def get_all_circuit_breaker_statuses(self) -> list[CircuitBreakerStatus]:
        """Return circuit breaker statuses for all known providers.

        Returns:
            A list of CircuitBreakerStatus objects.
        """
        with self._lock:
            return [b.to_status() for b in self._breakers.values()]

    def is_provider_available(self, provider: str) -> bool:
        """Check whether a provider's circuit breaker allows requests.

        Args:
            provider: The LLM provider name.

        Returns:
            True if the circuit is closed or half-open and accepting probes.
        """
        breaker = self._get_breaker(provider)
        with self._lock:
            return breaker.should_allow_request()


# Module-level singleton
llm_fallback_handler = LLMFallbackHandler()
