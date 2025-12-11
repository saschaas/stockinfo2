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

        return {
            "success": True,
            "data": result.data,
            "source_url": result.source_url,
            "response_time_ms": result.response_time_ms,
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


async def save_web_scraped_data_to_db(data: dict[str, Any]) -> int:
    """
    Save web-scraped market data to database.

    Args:
        data: Data to save including raw data and analysis results

    Returns:
        int: Record ID of saved data
    """
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import WebScrapedMarketData

    async with async_session_factory() as session:
        today = date.today()

        # Check if we already have data for today
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
        return record_id
