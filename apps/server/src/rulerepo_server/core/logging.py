"""Structured logging configuration using structlog."""

import logging
import sys

import structlog

from rulerepo_server.core.config import get_settings


def setup_logging() -> None:
    """Configure structlog with JSON output for production use."""
    settings = get_settings()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger instance.

    Args:
        name: Optional logger name for context.

    Returns:
        A structlog bound logger.
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
