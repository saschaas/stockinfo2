"""Market sentiment API routes."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import MarketSentiment
from backend.app.db.session import get_db
from backend.app.schemas.market import (
    MarketSentimentResponse,
    MarketSentimentHistoryResponse,
)

router = APIRouter()


@router.get("/sentiment", response_model=MarketSentimentResponse)
async def get_market_sentiment(
    db: AsyncSession = Depends(get_db),
) -> MarketSentimentResponse:
    """Get current market sentiment analysis.

    Returns the latest market sentiment including:
    - Major index performance (S&P 500, NASDAQ, Dow Jones)
    - Overall market sentiment score
    - Hot and negative sectors
    - Top market news
    """
    # Get the latest sentiment
    stmt = select(MarketSentiment).order_by(MarketSentiment.date.desc()).limit(1)
    result = await db.execute(stmt)
    sentiment = result.scalar_one_or_none()

    if not sentiment:
        return MarketSentimentResponse(
            date=date.today(),
            message="No sentiment data available. Run market analysis first.",
        )

    return MarketSentimentResponse(
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
