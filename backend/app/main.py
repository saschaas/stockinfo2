"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import market, stocks, funds, etfs, reports, websocket, health, config, websites
from backend.app.config import get_settings
from backend.app.core.exceptions import StockResearchException
from backend.app.db.session import close_db, init_db
from backend.app.services.cache import get_redis_client, close_redis

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.json_logs else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting Stock Research Tool API", environment=settings.environment)

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize Redis
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            logger.info("Redis connected")

        yield

    finally:
        # Shutdown
        logger.info("Shutting down Stock Research Tool API")
        await close_db()
        await close_redis()
        logger.info("Connections closed")


# Create FastAPI application
app = FastAPI(
    title="Stock Research Tool API",
    description="AI-Powered Stock Research Tool with fund tracking and analysis",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(StockResearchException)
async def stock_research_exception_handler(
    request: Request, exc: StockResearchException
) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.error(
        "Application error",
        error=exc.message,
        error_code=exc.error_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "suggestion": exc.suggestion,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    logger.warning(
        "Validation error",
        errors=exc.errors(),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(
        "Unexpected error",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
    }


# Readiness check endpoint
@app.get("/ready")
async def readiness_check() -> dict:
    """Readiness check endpoint with dependency verification."""
    checks = {
        "database": False,
        "redis": False,
    }

    try:
        # Check database
        from backend.app.db.session import async_session_factory
        async with async_session_factory() as session:
            await session.execute("SELECT 1")
            checks["database"] = True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))

    try:
        # Check Redis
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            checks["redis"] = True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["Stocks"])
app.include_router(funds.router, prefix="/api/v1/funds", tags=["Funds"])
app.include_router(etfs.router, prefix="/api/v1/etfs", tags=["ETFs"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(websites.router, prefix="/api/v1/websites", tags=["Websites"])


def run() -> None:
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
