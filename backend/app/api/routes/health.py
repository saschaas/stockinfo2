"""Health check API routes for data sources."""

import asyncio
from typing import Any

from fastapi import APIRouter
import structlog
import httpx
from sqlalchemy import text

from backend.app.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


async def check_database() -> dict[str, Any]:
    """Check database connectivity."""
    try:
        from backend.app.db.session import async_session_factory

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))

        return {
            "name": "PostgreSQL Database",
            "status": "healthy",
            "message": "Connected successfully",
        }
    except Exception as e:
        return {
            "name": "PostgreSQL Database",
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        from backend.app.celery_app import celery_app

        # Try to ping Redis through Celery
        inspector = celery_app.control.inspect()
        stats = inspector.stats()

        if stats:
            return {
                "name": "Redis Cache",
                "status": "healthy",
                "message": "Connected successfully",
            }
        else:
            return {
                "name": "Redis Cache",
                "status": "degraded",
                "message": "Connected but no workers available",
            }
    except Exception as e:
        return {
            "name": "Redis Cache",
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }


async def check_celery() -> dict[str, Any]:
    """Check Celery worker status."""
    try:
        from backend.app.celery_app import celery_app

        inspector = celery_app.control.inspect()
        active = inspector.active()

        if active:
            worker_count = len(active)
            return {
                "name": "Celery Workers",
                "status": "healthy",
                "message": f"{worker_count} worker(s) active",
                "workers": worker_count,
            }
        else:
            return {
                "name": "Celery Workers",
                "status": "unhealthy",
                "message": "No workers available",
            }
    except Exception as e:
        return {
            "name": "Celery Workers",
            "status": "unhealthy",
            "message": f"Check failed: {str(e)}",
        }


async def check_ollama() -> dict[str, Any]:
    """Check Ollama LLM service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if Ollama is running
            response = await client.get("http://ollama:11434/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                # Check if required model is available
                model_name = "llama3.2"  # From config
                has_model = any(model.get("name", "").startswith(model_name) for model in models)

                if has_model:
                    return {
                        "name": "Ollama LLM",
                        "status": "healthy",
                        "message": f"Service running with {len(models)} model(s)",
                        "models": [m.get("name") for m in models],
                    }
                else:
                    return {
                        "name": "Ollama LLM",
                        "status": "degraded",
                        "message": f"Service running but model '{model_name}' not found",
                        "models": [m.get("name") for m in models],
                    }
            else:
                return {
                    "name": "Ollama LLM",
                    "status": "unhealthy",
                    "message": f"HTTP {response.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "name": "Ollama LLM",
            "status": "unhealthy",
            "message": "Request timeout (5s)",
        }
    except Exception as e:
        return {
            "name": "Ollama LLM",
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }


async def check_alpha_vantage() -> dict[str, Any]:
    """Check Alpha Vantage API."""
    if not settings.alpha_vantage_api_key:
        return {
            "name": "Alpha Vantage API",
            "status": "degraded",
            "message": "API key not configured",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Simple API test - get AAPL quote
            response = await client.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": "AAPL",
                    "apikey": settings.alpha_vantage_api_key,
                },
            )

            if response.status_code == 200:
                data = response.json()

                # Check for rate limit or error
                if "Note" in data:
                    return {
                        "name": "Alpha Vantage API",
                        "status": "degraded",
                        "message": "Rate limit reached",
                    }
                elif "Error Message" in data:
                    return {
                        "name": "Alpha Vantage API",
                        "status": "unhealthy",
                        "message": data["Error Message"],
                    }
                elif "Global Quote" in data:
                    return {
                        "name": "Alpha Vantage API",
                        "status": "healthy",
                        "message": "API responding correctly",
                    }
                else:
                    return {
                        "name": "Alpha Vantage API",
                        "status": "degraded",
                        "message": "Unexpected response format",
                    }
            else:
                return {
                    "name": "Alpha Vantage API",
                    "status": "unhealthy",
                    "message": f"HTTP {response.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "name": "Alpha Vantage API",
            "status": "unhealthy",
            "message": "Request timeout (5s)",
        }
    except Exception as e:
        return {
            "name": "Alpha Vantage API",
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }


async def check_yahoo_finance() -> dict[str, Any]:
    """Check Yahoo Finance API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test endpoint
            response = await client.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
                params={"interval": "1d", "range": "1d"},
            )

            if response.status_code == 200:
                return {
                    "name": "Yahoo Finance API",
                    "status": "healthy",
                    "message": "API responding correctly",
                }
            else:
                return {
                    "name": "Yahoo Finance API",
                    "status": "unhealthy",
                    "message": f"HTTP {response.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "name": "Yahoo Finance API",
            "status": "unhealthy",
            "message": "Request timeout (5s)",
        }
    except Exception as e:
        return {
            "name": "Yahoo Finance API",
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }


async def check_sec_edgar() -> dict[str, Any]:
    """Check SEC EDGAR API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test endpoint - get a sample CIK
            response = await client.get(
                "https://data.sec.gov/submissions/CIK0001067983.json",
                headers={"User-Agent": "StockInfo Research Tool contact@example.com"},
            )

            if response.status_code == 200:
                return {
                    "name": "SEC EDGAR API",
                    "status": "healthy",
                    "message": "API responding correctly",
                }
            elif response.status_code == 429:
                return {
                    "name": "SEC EDGAR API",
                    "status": "degraded",
                    "message": "Rate limit reached",
                }
            else:
                return {
                    "name": "SEC EDGAR API",
                    "status": "degraded",
                    "message": f"HTTP {response.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "name": "SEC EDGAR API",
            "status": "unhealthy",
            "message": "Request timeout (5s)",
        }
    except Exception as e:
        return {
            "name": "SEC EDGAR API",
            "status": "degraded",
            "message": f"Connection failed: {str(e)}",
        }


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check for all data sources and services.

    Returns status for:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Workers (Celery)
    - LLM (Ollama)
    - External APIs (Alpha Vantage, Yahoo Finance, SEC EDGAR)
    """
    logger.info("Running health check")

    # Run all checks concurrently
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_celery(),
        check_ollama(),
        check_alpha_vantage(),
        check_yahoo_finance(),
        check_sec_edgar(),
    )

    # Categorize results
    infrastructure = results[0:3]  # Database, Redis, Celery
    ai_services = [results[3]]  # Ollama
    external_apis = results[4:7]  # Alpha Vantage, Yahoo, SEC

    # Determine overall status
    statuses = [r["status"] for r in results]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "degraded"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": "2025-12-12T10:00:00Z",  # Will be replaced with actual timestamp
        "services": {
            "infrastructure": infrastructure,
            "ai_services": ai_services,
            "external_apis": external_apis,
        },
        "checks": results,
    }
