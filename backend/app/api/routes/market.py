"""Market sentiment API routes."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import MarketSentiment, WebScrapedMarketData
from backend.app.db.session import get_db
from backend.app.schemas.market import (
    MarketSentimentResponse,
    MarketSentimentHistoryResponse,
    WebScrapedMarketDataResponse,
    CombinedMarketResponse,
)

router = APIRouter()


@router.get("/sentiment", response_model=CombinedMarketResponse)
async def get_market_sentiment(
    db: AsyncSession = Depends(get_db),
) -> CombinedMarketResponse:
    """Get current market sentiment analysis.

    Returns both traditional and web-scraped market data including:
    - Traditional: Major index performance, sentiment scores, sectors, news
    - Web-scraped: Market summary, sentiment, sectors, themes from configured website

    Auto-triggers a refresh if no data exists or if data has all zero values (placeholder).
    """
    # Get the latest traditional sentiment
    stmt = select(MarketSentiment).order_by(MarketSentiment.date.desc()).limit(1)
    result = await db.execute(stmt)
    sentiment = result.scalar_one_or_none()

    # Auto-trigger refresh if:
    # 1. No data exists
    # 2. Data has all zero values (placeholder)
    # 3. Data is not from today (stale)
    should_refresh = (
        not sentiment or
        (sentiment.sp500_close == 0 and sentiment.nasdaq_close == 0 and sentiment.dow_close == 0) or
        sentiment.date < date.today()
    )

    if should_refresh:
        from backend.app.tasks.market import refresh_market_sentiment as refresh_task
        refresh_task.delay()
        # Note: This will be async, so first load may show stale data, but subsequent loads will have fresh data

    if not sentiment:
        traditional_response = MarketSentimentResponse(
            date=date.today(),
            message="No sentiment data available. Run market analysis first.",
        )
    else:
        traditional_response = MarketSentimentResponse(
            date=sentiment.date,
            indices={
                "sp500": {
                    "close": float(sentiment.sp500_close) if sentiment.sp500_close else None,
                    "change_pct": float(sentiment.sp500_change_pct) if sentiment.sp500_change_pct else None,
                },
                "nasdaq": {
                    "close": float(sentiment.nasdaq_close) if sentiment.nasdaq_close else None,
                    "change_pct": float(sentiment.nasdaq_change_pct) if sentiment.nasdaq_change_pct else None,
                },
                "dow": {
                    "close": float(sentiment.dow_close) if sentiment.dow_close else None,
                    "change_pct": float(sentiment.dow_change_pct) if sentiment.dow_change_pct else None,
                },
            },
            overall_sentiment=float(sentiment.overall_sentiment) if sentiment.overall_sentiment else None,
            bullish_score=float(sentiment.bullish_score) if sentiment.bullish_score else None,
            bearish_score=float(sentiment.bearish_score) if sentiment.bearish_score else None,
            hot_sectors=sentiment.hot_sectors or [],
            negative_sectors=sentiment.negative_sectors or [],
            top_news=sentiment.top_news or [],
        )

    # Get web-scraped data
    stmt = select(WebScrapedMarketData).order_by(WebScrapedMarketData.date.desc()).limit(1)
    result = await db.execute(stmt)
    web_data = result.scalar_one_or_none()

    web_scraped_response = None
    if web_data:
        web_scraped_response = WebScrapedMarketDataResponse(
            date=web_data.date,
            source_url=web_data.source_url,
            source_name=web_data.source_name,
            market_summary=web_data.market_summary,
            overall_sentiment=float(web_data.overall_sentiment) if web_data.overall_sentiment else None,
            bullish_score=float(web_data.bullish_score) if web_data.bullish_score else None,
            bearish_score=float(web_data.bearish_score) if web_data.bearish_score else None,
            trending_sectors=web_data.trending_sectors or [],
            declining_sectors=web_data.declining_sectors or [],
            market_themes=web_data.market_themes or [],
            key_events=web_data.key_events or [],
            confidence_score=float(web_data.confidence_score) if web_data.confidence_score else None,
            scraping_model=web_data.scraping_model,
            analysis_model=web_data.analysis_model,
        )

    return CombinedMarketResponse(
        traditional=traditional_response,
        web_scraped=web_scraped_response,
    )


@router.get("/sentiment/history", response_model=MarketSentimentHistoryResponse)
async def get_market_sentiment_history(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> MarketSentimentHistoryResponse:
    """Get market sentiment history for the specified number of days."""
    start_date = date.today() - timedelta(days=days)

    stmt = (
        select(MarketSentiment)
        .where(MarketSentiment.date >= start_date)
        .order_by(MarketSentiment.date.desc())
    )
    result = await db.execute(stmt)
    sentiments = result.scalars().all()

    history = []
    for s in sentiments:
        history.append({
            "date": s.date,
            "sp500_change_pct": float(s.sp500_change_pct) if s.sp500_change_pct else None,
            "nasdaq_change_pct": float(s.nasdaq_change_pct) if s.nasdaq_change_pct else None,
            "dow_change_pct": float(s.dow_change_pct) if s.dow_change_pct else None,
            "overall_sentiment": float(s.overall_sentiment) if s.overall_sentiment else None,
        })

    return MarketSentimentHistoryResponse(
        days=days,
        history=history,
    )


@router.post("/sentiment/refresh")
async def refresh_market_sentiment(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a refresh of market sentiment analysis.

    This will queue a job to fetch latest market data and run sentiment analysis.
    """
    from backend.app.tasks.market import refresh_market_sentiment as refresh_task

    # Send task to Celery
    task = refresh_task.delay()

    return {
        "status": "queued",
        "message": "Market sentiment refresh has been queued",
        "job_id": task.id,
    }


@router.post("/sentiment/refresh-web-scraped")
async def refresh_web_scraped_market_data(
    website_key: str | None = None,
    scraping_model: str | None = None,
    analysis_model: str | None = None,
) -> dict:
    """Trigger a refresh of web-scraped market data.

    Args:
        website_key: Optional website config key (defaults to user config)
        scraping_model: Optional LLM model for scraping (defaults to user config)
        analysis_model: Optional LLM model for analysis (defaults to user config)
    """
    from backend.app.tasks.market import refresh_web_scraped_market as refresh_task

    # Send task to Celery
    task = refresh_task.delay(
        website_config_key=website_key,
        scraping_model=scraping_model,
        analysis_model=analysis_model,
    )

    return {
        "status": "queued",
        "message": "Web-scraped market data refresh has been queued",
        "job_id": task.id,
    }


@router.get("/scraping-config")
async def get_market_scraping_config() -> dict:
    """Get available market scraping website configurations."""
    from backend.app.config import get_settings

    settings = get_settings()
    configs = settings.web_scraping_configs

    # Filter for market-related configs
    market_configs = {
        key: {
            "name": key,
            "url": cfg.url_pattern,
        }
        for key, cfg in configs.items()
        if key.startswith("market_overview_")
    }

    return {
        "available_websites": market_configs,
    }


@router.post("/scraping-config")
async def set_market_scraping_config(
    website_key: str,
    scraping_model: str | None = None,
    analysis_model: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save user's market scraping configuration."""
    from backend.app.db.models import UserConfig

    # Save website selection
    stmt = select(UserConfig).where(UserConfig.config_key == "market_scraping_website")
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.config_value = {"website_key": website_key}
    else:
        config = UserConfig(
            config_key="market_scraping_website",
            config_value={"website_key": website_key},
            description="Selected website for market data scraping",
        )
        db.add(config)

    # Save scraping model if provided
    if scraping_model:
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_scraping_llm_model"
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.config_value = {"model": scraping_model}
        else:
            config = UserConfig(
                config_key="market_scraping_llm_model",
                config_value={"model": scraping_model},
                description="LLM model for market data scraping",
            )
            db.add(config)

    # Save analysis model if provided
    if analysis_model:
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_analysis_llm_model"
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.config_value = {"model": analysis_model}
        else:
            config = UserConfig(
                config_key="market_analysis_llm_model",
                config_value={"model": analysis_model},
                description="LLM model for market analysis",
            )
            db.add(config)

    await db.commit()

    return {
        "status": "success",
        "message": "Market scraping configuration saved",
        "config": {
            "website_key": website_key,
            "scraping_model": scraping_model,
            "analysis_model": analysis_model,
        },
    }


@router.get("/indices/history")
async def get_indices_history(
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Get historical data for major market indices.

    Returns the last N days of price data for S&P 500, NASDAQ, and Dow Jones.
    """
    from backend.app.services.yahoo_finance import get_yahoo_finance_client

    client = get_yahoo_finance_client()

    # Map days to period parameter
    if days <= 5:
        period = "5d"
    elif days <= 30:
        period = "1mo"
    elif days <= 90:
        period = "3mo"
    elif days <= 180:
        period = "6mo"
    else:
        period = "1y"

    indices = {
        "^GSPC": "sp500",
        "^IXIC": "nasdaq",
        "^DJI": "dow",
    }

    result = {}
    for symbol, key in indices.items():
        try:
            history = await client.get_historical_prices(
                symbol,
                period=period,
                interval="1d",
            )
            result[key] = [
                {
                    "date": point["date"],
                    "close": float(point["close"]) if point["close"] else None,
                }
                for point in history
            ]
        except Exception as e:
            result[key] = []

    return result
