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
from backend.app.schemas.config import (
    ConfigResponse,
    ConfigSettings,
    TestAPIKeyRequest,
    TestAPIKeyResponse,
    AIModelSettings,
    DisplayPreferences,
    MarketScrapingSettings,
)

router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()


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

        return ConfigResponse(
            settings=ConfigSettings(
                ai_models=ai_models,
                display_preferences=display_preferences,
                market_scraping=market_scraping,
            ),
            has_alpha_vantage_key=has_alpha_vantage,
            has_fmp_key=has_fmp,
            has_sec_user_agent=has_sec_agent,
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
            # Test FMP API key with a profile request
            import aiohttp

            url = f"https://financialmodelingprep.com/api/v3/profile/MSFT"
            params = {"apikey": request.api_key}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
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
