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
