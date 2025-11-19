"""Market sentiment Dagster asset."""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from dagster import asset, Output, MetadataValue
import structlog

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def fetch_market_data() -> dict[str, Any]:
    """Fetch market indices and sector performance."""
    from backend.app.services.yahoo_finance import get_yahoo_finance_client

    client = get_yahoo_finance_client()

    # Fetch indices
    indices = await client.get_market_indices()

    # Fetch sector performance
    sectors = await client.get_sector_performance()

    return {
        "indices": indices,
        "sectors": sectors,
    }


async def fetch_market_news() -> list[dict[str, Any]]:
    """Fetch market news with sentiment."""
    from backend.app.services.alpha_vantage import get_alpha_vantage_client

    try:
        client = await get_alpha_vantage_client()
        news = await client.get_news_sentiment(
            topics="economy,finance,earnings",
            limit=20,
        )
        return news
    except Exception as e:
        logger.warning("Failed to fetch news", error=str(e))
        return []


async def analyze_sentiment_with_ollama(
    indices: dict,
    sectors: list,
    news: list,
) -> dict[str, Any]:
    """Use Ollama to analyze overall market sentiment."""
    import ollama
    from backend.app.config import get_settings

    settings = get_settings()

    # Prepare context for analysis
    context = f"""
    Analyze the following market data and provide sentiment analysis.

    ## Market Indices
    """

    for symbol, data in indices.items():
        if "error" not in data:
            change = float(data.get("change_percent", 0) or 0)
            context += f"- {data['name']}: {change:+.2f}%\n"

    context += "\n## Sector Performance\n"
    for sector in sectors[:5]:
        change = float(sector.get("change_percent", 0) or 0)
        context += f"- {sector['name']}: {change:+.2f}%\n"

    context += "\n## Recent News Headlines\n"
    for article in news[:10]:
        sentiment = article.get("overall_sentiment_label", "neutral")
        context += f"- [{sentiment}] {article.get('title', 'Unknown')}\n"

    context += """

    Based on this data, provide:
    1. Overall market sentiment score (0-1, where 0=very bearish, 1=very bullish)
    2. Bullish score (0-1)
    3. Bearish score (0-1)
    4. Top 3 hot sectors
    5. Top 3 concerning sectors
    6. Brief market summary (2-3 sentences)

    Respond in JSON format:
    {
        "overall_sentiment": 0.X,
        "bullish_score": 0.X,
        "bearish_score": 0.X,
        "hot_sectors": ["sector1", "sector2", "sector3"],
        "negative_sectors": ["sector1", "sector2", "sector3"],
        "summary": "Brief market summary..."
    }
    """

    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst providing objective market sentiment analysis. Respond only with valid JSON.",
                },
                {"role": "user", "content": context},
            ],
        )

        # Parse response
        import json
        content = response["message"]["content"]

        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)

        # Fallback if parsing fails
        return {
            "overall_sentiment": 0.5,
            "bullish_score": 0.5,
            "bearish_score": 0.5,
            "hot_sectors": [],
            "negative_sectors": [],
            "summary": "Unable to analyze market sentiment.",
        }

    except Exception as e:
        logger.error("Ollama analysis failed", error=str(e))
        return {
            "overall_sentiment": 0.5,
            "bullish_score": 0.5,
            "bearish_score": 0.5,
            "hot_sectors": [],
            "negative_sectors": [],
            "summary": f"Analysis failed: {e}",
        }


async def save_sentiment_to_db(sentiment_data: dict[str, Any]) -> int:
    """Save sentiment data to database."""
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import MarketSentiment

    async with async_session_factory() as session:
        today = date.today()

        # Check if we already have data for today
        stmt = select(MarketSentiment).where(MarketSentiment.date == today)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        indices = sentiment_data.get("indices", {})
        analysis = sentiment_data.get("analysis", {})

        # Extract index data
        sp500 = indices.get("^GSPC", {})
        nasdaq = indices.get("^IXIC", {})
        dow = indices.get("^DJI", {})

        if existing:
            # Update existing record
            existing.sp500_close = sp500.get("price")
            existing.sp500_change_pct = sp500.get("change_percent")
            existing.nasdaq_close = nasdaq.get("price")
            existing.nasdaq_change_pct = nasdaq.get("change_percent")
            existing.dow_close = dow.get("price")
            existing.dow_change_pct = dow.get("change_percent")
            existing.overall_sentiment = Decimal(str(analysis.get("overall_sentiment", 0.5)))
            existing.bullish_score = Decimal(str(analysis.get("bullish_score", 0.5)))
            existing.bearish_score = Decimal(str(analysis.get("bearish_score", 0.5)))
            existing.hot_sectors = [{"name": s} for s in analysis.get("hot_sectors", [])]
            existing.negative_sectors = [{"name": s} for s in analysis.get("negative_sectors", [])]
            existing.top_news = sentiment_data.get("news", [])[:10]
            existing.news_count = len(sentiment_data.get("news", []))

            sentiment_id = existing.id
        else:
            # Create new record
            sentiment = MarketSentiment(
                date=today,
                sp500_close=sp500.get("price"),
                sp500_change_pct=sp500.get("change_percent"),
                nasdaq_close=nasdaq.get("price"),
                nasdaq_change_pct=nasdaq.get("change_percent"),
                dow_close=dow.get("price"),
                dow_change_pct=dow.get("change_percent"),
                overall_sentiment=Decimal(str(analysis.get("overall_sentiment", 0.5))),
                bullish_score=Decimal(str(analysis.get("bullish_score", 0.5))),
                bearish_score=Decimal(str(analysis.get("bearish_score", 0.5))),
                hot_sectors=[{"name": s} for s in analysis.get("hot_sectors", [])],
                negative_sectors=[{"name": s} for s in analysis.get("negative_sectors", [])],
                top_news=sentiment_data.get("news", [])[:10],
                news_count=len(sentiment_data.get("news", [])),
                analysis_source="ollama",
            )
            session.add(sentiment)
            await session.flush()
            sentiment_id = sentiment.id

        await session.commit()
        return sentiment_id


@asset(
    description="Daily market sentiment analysis including indices, sectors, and AI-powered sentiment scoring",
    group_name="market",
    compute_kind="python",
)
def market_sentiment_asset() -> Output[dict]:
    """Fetch and analyze daily market sentiment."""

    async def run():
        logger.info("Starting market sentiment analysis")

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

        logger.info("Saved market sentiment", sentiment_id=sentiment_id)
        return result

    result = run_async(run())

    return Output(
        value=result,
        metadata={
            "date": MetadataValue.text(result["date"]),
            "overall_sentiment": MetadataValue.float(result["analysis"].get("overall_sentiment", 0.5)),
            "news_count": MetadataValue.int(len(result["news"])),
            "hot_sectors": MetadataValue.json(result["analysis"].get("hot_sectors", [])),
        },
    )
