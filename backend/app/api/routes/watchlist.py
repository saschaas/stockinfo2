"""Watchlist API routes."""

import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import WatchlistItem
from backend.app.db.session import get_db
from backend.app.services.yahoo_finance import get_yahoo_finance_client
from backend.app.services.alpha_vantage import get_alpha_vantage_client
from backend.app.schemas.watchlist import (
    WatchlistItemCreate,
    WatchlistItemInfo,
    WatchlistResponse,
    WatchlistNewsResponse,
    NewsItem,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _fetch_stock_price(ticker: str) -> dict[str, Any]:
    """Fetch current price data for a ticker from Yahoo Finance."""
    try:
        client = get_yahoo_finance_client()
        info = await client.get_stock_info(ticker)

        current_price = info.get("current_price") or info.get("regularMarketPrice")
        previous_close = info.get("previous_close") or info.get("regularMarketPreviousClose")

        change_amount = None
        change_pct = None
        if current_price and previous_close:
            change_amount = float(current_price) - float(previous_close)
            change_pct = (change_amount / float(previous_close)) * 100

        return {
            "current_price": float(current_price) if current_price else None,
            "previous_close": float(previous_close) if previous_close else None,
            "change_amount": round(change_amount, 2) if change_amount else None,
            "change_pct": round(change_pct, 2) if change_pct else None,
            "company_name": info.get("name"),
        }
    except Exception as e:
        logger.warning("Failed to fetch stock price", ticker=ticker, error=str(e))
        return {
            "current_price": None,
            "previous_close": None,
            "change_amount": None,
            "change_pct": None,
            "company_name": None,
        }


async def _fetch_news_count(ticker: str) -> int:
    """Fetch news count for a ticker from Alpha Vantage."""
    try:
        client = await get_alpha_vantage_client()
        news = await client.get_news_sentiment(tickers=ticker, limit=10)
        return len(news)
    except Exception as e:
        logger.warning("Failed to fetch news count", ticker=ticker, error=str(e))
        return 0


@router.get("/", response_model=WatchlistResponse)
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
) -> WatchlistResponse:
    """Get all watchlist items with current prices and news counts.

    Returns all stocks in the watchlist with real-time price data
    and news counts fetched from external APIs.
    """
    # Get all active watchlist items from DB
    stmt = select(WatchlistItem).where(WatchlistItem.is_active == True).order_by(WatchlistItem.added_at.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        return WatchlistResponse(total=0, items=[])

    # Fetch price and news data for all tickers concurrently
    tickers = [item.ticker for item in items]

    # Create tasks for price fetching
    price_tasks = [_fetch_stock_price(ticker) for ticker in tickers]
    news_tasks = [_fetch_news_count(ticker) for ticker in tickers]

    # Run all tasks concurrently
    all_tasks = price_tasks + news_tasks
    results = await asyncio.gather(*all_tasks, return_exceptions=True)

    # Split results
    price_results = results[:len(tickers)]
    news_results = results[len(tickers):]

    # Build response items
    response_items = []
    for i, item in enumerate(items):
        price_data = price_results[i] if not isinstance(price_results[i], Exception) else {}
        news_count = news_results[i] if not isinstance(news_results[i], Exception) else 0

        # Use company name from DB if available, otherwise from API
        company_name = item.company_name or (price_data.get("company_name") if isinstance(price_data, dict) else None)

        response_items.append(
            WatchlistItemInfo(
                id=item.id,
                ticker=item.ticker,
                company_name=company_name,
                added_at=item.added_at,
                current_price=price_data.get("current_price") if isinstance(price_data, dict) else None,
                previous_close=price_data.get("previous_close") if isinstance(price_data, dict) else None,
                change_amount=price_data.get("change_amount") if isinstance(price_data, dict) else None,
                change_pct=price_data.get("change_pct") if isinstance(price_data, dict) else None,
                news_count=news_count if isinstance(news_count, int) else 0,
            )
        )

    return WatchlistResponse(total=len(response_items), items=response_items)


@router.post("/", response_model=WatchlistItemInfo)
async def add_to_watchlist(
    request: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
) -> WatchlistItemInfo:
    """Add a stock to the watchlist.

    Validates the ticker exists via Yahoo Finance before adding.
    Returns the new watchlist item with current price data.
    """
    ticker = request.ticker.upper().strip()

    # Check if already in watchlist
    existing_stmt = select(WatchlistItem).where(WatchlistItem.ticker == ticker)
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail=f"{ticker} is already in your watchlist")
        else:
            # Reactivate inactive item
            existing.is_active = True
            await db.commit()
            await db.refresh(existing)
            item = existing
    else:
        # Validate ticker exists via Yahoo Finance
        try:
            client = get_yahoo_finance_client()
            info = await client.get_stock_info(ticker)
            if not info.get("current_price") and not info.get("regularMarketPrice"):
                raise HTTPException(status_code=404, detail=f"Stock ticker '{ticker}' not found")
            company_name = info.get("name")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to validate ticker", ticker=ticker, error=str(e))
            raise HTTPException(status_code=404, detail=f"Stock ticker '{ticker}' not found or invalid")

        # Create new watchlist item
        item = WatchlistItem(
            ticker=ticker,
            company_name=company_name,
            is_active=True,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

    # Fetch current price and news
    price_data = await _fetch_stock_price(ticker)
    news_count = await _fetch_news_count(ticker)

    return WatchlistItemInfo(
        id=item.id,
        ticker=item.ticker,
        company_name=item.company_name or price_data.get("company_name"),
        added_at=item.added_at,
        current_price=price_data.get("current_price"),
        previous_close=price_data.get("previous_close"),
        change_amount=price_data.get("change_amount"),
        change_pct=price_data.get("change_pct"),
        news_count=news_count,
    )


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Remove a stock from the watchlist.

    Soft-deletes the item by setting is_active to False.
    """
    stmt = select(WatchlistItem).where(WatchlistItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    # Soft delete
    item.is_active = False
    await db.commit()

    return {"message": f"{item.ticker} removed from watchlist"}


@router.get("/{item_id}/news", response_model=WatchlistNewsResponse)
async def get_stock_news(
    item_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> WatchlistNewsResponse:
    """Get news articles for a watchlist stock.

    Fetches the latest news from Alpha Vantage for the specified ticker.
    """
    # Get watchlist item
    stmt = select(WatchlistItem).where(WatchlistItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    # Fetch news from Alpha Vantage
    try:
        client = await get_alpha_vantage_client()
        articles = await client.get_news_sentiment(tickers=item.ticker, limit=limit)

        news_items = [
            NewsItem(
                title=article.get("title", ""),
                url=article.get("url"),
                source=article.get("source"),
                published_at=article.get("published_at"),
                summary=article.get("summary"),
                sentiment_score=article.get("overall_sentiment"),
                sentiment_label=article.get("overall_sentiment_label"),
            )
            for article in articles
        ]

        return WatchlistNewsResponse(
            ticker=item.ticker,
            news=news_items,
            total=len(news_items),
        )
    except Exception as e:
        logger.error("Failed to fetch news", ticker=item.ticker, error=str(e))
        return WatchlistNewsResponse(
            ticker=item.ticker,
            news=[],
            total=0,
        )
