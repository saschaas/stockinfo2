"""Configuration API routes."""

import os
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.app.config import get_settings
from backend.app.db.models import UserConfig
from backend.app.db.session import async_session_factory
import httpx

from backend.app.schemas.config import (
    ConfigResponse,
    ConfigSettings,
    TestAPIKeyRequest,
    TestAPIKeyResponse,
    AIModelSettings,
    DisplayPreferences,
    MarketScrapingSettings,
    VPNStatus,
    DATA_USE_CATEGORIES,
    DATA_USE_DISPLAY_NAMES,
)

router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()


async def _get_vpn_status() -> VPNStatus:
    """Get current VPN connection status."""
    # Check if VPN mode is enabled via environment variable
    vpn_enabled = os.getenv("VPN_ENABLED", "true").lower() != "false"

    if not vpn_enabled:
        return VPNStatus(
            enabled=False,
            connected=False,
            location=None,
            message="VPN mode disabled in configuration",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.nordvpn.com/v1/helpers/ips/insights"
            )

            if response.status_code == 200:
                data = response.json()
                is_protected = data.get("protected", False)
                country = data.get("country", "Unknown")
                city = data.get("city", "Unknown")

                if is_protected:
                    return VPNStatus(
                        enabled=True,
                        connected=True,
                        location=f"{city}, {country}",
                        message=f"Connected via {city}, {country}",
                    )
                else:
                    return VPNStatus(
                        enabled=True,
                        connected=False,
                        location=None,
                        message="VPN enabled but not connected",
                    )
            else:
                return VPNStatus(
                    enabled=True,
                    connected=False,
                    location=None,
                    message=f"Could not verify VPN status (HTTP {response.status_code})",
                )
    except httpx.TimeoutException:
        return VPNStatus(
            enabled=True,
            connected=False,
            location=None,
            message="VPN status check timed out",
        )
    except Exception as e:
        return VPNStatus(
            enabled=True,
            connected=False,
            location=None,
            message=f"VPN status check failed: {str(e)}",
        )


async def _get_config_value(key: str) -> Optional[dict]:
    """Get configuration value from database."""
    async with async_session_factory() as session:
        stmt = select(UserConfig).where(UserConfig.config_key == key)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()
        return config.config_value if config else None


async def _set_config_value(key: str, value: dict, description: str = "") -> None:
    """Set configuration value in database (upsert)."""
    async with async_session_factory() as session:
        stmt = insert(UserConfig).values(
            config_key=key,
            config_value=value,
            description=description,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["config_key"],
            set_={"config_value": value, "description": description},
        )
        await session.execute(stmt)
        await session.commit()


@router.get("/settings", response_model=ConfigResponse)
async def get_config_settings() -> ConfigResponse:
    """
    Get all user configuration settings.

    Returns current configuration including AI models, display preferences,
    and market scraping settings. Also returns flags indicating which API
    keys are configured (but not the keys themselves).
    """
    try:
        # Load AI model settings
        ai_models_data = await _get_config_value("ai_models")
        ai_models = AIModelSettings(**ai_models_data) if ai_models_data else AIModelSettings()

        # Load display preferences
        display_data = await _get_config_value("display_preferences")
        display_preferences = DisplayPreferences(**display_data) if display_data else DisplayPreferences()

        # Load market scraping settings
        scraping_data = await _get_config_value("market_scraping")
        market_scraping = MarketScrapingSettings(**scraping_data) if scraping_data else MarketScrapingSettings()

        # Check if API keys are configured (don't return the actual keys)
        has_alpha_vantage = bool(settings.alpha_vantage_api_key)
        has_fmp = bool(settings.fmp_api_key)
        has_sec_agent = bool(settings.sec_user_agent)

        # Get VPN status
        vpn_status = await _get_vpn_status()

        return ConfigResponse(
            settings=ConfigSettings(
                ai_models=ai_models,
                display_preferences=display_preferences,
                market_scraping=market_scraping,
            ),
            has_alpha_vantage_key=has_alpha_vantage,
            has_fmp_key=has_fmp,
            has_sec_user_agent=has_sec_agent,
            vpn_status=vpn_status,
        )

    except Exception as e:
        logger.error("Error retrieving configuration settings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration settings",
        )


@router.put("/settings")
async def update_config_settings(config: ConfigSettings) -> dict:
    """
    Update user configuration settings.

    Saves AI model preferences, display preferences, and market scraping
    settings to the database.

    Note: API keys should be set via environment variables, not through this endpoint.
    """
    try:
        # Save AI model settings
        await _set_config_value(
            "ai_models",
            config.ai_models.model_dump(exclude_none=True),
            "AI model configuration settings",
        )

        # Save display preferences
        await _set_config_value(
            "display_preferences",
            config.display_preferences.model_dump(exclude_none=True),
            "Display preferences for UI",
        )

        # Save market scraping settings
        await _set_config_value(
            "market_scraping",
            config.market_scraping.model_dump(exclude_none=True),
            "Market data scraping configuration",
        )

        logger.info("Configuration settings updated successfully")

        return {
            "status": "success",
            "message": "Configuration settings updated successfully",
        }

    except Exception as e:
        logger.error("Error updating configuration settings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration settings",
        )


@router.post("/test-api-key", response_model=TestAPIKeyResponse)
async def test_api_key(request: TestAPIKeyRequest) -> TestAPIKeyResponse:
    """
    Test if an API key is valid by making a test request to the provider.

    Supported providers:
    - alpha_vantage: Tests with a simple quote lookup
    - fmp: Tests with a profile lookup
    """
    try:
        if request.provider == "alpha_vantage":
            # Test Alpha Vantage API key with a simple quote request
            import aiohttp

            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": "MSFT",
                "apikey": request.api_key,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    data = await response.json()

                    # Check if we got valid data or an error
                    if "Global Quote" in data and data["Global Quote"]:
                        return TestAPIKeyResponse(
                            valid=True,
                            message="API key is valid",
                            provider="alpha_vantage",
                        )
                    elif "Error Message" in data:
                        return TestAPIKeyResponse(
                            valid=False,
                            message=data["Error Message"],
                            provider="alpha_vantage",
                        )
                    elif "Note" in data:
                        # Rate limit message - key is valid but rate limited
                        return TestAPIKeyResponse(
                            valid=True,
                            message="API key is valid (rate limited)",
                            provider="alpha_vantage",
                        )
                    else:
                        return TestAPIKeyResponse(
                            valid=False,
                            message="Invalid API key or unexpected response",
                            provider="alpha_vantage",
                        )

        elif request.provider == "fmp":
            # Test FMP API key with a profile request (using stable API endpoint)
            import aiohttp

            # Use the new stable API endpoint instead of deprecated v3
            url = "https://financialmodelingprep.com/stable/profile"
            params = {"symbol": "MSFT", "apikey": request.api_key}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check for error message in response
                        if isinstance(data, dict) and "Error Message" in data:
                            return TestAPIKeyResponse(
                                valid=False,
                                message=data.get("Error Message", "API error"),
                                provider="fmp",
                            )
                        if isinstance(data, list) and len(data) > 0:
                            return TestAPIKeyResponse(
                                valid=True,
                                message="API key is valid",
                                provider="fmp",
                            )
                    elif response.status == 401:
                        return TestAPIKeyResponse(
                            valid=False,
                            message="Invalid API key",
                            provider="fmp",
                        )
                    elif response.status == 403:
                        return TestAPIKeyResponse(
                            valid=False,
                            message="Access denied - check your FMP subscription plan",
                            provider="fmp",
                        )

                    return TestAPIKeyResponse(
                        valid=False,
                        message=f"Unexpected response (status {response.status})",
                        provider="fmp",
                    )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}",
            )

    except Exception as e:
        logger.error("Error testing API key", provider=request.provider, error=str(e))
        return TestAPIKeyResponse(
            valid=False,
            message=f"Error testing API key: {str(e)}",
            provider=request.provider,
        )


@router.get("/category-mappings")
async def get_category_mappings() -> dict:
    """
    Get the mapping of data categories to configured data sources.

    Returns a mapping of each category (top_gainers, top_losers, etc.)
    to a list of sources that provide that data, including both
    traditional API sources and web-scraped sources.
    """
    from backend.app.db.models import ScrapedWebsite

    # Traditional API sources that support specific categories
    # These are built-in data sources that don't require web scraping
    TRADITIONAL_API_SOURCES = {
        "news": [
            {
                "key": "alpha_vantage_news",
                "name": "Alpha Vantage News",
                "url": "https://www.alphavantage.co/",
                "type": "api",
            },
        ],
        "dashboard_sentiment": [
            {
                "key": "alpha_vantage_sentiment",
                "name": "Alpha Vantage Market Sentiment",
                "url": "https://www.alphavantage.co/",
                "type": "api",
            },
        ],
        "top_gainers": [
            {
                "key": "yahoo_finance_gainers",
                "name": "Yahoo Finance Gainers",
                "url": "https://finance.yahoo.com/",
                "type": "api",
            },
        ],
        "top_losers": [
            {
                "key": "yahoo_finance_losers",
                "name": "Yahoo Finance Losers",
                "url": "https://finance.yahoo.com/",
                "type": "api",
            },
        ],
    }

    # Get saved mappings from user config
    saved_mappings = await _get_config_value("category_source_mappings")
    if saved_mappings is None:
        saved_mappings = {}

    # Get all active websites with their categories
    async with async_session_factory() as session:
        stmt = select(ScrapedWebsite).where(ScrapedWebsite.is_active == True)
        result = await session.execute(stmt)
        websites = result.scalars().all()

    # Build available sources per category
    available_sources = {}
    for category in DATA_USE_CATEGORIES:
        available_sources[category] = []
        # Add traditional API sources first (if available for this category)
        if category in TRADITIONAL_API_SOURCES:
            for api_source in TRADITIONAL_API_SOURCES[category]:
                available_sources[category].append({
                    **api_source,
                    "type": "api",
                })

    # Add web-scraped sources
    for website in websites:
        website_categories = [c.strip() for c in website.data_use.split(",") if c.strip()]
        for cat in website_categories:
            if cat in available_sources:
                available_sources[cat].append({
                    "key": website.key,
                    "name": website.name,
                    "url": website.url,
                    "type": "web_scraping",
                })

    # Build response with display names
    categories_info = []
    for category in DATA_USE_CATEGORIES:
        categories_info.append({
            "category": category,
            "display_name": DATA_USE_DISPLAY_NAMES.get(category, category),
            "selected_sources": saved_mappings.get(category, []),
            "available_sources": available_sources.get(category, []),
        })

    return {
        "categories": categories_info,
        "mappings": saved_mappings,
    }


@router.put("/category-mappings")
async def update_category_mappings(mappings: dict) -> dict:
    """
    Update the mapping of data categories to data sources.

    Args:
        mappings: Dict mapping category names to lists of source keys.
                  e.g., {"top_gainers": ["yahoo_gainer"], "news": ["alpha_vantage_news", "yahoo_news_latest"]}

    Returns:
        Success status and updated mappings.
    """
    # Known traditional API source keys (not in database)
    TRADITIONAL_API_SOURCE_KEYS = {
        "alpha_vantage_news",
        "alpha_vantage_sentiment",
        "yahoo_finance_gainers",
        "yahoo_finance_losers",
    }

    try:
        # Validate that all categories are valid
        for category in mappings.keys():
            if category not in DATA_USE_CATEGORIES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}",
                )

        # Validate that all source keys exist (either as API source or web-scraped website)
        async with async_session_factory() as session:
            from backend.app.db.models import ScrapedWebsite

            for category, source_keys in mappings.items():
                if not isinstance(source_keys, list):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sources for {category} must be a list",
                    )

                for key in source_keys:
                    # Skip validation for known API sources
                    if key in TRADITIONAL_API_SOURCE_KEYS:
                        continue

                    # Check if it's a web-scraped source
                    stmt = select(ScrapedWebsite).where(ScrapedWebsite.key == key)
                    result = await session.execute(stmt)
                    website = result.scalar_one_or_none()
                    if not website:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unknown data source: {key}",
                        )

        # Save mappings
        await _set_config_value(
            "category_source_mappings",
            mappings,
            "Mapping of data categories to data sources",
        )

        logger.info("Category mappings updated", mappings=mappings)

        return {
            "status": "success",
            "message": "Category mappings updated successfully",
            "mappings": mappings,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating category mappings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category mappings",
        )


@router.post("/refresh-category/{category}")
async def refresh_category_data(category: str) -> dict:
    """
    Trigger a refresh of data for a specific category.

    This scrapes all configured data sources for the specified category.

    Args:
        category: The category to refresh (e.g., "top_gainers", "top_losers")

    Returns:
        Status and list of triggered jobs.
    """
    if category not in DATA_USE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}",
        )

    # Get configured sources for this category
    saved_mappings = await _get_config_value("category_source_mappings")
    if not saved_mappings or category not in saved_mappings:
        return {
            "status": "warning",
            "message": f"No data sources configured for category: {category}",
            "jobs": [],
        }

    source_keys = saved_mappings[category]
    if not source_keys:
        return {
            "status": "warning",
            "message": f"No data sources configured for category: {category}",
            "jobs": [],
        }

    # Trigger scrape for each configured source
    from backend.app.tasks.market import refresh_web_scraped_market

    jobs = []
    for source_key in source_keys:
        task = refresh_web_scraped_market.delay(website_config_key=source_key)
        jobs.append({
            "source_key": source_key,
            "job_id": task.id,
        })

    return {
        "status": "queued",
        "message": f"Triggered refresh for {len(jobs)} data source(s)",
        "jobs": jobs,
    }
