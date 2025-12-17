"""Health check API routes for data sources."""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter
import structlog
import httpx
from sqlalchemy import text

from backend.app.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


# Data source configurations with descriptions and tab mappings
DATA_SOURCE_INFO = {
    "alpha_vantage": {
        "description": "Stock prices and technical indicators",
        "type": "api",
    },
    "yahoo_finance": {
        "description": "Stock fundamentals and backup price data",
        "type": "api",
    },
    "sec_edgar": {
        "description": "13F filings and institutional holdings",
        "type": "api",
    },
    "ollama": {
        "description": "AI-powered stock analysis",
        "type": "service",
    },
    "openfigi": {
        "description": "CUSIP to ticker symbol resolution",
        "type": "api",
    },
    "web_scraping": {
        "description": "Custom website scraping for market data",
        "type": "service",
    },
    "database": {
        "description": "PostgreSQL data storage",
        "type": "infrastructure",
    },
    "redis": {
        "description": "Caching and job queue",
        "type": "infrastructure",
    },
    "celery": {
        "description": "Background task processing",
        "type": "infrastructure",
    },
    "nordvpn": {
        "description": "VPN for external API requests",
        "type": "infrastructure",
    },
}

# Tab to data source mappings - supports configurable sources
TAB_DATA_MAPPINGS = {
    "Dashboard": {
        "data_types": [
            {"name": "Top Movers", "primary": "web_scraping", "fallback": None, "configurable": True, "config_category": "top_gainers,top_losers"},
            {"name": "Market Sentiment", "primary": "alpha_vantage", "fallback": "yahoo_finance", "configurable": False},
            {"name": "Sector Analysis", "primary": "alpha_vantage", "fallback": "web_scraping", "configurable": True, "config_category": "dashboard_sentiment"},
            {"name": "Market Summary", "primary": "web_scraping", "fallback": None, "configurable": True, "config_category": "dashboard_sentiment"},
            {"name": "News Feed", "primary": "alpha_vantage", "fallback": "web_scraping", "configurable": True, "config_category": "news"},
        ]
    },
    "Stock Research": {
        "data_types": [
            {"name": "Stock Prices", "primary": "alpha_vantage", "fallback": "yahoo_finance", "configurable": True},
            {"name": "Technical Indicators", "primary": "alpha_vantage", "fallback": None, "configurable": False},
            {"name": "Fundamentals", "primary": "yahoo_finance", "fallback": None, "configurable": False},
            {"name": "AI Analysis", "primary": "ollama", "fallback": None, "configurable": False},
            {"name": "Analyst Ratings", "primary": "yahoo_finance", "fallback": None, "configurable": True, "alternatives": ["web_scraping"]},
        ]
    },
    "Fund Tracker": {
        "data_types": [
            {"name": "13F Holdings", "primary": "sec_edgar", "fallback": None, "configurable": True, "alternatives": ["web_scraping"]},
            {"name": "Fund Holding Changes", "primary": "sec_edgar", "fallback": None, "configurable": True, "alternatives": ["web_scraping"]},
            {"name": "Ticker Resolution", "primary": "openfigi", "fallback": None, "configurable": False},
        ]
    },
    "ETF Tracker": {
        "data_types": [
            {"name": "ETF Holdings", "primary": "yahoo_finance", "fallback": None, "configurable": True, "alternatives": ["web_scraping"]},
            {"name": "ETF Holding Changes", "primary": "yahoo_finance", "fallback": None, "configurable": True, "alternatives": ["web_scraping"]},
        ]
    },
    "Watchlist": {
        "data_types": [
            {"name": "Price Updates", "primary": "yahoo_finance", "fallback": None, "configurable": False},
            {"name": "Saved Data", "primary": "database", "fallback": None, "configurable": False},
        ]
    },
}


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
            # Check if Ollama is running - use gateway IP since backend runs through VPN
            response = await client.get("http://172.18.0.1:11434/api/tags")

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
        # Yahoo Finance requires a browser-like User-Agent header
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
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


async def check_openfigi() -> dict[str, Any]:
    """Check OpenFIGI API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test with a known CUSIP (Apple)
            response = await client.post(
                "https://api.openfigi.com/v3/mapping",
                headers={"Content-Type": "application/json"},
                json=[{"idType": "ID_CUSIP", "idValue": "037833100"}],
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and "data" in data[0]:
                    return {
                        "name": "OpenFIGI API",
                        "status": "healthy",
                        "message": "API responding correctly",
                    }
                else:
                    return {
                        "name": "OpenFIGI API",
                        "status": "degraded",
                        "message": "Unexpected response format",
                    }
            elif response.status_code == 429:
                return {
                    "name": "OpenFIGI API",
                    "status": "degraded",
                    "message": "Rate limit reached",
                }
            else:
                return {
                    "name": "OpenFIGI API",
                    "status": "unhealthy",
                    "message": f"HTTP {response.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "name": "OpenFIGI API",
            "status": "unhealthy",
            "message": "Request timeout (5s)",
        }
    except Exception as e:
        return {
            "name": "OpenFIGI API",
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)}",
        }


async def check_web_scraping() -> dict[str, Any]:
    """Check web scraping capability (Playwright/browser availability)."""
    try:
        # Check if there are any configured scraped websites
        from backend.app.db.session import async_session_factory
        from backend.app.db.models import ScrapedWebsite
        from sqlalchemy import select, func

        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(ScrapedWebsite).where(ScrapedWebsite.is_active == True)
            result = await session.execute(stmt)
            active_count = result.scalar() or 0

        if active_count > 0:
            return {
                "name": "Web Scraping",
                "status": "healthy",
                "message": f"{active_count} active website(s) configured",
                "active_websites": active_count,
            }
        else:
            return {
                "name": "Web Scraping",
                "status": "degraded",
                "message": "No active websites configured",
                "active_websites": 0,
            }
    except Exception as e:
        return {
            "name": "Web Scraping",
            "status": "unknown",
            "message": f"Check failed: {str(e)}",
        }


async def check_nordvpn() -> dict[str, Any]:
    """Check NordVPN connection status."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check NordVPN API for connection status
            response = await client.get(
                "https://api.nordvpn.com/v1/helpers/ips/insights"
            )

            if response.status_code == 200:
                data = response.json()
                is_protected = data.get("protected", False)
                country = data.get("country", "Unknown")
                city = data.get("city", "Unknown")

                if is_protected:
                    return {
                        "name": "NordVPN",
                        "status": "healthy",
                        "message": f"Connected via {city}, {country}",
                        "protected": True,
                        "location": f"{city}, {country}",
                    }
                else:
                    return {
                        "name": "NordVPN",
                        "status": "unhealthy",
                        "message": "VPN not active - traffic not protected",
                        "protected": False,
                    }
            else:
                return {
                    "name": "NordVPN",
                    "status": "unhealthy",
                    "message": f"HTTP {response.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "name": "NordVPN",
            "status": "unhealthy",
            "message": "Request timeout (10s)",
        }
    except Exception as e:
        return {
            "name": "NordVPN",
            "status": "unhealthy",
            "message": f"Check failed: {str(e)}",
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
        check_nordvpn(),
        check_ollama(),
        check_alpha_vantage(),
        check_yahoo_finance(),
        check_sec_edgar(),
    )

    # Categorize results
    infrastructure = results[0:4]  # Database, Redis, Celery, NordVPN
    ai_services = [results[4]]  # Ollama
    external_apis = results[5:8]  # Alpha Vantage, Yahoo, SEC

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
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "infrastructure": infrastructure,
            "ai_services": ai_services,
            "external_apis": external_apis,
        },
        "checks": results,
    }


@router.get("/health/data-sources")
async def data_sources_overview() -> dict[str, Any]:
    """
    Get data sources overview for the Overview tab.

    Returns:
    - Status of all data sources with descriptions
    - Tab-to-source mappings with fallback information
    - Timestamp of when the check was performed
    """
    logger.info("Running data sources overview check")

    # Run all source checks concurrently
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_celery(),
        check_nordvpn(),
        check_ollama(),
        check_alpha_vantage(),
        check_yahoo_finance(),
        check_sec_edgar(),
        check_openfigi(),
        check_web_scraping(),
    )

    # Map results to source names
    source_checks = {
        "database": results[0],
        "redis": results[1],
        "celery": results[2],
        "nordvpn": results[3],
        "ollama": results[4],
        "alpha_vantage": results[5],
        "yahoo_finance": results[6],
        "sec_edgar": results[7],
        "openfigi": results[8],
        "web_scraping": results[9],
    }

    # Build sources dict with status and descriptions
    sources = {}
    for source_id, info in DATA_SOURCE_INFO.items():
        check_result = source_checks.get(source_id, {"status": "unknown", "message": "Not checked"})
        sources[source_id] = {
            "status": check_result["status"],
            "description": info["description"],
            "type": info["type"],
            "message": check_result.get("message", ""),
        }

    # Collect warnings for unavailable sources
    warnings = []
    for source_id, source_data in sources.items():
        if source_data["status"] == "unhealthy":
            # Find which tabs are affected
            affected_tabs = []
            for tab_name, tab_info in TAB_DATA_MAPPINGS.items():
                for data_type in tab_info["data_types"]:
                    if data_type["primary"] == source_id:
                        fallback = data_type.get("fallback")
                        has_fallback = fallback and sources.get(fallback, {}).get("status") == "healthy"
                        affected_tabs.append({
                            "tab": tab_name,
                            "data_type": data_type["name"],
                            "fallback": fallback,
                            "fallback_available": has_fallback,
                        })

            if affected_tabs:
                warnings.append({
                    "source": source_id,
                    "source_name": source_checks[source_id].get("name", source_id),
                    "message": source_data["message"],
                    "affected": affected_tabs,
                })

    return {
        "sources": sources,
        "tabs": TAB_DATA_MAPPINGS,
        "warnings": warnings,
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
