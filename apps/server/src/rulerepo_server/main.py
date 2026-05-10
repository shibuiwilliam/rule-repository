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
from rulerepo_server.core.pii_middleware import PIIScrubMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown.

    Initializes database connections and, depending on the deployment
    tier, search clients and graph drivers.  Tier 1 (Postgres-only)
    skips Elasticsearch and Neo4j entirely.
    """
    setup_logging()
    settings = get_settings()

    from rulerepo_server.core.feature_flags import get_feature_flags

    flags = get_feature_flags()
    flags.log_tier_info()

    logger.info(
        "starting_server",
        host=settings.server_host,
        port=settings.server_port,
        tier=flags.tier,
    )

    # Import adapters lazily to avoid import-time side effects
    from rulerepo_server.adapters.postgres.session import create_engine, dispose_engine

    # Postgres is always required
    create_engine()

    # Elasticsearch — Tier 2/3 only
    if flags.elasticsearch_enabled:
        from rulerepo_server.adapters.elasticsearch.client import create_es_client

        await create_es_client()
        logger.info("elasticsearch_initialized")
    else:
        logger.info("elasticsearch_disabled", fallback="postgres_fts")

    # Neo4j — Tier 3 only
    if flags.neo4j_enabled:
        from rulerepo_server.adapters.neo4j.client import create_neo4j_driver

        await create_neo4j_driver()
        logger.info("neo4j_initialized")
    else:
        logger.info("neo4j_disabled", fallback="postgres_adjacency")

    logger.info("all_connections_initialized", tier=flags.tier)

    yield

    # Teardown
    logger.info("shutting_down")

    if flags.neo4j_enabled:
        from rulerepo_server.adapters.neo4j.client import close_neo4j_driver

        await close_neo4j_driver()

    if flags.elasticsearch_enabled:
        from rulerepo_server.adapters.elasticsearch.client import close_es_client

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
    app.add_middleware(PIIScrubMiddleware)
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
        """Readiness probe — checks connectivity to downstream services.

        Only checks services that are enabled for the current tier.
        Tier 1 checks Postgres only; Tier 2 adds Elasticsearch;
        Tier 3 adds Neo4j.
        """
        from rulerepo_server.core.feature_flags import get_feature_flags

        flags = get_feature_flags()
        checks: dict[str, str] = {}
        healthy = True

        # Postgres — always required
        try:
            from rulerepo_server.adapters.postgres.session import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
            healthy = False

        # Elasticsearch — Tier 2/3 only
        if flags.elasticsearch_enabled:
            try:
                from rulerepo_server.adapters.elasticsearch.client import get_es_client

                es = get_es_client()
                await es.info()
                checks["elasticsearch"] = "ok"
            except Exception as exc:
                checks["elasticsearch"] = f"error: {exc}"
                healthy = False
        else:
            checks["elasticsearch"] = "disabled (tier 1)"

        # Neo4j — Tier 3 only
        if flags.neo4j_enabled:
            try:
                from rulerepo_server.adapters.neo4j.client import get_neo4j_driver

                driver = get_neo4j_driver()
                await driver.verify_connectivity()
                checks["neo4j"] = "ok"
            except Exception as exc:
                checks["neo4j"] = f"error: {exc}"
                healthy = False
        else:
            checks["neo4j"] = "disabled (tier 1/2)"

        return {
            "status": "ok" if healthy else "degraded",
            "checks": checks,
            "tier": flags.tier,
        }

    # --- Register API routers ---
    from rulerepo_server.api.v1 import v1_router
    from rulerepo_server.core.feature_flags import get_feature_flags
    from rulerepo_server.gateway.router import router as gateway_router

    app.include_router(v1_router)
    app.include_router(gateway_router, prefix="/api/v1")

    # GitHub App webhook — only registered when enabled
    flags = get_feature_flags()
    if flags.github_app_enabled:
        from rulerepo_server.integrations.github.router import router as github_router

        app.include_router(github_router, prefix="/api/v1")

    return app


app = create_app()
