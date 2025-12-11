"""Market sentiment Celery tasks."""

import asyncio
from typing import Any

import structlog

from backend.app.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(name="backend.app.tasks.market.refresh_market_sentiment")
def refresh_market_sentiment() -> dict[str, Any]:
    """Refresh daily market sentiment analysis.

    This task is scheduled to run at 4 PM EST on weekdays.
    """
    from pipelines.assets.market_sentiment import (
        fetch_market_data,
        fetch_market_news,
        analyze_sentiment_with_ollama,
        save_sentiment_to_db,
    )
    from datetime import date

    async def run():
        logger.info("Starting market sentiment refresh")

        # Fetch market data
        market_data = await fetch_market_data()
        logger.info("Fetched market indices and sectors")

        # Fetch news
        news = await fetch_market_news()
        logger.info("Fetched market news", count=len(news))

        # Analyze with Ollama
        analysis = await analyze_sentiment_with_ollama(
            market_data["indices"],
            market_data["sectors"],
            news,
        )
        logger.info("Completed sentiment analysis")

        # Prepare result
        result = {
            "date": date.today().isoformat(),
            "indices": market_data["indices"],
            "sectors": market_data["sectors"],
            "news": news,
            "analysis": analysis,
        }

        # Save to database
        sentiment_id = await save_sentiment_to_db(result)
        result["sentiment_id"] = sentiment_id

        logger.info("Market sentiment refresh completed", sentiment_id=sentiment_id)
        return result

    return run_async(run())


@celery_app.task(name="backend.app.tasks.market.refresh_web_scraped_market")
def refresh_web_scraped_market(
    website_config_key: str | None = None,
    scraping_model: str | None = None,
    analysis_model: str | None = None,
) -> dict[str, Any]:
    """
    Refresh web-scraped market data analysis.

    Args:
        website_config_key: Config key for website to scrape (e.g., "market_overview_perplexity")
        scraping_model: LLM model for data extraction
        analysis_model: LLM model for market analysis

    This task:
    1. Uses WebScrapingAgent (with Playwright) to extract data from configured website
    2. Uses MarketAnalysisAgent to analyze the scraped data
    3. Saves results to WebScrapedMarketData table
    """
    from pipelines.assets.web_scraped_market import (
        scrape_market_website,
        analyze_scraped_market_data,
        save_web_scraped_data_to_db,
        get_user_config_for_market_scraping,
    )
    from datetime import date

    async def run():
        logger.info("Starting web-scraped market data refresh")

        # Get user configuration for LLM models and website
        user_config = await get_user_config_for_market_scraping()

        # Determine which website to scrape
        website_key = (
            website_config_key
            or user_config.get("market_scraping_website")
            or "market_overview_perplexity"
        )

        # Determine LLM models to use
        scraping_llm = scraping_model or user_config.get("market_scraping_llm_model")
        analysis_llm = analysis_model or user_config.get("market_analysis_llm_model")

        logger.info(
            "Configuration loaded",
            website=website_key,
            scraping_model=scraping_llm,
            analysis_model=analysis_llm,
        )

        # Step 1: Scrape website (now using Playwright directly)
        scraped_data = await scrape_market_website(
            website_config_key=website_key,
            llm_model=scraping_llm,
        )

        logger.info(
            "Scraped market website",
            website=website_key,
            success=scraped_data.get("success", False),
        )

        if not scraped_data.get("success"):
            logger.error("Web scraping failed", error=scraped_data.get("error"))
            return {
                "status": "failed",
                "error": scraped_data.get("error"),
                "step": "scraping",
            }

        # Step 2: Analyze scraped data
        analysis_result = await analyze_scraped_market_data(
            raw_data=scraped_data["data"],
            source_url=scraped_data["source_url"],
            llm_model=analysis_llm,
        )

        logger.info(
            "Analyzed scraped data",
            success=analysis_result.get("success", False),
        )

        if not analysis_result.get("success"):
            logger.error("Market analysis failed", error=analysis_result.get("error"))
            return {
                "status": "failed",
                "error": analysis_result.get("error"),
                "step": "analysis",
            }

        # Step 3: Save to database
        result = {
            "date": date.today().isoformat(),
            "source_url": scraped_data["source_url"],
            "source_name": website_key,
            "raw_data": scraped_data["data"],
            "scraping_model": scraping_llm,
            "analysis": analysis_result,
            "analysis_model": analysis_llm,
            "response_time_ms": scraped_data.get("response_time_ms", 0),
        }

        record_id = await save_web_scraped_data_to_db(result)
        result["record_id"] = record_id
        result["status"] = "success"

        logger.info(
            "Web-scraped market data refresh completed", record_id=record_id
        )
        return result

    return run_async(run())
