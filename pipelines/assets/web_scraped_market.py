"""Web-scraped market data asset for Dagster and Celery."""

import asyncio
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


async def get_user_config_for_market_scraping() -> dict[str, Any]:
    """
    Get user configuration for market scraping LLM models.

    Returns:
        dict: Configuration with LLM model names and website selection
    """
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import UserConfig

    async with async_session_factory() as session:
        # Get scraping model config
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_scraping_llm_model"
        )
        result = await session.execute(stmt)
        scraping_config = result.scalar_one_or_none()

        # Get analysis model config
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_analysis_llm_model"
        )
        result = await session.execute(stmt)
        analysis_config = result.scalar_one_or_none()

        # Get website config
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_scraping_website"
        )
        result = await session.execute(stmt)
        website_config = result.scalar_one_or_none()

        return {
            "market_scraping_llm_model": (
                scraping_config.config_value.get("model")
                if scraping_config and scraping_config.config_value
                else None
            ),
            "market_analysis_llm_model": (
                analysis_config.config_value.get("model")
                if analysis_config and analysis_config.config_value
                else None
            ),
            "market_scraping_website": (
                website_config.config_value.get("website_key")
                if website_config and website_config.config_value
                else "market_overview_perplexity"
            ),
        }


async def scrape_market_website(
    website_config_key: str,
    llm_model: str | None = None,
) -> dict[str, Any]:
    """
    Scrape market data from configured website.

    Args:
        website_config_key: Configuration key for website (e.g., "market_overview_perplexity")
        llm_model: Optional LLM model for extraction

    Returns:
        Dict with success, data, source_url, response_time_ms
    """
    from backend.app.agents.web_scraping_agent import (
        WebScrapingAgent,
        load_web_scraping_config,
    )

    # Load configuration for this website
    config = load_web_scraping_config(website_config_key)
    if not config:
        logger.error(
            "No configuration found for website",
            website_key=website_config_key,
        )
        return {
            "success": False,
            "error": f"No configuration found for website: {website_config_key}",
        }

    # Override model if provided
    agent = WebScrapingAgent()
    if llm_model:
        agent.settings.ollama_model = llm_model  # Temporary override

    try:
        # Scrape website (no context vars needed for market overview URLs)
        result = await agent.extract_data(
            config=config,
            context_vars={},  # No template variables in URL for market overview
        )

        if not result.success:
            return {
                "success": False,
                "error": result.error,
            }

        # Extract data categories from config.data_type (comma-separated)
        data_categories = [c.strip() for c in config.data_type.split(",") if c.strip()]

        return {
            "success": True,
            "data": result.data,
            "source_url": result.source_url,
            "response_time_ms": result.response_time_ms,
            "data_categories": data_categories,
        }

    except Exception as e:
        logger.error("Web scraping failed", error=str(e), website_key=website_config_key)
        return {
            "success": False,
            "error": str(e),
        }


async def analyze_scraped_market_data(
    raw_data: dict[str, Any],
    source_url: str,
    llm_model: str | None = None,
) -> dict[str, Any]:
    """
    Analyze scraped market data using MarketAnalysisAgent.

    Args:
        raw_data: Raw data extracted by web scraping
        source_url: Source URL for context
        llm_model: Optional LLM model for analysis

    Returns:
        Dict with success, sentiment scores, sectors, themes
    """
    from backend.app.agents.market_analysis_agent import MarketAnalysisAgent

    agent = MarketAnalysisAgent(llm_model=llm_model)

    result = await agent.analyze_market_data(
        raw_data=raw_data,
        source_url=source_url,
    )

    if not result.success:
        return {
            "success": False,
            "error": result.error,
        }

    return {
        "success": True,
        "overall_sentiment": result.overall_sentiment,
        "bullish_score": result.bullish_score,
        "bearish_score": result.bearish_score,
        "trending_sectors": result.trending_sectors,
        "declining_sectors": result.declining_sectors,
        "market_themes": result.market_themes,
        "key_events": result.key_events,
        "analysis_summary": result.analysis_summary,
        "confidence_score": result.confidence_score,
    }


async def save_web_scraped_data_to_db(data: dict[str, Any]) -> int | None:
    """
    Save web-scraped market data to database.

    Only saves to WebScrapedMarketData if source has 'dashboard_sentiment' category.
    Always saves category-specific data to ScrapedCategoryData.

    Args:
        data: Data to save including raw data and analysis results

    Returns:
        int | None: Record ID of saved data (None if not saved to WebScrapedMarketData)
    """
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import WebScrapedMarketData

    data_categories = data.get("data_categories", [])
    record_id = None

    # Only save to WebScrapedMarketData if source has 'dashboard_sentiment' category
    # This ensures Market Summary only shows data from appropriate sources
    if "dashboard_sentiment" in data_categories:
        async with async_session_factory() as session:
            today = date.today()

            # Check if we already have data for today from a dashboard_sentiment source
            stmt = select(WebScrapedMarketData).where(WebScrapedMarketData.date == today)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            analysis = data.get("analysis", {})

            if existing:
                # Update existing record
                existing.source_url = data["source_url"]
                existing.source_name = data["source_name"]
                existing.raw_scraped_data = data["raw_data"]
                existing.scraping_model = data.get("scraping_model")
                existing.market_summary = analysis.get("analysis_summary", "")
                existing.overall_sentiment = Decimal(
                    str(analysis.get("overall_sentiment", 0.5))
                )
                existing.bullish_score = Decimal(str(analysis.get("bullish_score", 0.5)))
                existing.bearish_score = Decimal(str(analysis.get("bearish_score", 0.5)))
                existing.trending_sectors = [
                    {"name": s} for s in analysis.get("trending_sectors", [])
                ]
                existing.declining_sectors = [
                    {"name": s} for s in analysis.get("declining_sectors", [])
                ]
                existing.market_themes = analysis.get("market_themes", [])
                existing.key_events = analysis.get("key_events", [])
                existing.analysis_model = data.get("analysis_model")
                existing.analysis_timestamp = datetime.now()
                existing.confidence_score = Decimal(
                    str(analysis.get("confidence_score", 0.5))
                )
                existing.response_time_ms = data.get("response_time_ms", 0)

                record_id = existing.id
                logger.info("Updated existing web-scraped market data", record_id=record_id)
            else:
                # Create new record
                record = WebScrapedMarketData(
                    date=today,
                    source_url=data["source_url"],
                    source_name=data["source_name"],
                    data_type="market_overview",
                    raw_scraped_data=data["raw_data"],
                    scraping_model=data.get("scraping_model"),
                    market_summary=analysis.get("analysis_summary", ""),
                    overall_sentiment=Decimal(str(analysis.get("overall_sentiment", 0.5))),
                    bullish_score=Decimal(str(analysis.get("bullish_score", 0.5))),
                    bearish_score=Decimal(str(analysis.get("bearish_score", 0.5))),
                    trending_sectors=[
                        {"name": s} for s in analysis.get("trending_sectors", [])
                    ],
                    declining_sectors=[
                        {"name": s} for s in analysis.get("declining_sectors", [])
                    ],
                    market_themes=analysis.get("market_themes", []),
                    key_events=analysis.get("key_events", []),
                    analysis_model=data.get("analysis_model"),
                    analysis_timestamp=datetime.now(),
                    confidence_score=Decimal(str(analysis.get("confidence_score", 0.5))),
                    extraction_method="mcp_playwright",
                    response_time_ms=data.get("response_time_ms", 0),
                )
                session.add(record)
                await session.flush()
                record_id = record.id
                logger.info("Created new web-scraped market data", record_id=record_id)

            await session.commit()
    else:
        logger.info(
            "Skipping WebScrapedMarketData save - source not configured for dashboard_sentiment",
            source_name=data["source_name"],
            categories=data_categories,
        )

    # Always save category-specific data
    if data.get("raw_data") and data_categories:
        await save_category_data_to_db(
            source_key=data["source_name"],
            source_url=data["source_url"],
            categories=data_categories,
            raw_data=data["raw_data"],
            scraping_model=data.get("scraping_model"),
            response_time_ms=data.get("response_time_ms", 0),
        )

    return record_id


async def save_category_data_to_db(
    source_key: str,
    source_url: str,
    categories: list[str],
    raw_data: dict[str, Any],
    scraping_model: str | None = None,
    response_time_ms: int = 0,
) -> list[int]:
    """
    Save category-specific scraped data to database.

    This extracts data for each category from the raw_data and saves it
    to the ScrapedCategoryData table, allowing multiple sources per category.

    Args:
        source_key: Website configuration key
        source_url: URL that was scraped
        categories: List of data categories configured for this website
        raw_data: Raw LLM extraction results
        scraping_model: Name of LLM used for scraping
        response_time_ms: Time taken for scraping

    Returns:
        list[int]: List of record IDs saved
    """
    from sqlalchemy import select, and_
    from sqlalchemy.dialects.postgresql import insert
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ScrapedCategoryData

    saved_ids = []
    today = date.today()

    # Category key mappings - maps category name to possible keys in raw_data
    CATEGORY_DATA_KEYS = {
        "top_gainers": ["stocks", "gainers", "top_gainers"],
        "top_losers": ["stocks", "losers", "top_losers"],
        "hot_stocks": ["stocks", "hot_stocks", "trending_stocks"],
        "hot_sectors": ["sectors", "hot_sectors", "trending_sectors"],
        "bad_sectors": ["sectors", "bad_sectors", "declining_sectors"],
        "analyst_ratings": ["ratings", "analyst_ratings"],
        "news": ["articles", "news", "headlines"],
        "dashboard_sentiment": ["market_summary", "sentiment"],
        "etf_holdings": ["holdings", "etf_holdings"],
        "etf_holding_changes": ["changes", "etf_holding_changes"],
        "fund_holdings": ["holdings", "fund_holdings"],
        "fund_holding_changes": ["changes", "fund_holding_changes"],
    }

    async with async_session_factory() as session:
        for category in categories:
            # Extract data for this category from raw_data
            category_data = None

            # First, check if raw_data has a key matching the category directly
            if category in raw_data:
                category_data = raw_data[category]
            else:
                # Try alternative keys for this category
                possible_keys = CATEGORY_DATA_KEYS.get(category, [])
                for key in possible_keys:
                    if key in raw_data and raw_data[key]:
                        category_data = raw_data[key]
                        break

            # If we still don't have data, check if the entire raw_data is for a single category
            if category_data is None and len(categories) == 1:
                # Single category - the raw_data itself might be the category data
                category_data = raw_data

            if category_data is None:
                logger.warning(
                    "No data found for category",
                    category=category,
                    source_key=source_key,
                    available_keys=list(raw_data.keys()),
                )
                continue

            # Check for existing record for today/source/category
            stmt = select(ScrapedCategoryData).where(
                and_(
                    ScrapedCategoryData.date == today,
                    ScrapedCategoryData.source_key == source_key,
                    ScrapedCategoryData.category == category,
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.source_url = source_url
                existing.data = category_data
                existing.scraping_model = scraping_model
                existing.response_time_ms = response_time_ms
                saved_ids.append(existing.id)
                logger.info(
                    "Updated category data",
                    category=category,
                    source_key=source_key,
                    record_id=existing.id,
                )
            else:
                # Create new record
                record = ScrapedCategoryData(
                    date=today,
                    source_key=source_key,
                    source_url=source_url,
                    category=category,
                    data=category_data,
                    scraping_model=scraping_model,
                    response_time_ms=response_time_ms,
                )
                session.add(record)
                await session.flush()
                saved_ids.append(record.id)
                logger.info(
                    "Created category data",
                    category=category,
                    source_key=source_key,
                    record_id=record.id,
                )

        await session.commit()

    return saved_ids
