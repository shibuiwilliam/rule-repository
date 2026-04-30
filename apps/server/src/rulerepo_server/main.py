"""FastAPI application factory for the Rule Repository server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.errors import RuleRepoError
from rulerepo_server.core.logging import get_logger, setup_logging
from rulerepo_server.core.middleware import RequestIdMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Initializes database connections, search clients, and graph driver
    on startup, and tears them down on shutdown.
    """
    setup_logging()
    settings = get_settings()
    logger.info("starting_server", host=settings.server_host, port=settings.server_port)

    # Import adapters lazily to avoid import-time side effects
    from rulerepo_server.adapters.elasticsearch.client import (
        close_es_client,
        create_es_client,
    )
    from rulerepo_server.adapters.neo4j.client import close_neo4j_driver, create_neo4j_driver
    from rulerepo_server.adapters.postgres.session import create_engine, dispose_engine

    # Initialize connections
    create_engine()
    await create_es_client()
    await create_neo4j_driver()
    logger.info("all_connections_initialized")

    yield

    # Teardown
    logger.info("shutting_down")
    await close_neo4j_driver()
    await close_es_client()
    await dispose_engine()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Rule Repository",
        description=(
            "A platform for managing, searching, serving, and enforcing "
            "natural-language rules using LLMs and AI agents."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware (outermost first) ---
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # --- Exception handlers ---

    @app.exception_handler(RuleRepoError)
    async def rulerepo_error_handler(request: Request, exc: RuleRepoError) -> JSONResponse:
        """Handle application-level errors with structured JSON responses."""
        logger.warning(
            "application_error",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unexpected errors — log and return 500."""
        logger.error(
            "unhandled_error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
        )

    # --- Health checks ---

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        """Lightweight liveness probe — always returns ok if the process is running."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> dict[str, object]:
        """Readiness probe — checks connectivity to all downstream services."""
        checks: dict[str, str] = {}
        healthy = True

        # Postgres
        try:
            from rulerepo_server.adapters.postgres.session import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
            healthy = False

        # Elasticsearch
        try:
            from rulerepo_server.adapters.elasticsearch.client import get_es_client

            es = get_es_client()
            await es.info()
            checks["elasticsearch"] = "ok"
        except Exception as exc:
            checks["elasticsearch"] = f"error: {exc}"
            healthy = False

        # Neo4j
        try:
            from rulerepo_server.adapters.neo4j.client import get_neo4j_driver

            driver = get_neo4j_driver()
            await driver.verify_connectivity()
            checks["neo4j"] = "ok"
        except Exception as exc:
            checks["neo4j"] = f"error: {exc}"
            healthy = False

        return {
            "status": "ok" if healthy else "degraded",
            "checks": checks,
        }

    # --- Register API routers ---
    from rulerepo_server.api.v1 import v1_router
    from rulerepo_server.gateway.router import router as gateway_router
    from rulerepo_server.integrations.github.router import router as github_router

    app.include_router(v1_router)
    app.include_router(gateway_router, prefix="/api/v1")
    app.include_router(github_router, prefix="/api/v1")

    return app


app = create_app()
