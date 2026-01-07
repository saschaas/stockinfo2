"""Watchlist API routes."""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models import WatchlistItem, WatchlistLine, TriggeredAlert
from backend.app.db.session import get_db
from backend.app.services.yahoo_finance import get_yahoo_finance_client
from backend.app.services.alpha_vantage import get_alpha_vantage_client
from backend.app.schemas.watchlist import (
    WatchlistItemCreate,
    WatchlistItemInfo,
    WatchlistResponse,
    WatchlistNewsResponse,
    NewsItem,
    WatchlistLineCreate,
    WatchlistLineUpdate,
    WatchlistLineResponse,
    TechnicalSummaryResponse,
    ChartDataResponse,
    TriggeredAlertResponse,
    TriggeredAlertsResponse,
    WatchlistStockDetailsResponse,
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


async def _calculate_momentum_indicators(ticker: str) -> dict[str, Any]:
    """Calculate momentum indicators (SMA 20/50/200, golden cross, bullish trend).

    Returns dict with:
        - sma_20, sma_50, sma_200: SMA values
        - has_golden_cross: True if SMA 50 > SMA 200
        - is_bullish_trend: True if price > SMA 20 and price > SMA 50
        - current_price: Latest close price
    """
    try:
        client = get_yahoo_finance_client()
        # Fetch 1 year of daily data for accurate SMA 200
        prices_list = await client.get_historical_prices(ticker, period="1y", interval="1d")

        # Convert list to DataFrame
        if not prices_list or len(prices_list) < 50:
            return {
                "sma_20": None,
                "sma_50": None,
                "sma_200": None,
                "has_golden_cross": None,
                "is_bullish_trend": None,
                "current_price": None,
            }

        # Convert list of dicts to DataFrame
        df = pd.DataFrame(prices_list)
        df["close"] = df["close"].astype(float)

        # Calculate SMAs
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        df["sma_200"] = df["close"].rolling(window=200).mean() if len(df) >= 200 else None

        latest = df.iloc[-1]
        current_price = float(latest["close"])
        sma_20 = float(latest["sma_20"]) if pd.notna(latest["sma_20"]) else None
        sma_50 = float(latest["sma_50"]) if pd.notna(latest["sma_50"]) else None
        sma_200 = float(latest["sma_200"]) if "sma_200" in df.columns and pd.notna(latest.get("sma_200")) else None

        # Golden cross: SMA 50 crosses above SMA 200
        has_golden_cross = False
        if sma_50 is not None and sma_200 is not None:
            has_golden_cross = sma_50 > sma_200

        # Bullish trend: Price above SMA 20 and SMA 50
        is_bullish_trend = False
        if sma_20 is not None and sma_50 is not None:
            is_bullish_trend = current_price > sma_20 and current_price > sma_50

        return {
            "sma_20": round(sma_20, 4) if sma_20 else None,
            "sma_50": round(sma_50, 4) if sma_50 else None,
            "sma_200": round(sma_200, 4) if sma_200 else None,
            "has_golden_cross": has_golden_cross,
            "is_bullish_trend": is_bullish_trend,
            "current_price": round(current_price, 4),
        }
    except Exception as e:
        logger.warning("Failed to calculate momentum", ticker=ticker, error=str(e))
        return {
            "sma_20": None,
            "sma_50": None,
            "sma_200": None,
            "has_golden_cross": None,
            "is_bullish_trend": None,
            "current_price": None,
        }


async def _get_chart_data(ticker: str, period: str = "6mo") -> dict[str, Any]:
    """Fetch chart data with OHLCV and calculated indicators.

    Returns dict with:
        - dates: List of date strings
        - ohlcv: Dict with open, high, low, close, volume arrays
        - moving_averages: Dict with sma_20, sma_50, sma_200 arrays
        - support_levels, resistance_levels: Lists of price levels
    """
    try:
        client = get_yahoo_finance_client()
        # Fetch enough data for SMA 200 calculation + display period
        prices_list = await client.get_historical_prices(ticker, period="1y", interval="1d")

        if not prices_list:
            return {
                "dates": [],
                "ohlcv": {"open": [], "high": [], "low": [], "close": [], "volume": []},
                "moving_averages": {"sma_20": [], "sma_50": [], "sma_200": []},
                "support_levels": [],
                "resistance_levels": [],
            }

        # Convert list of dicts to DataFrame
        df = pd.DataFrame(prices_list)
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(int)

        # Calculate SMAs on full data
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        df["sma_200"] = df["close"].rolling(window=200).mean() if len(df) >= 200 else np.nan

        # Limit to display period (approx 130 trading days for 6 months)
        display_days = 130 if period == "6mo" else (65 if period == "3mo" else 252)
        df_display = df.tail(display_days).copy()

        # Calculate simple support/resistance using recent highs/lows
        recent_data = df.tail(50)
        support_levels = []
        resistance_levels = []

        if len(recent_data) > 10:
            # Support: recent lows
            low_quantiles = recent_data["low"].quantile([0.1, 0.25])
            support_levels = [round(float(v), 2) for v in low_quantiles.values]

            # Resistance: recent highs
            high_quantiles = recent_data["high"].quantile([0.75, 0.9])
            resistance_levels = [round(float(v), 2) for v in high_quantiles.values]

        # Convert to response format - use 'date' column from prices_list
        dates = df_display["date"].tolist()
        ohlcv = {
            "open": df_display["open"].round(4).tolist(),
            "high": df_display["high"].round(4).tolist(),
            "low": df_display["low"].round(4).tolist(),
            "close": df_display["close"].round(4).tolist(),
            "volume": df_display["volume"].tolist(),
        }
        moving_averages = {
            "sma_20": [round(v, 4) if pd.notna(v) else None for v in df_display["sma_20"]],
            "sma_50": [round(v, 4) if pd.notna(v) else None for v in df_display["sma_50"]],
            "sma_200": [round(v, 4) if pd.notna(v) else None for v in df_display["sma_200"]],
        }

        return {
            "dates": dates,
            "ohlcv": ohlcv,
            "moving_averages": moving_averages,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
        }
    except Exception as e:
        logger.error("Failed to get chart data", ticker=ticker, error=str(e))
        return {
            "dates": [],
            "ohlcv": {"open": [], "high": [], "low": [], "close": [], "volume": []},
            "moving_averages": {"sma_20": [], "sma_50": [], "sma_200": []},
            "support_levels": [],
            "resistance_levels": [],
        }


async def _get_technical_summary(ticker: str, momentum_data: dict[str, Any]) -> TechnicalSummaryResponse:
    """Get technical analysis summary including MACD status."""
    try:
        client = get_yahoo_finance_client()
        prices_list = await client.get_historical_prices(ticker, period="3mo", interval="1d")

        if not prices_list or len(prices_list) < 30:
            return TechnicalSummaryResponse(
                ticker=ticker,
                current_price=momentum_data.get("current_price"),
                sma_20=momentum_data.get("sma_20"),
                sma_50=momentum_data.get("sma_50"),
                sma_200=momentum_data.get("sma_200"),
                has_golden_cross=momentum_data.get("has_golden_cross", False),
            )

        # Convert list to DataFrame
        df = pd.DataFrame(prices_list)
        df["close"] = df["close"].astype(float)

        # Calculate MACD
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = macd - macd_signal

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        current_price = float(latest["close"])
        sma_20 = momentum_data.get("sma_20")
        sma_50 = momentum_data.get("sma_50")
        sma_200 = momentum_data.get("sma_200")

        # SMA direction (compare to 5 days ago)
        sma_20_series = df["close"].rolling(window=20).mean()
        sma_50_series = df["close"].rolling(window=50).mean()

        sma_20_direction = "flat"
        sma_50_direction = "flat"

        if len(sma_20_series) >= 5:
            sma_20_change = sma_20_series.iloc[-1] - sma_20_series.iloc[-5]
            sma_20_direction = "up" if sma_20_change > 0.5 else ("down" if sma_20_change < -0.5 else "flat")

        if len(sma_50_series) >= 5:
            sma_50_change = sma_50_series.iloc[-1] - sma_50_series.iloc[-5]
            sma_50_direction = "up" if sma_50_change > 0.5 else ("down" if sma_50_change < -0.5 else "flat")

        # MACD status
        latest_macd = float(macd.iloc[-1])
        latest_signal = float(macd_signal.iloc[-1])
        latest_histogram = float(macd_histogram.iloc[-1])
        prev_histogram = float(macd_histogram.iloc[-2]) if len(macd_histogram) > 1 else 0

        # Determine MACD status
        macd_status = "neutral"
        if latest_histogram > 0 and prev_histogram <= 0:
            macd_status = "bullish_crossover"
        elif latest_histogram < 0 and prev_histogram >= 0:
            macd_status = "bearish_crossover"
        elif latest_macd > latest_signal:
            macd_status = "bullish"
        else:
            macd_status = "bearish"

        histogram_direction = "flat"
        if latest_histogram > prev_histogram:
            histogram_direction = "increasing"
        elif latest_histogram < prev_histogram:
            histogram_direction = "decreasing"

        # Golden cross / death cross
        has_golden_cross = momentum_data.get("has_golden_cross", False)
        has_death_cross = False
        if sma_50 is not None and sma_200 is not None:
            has_death_cross = sma_50 < sma_200

        return TechnicalSummaryResponse(
            ticker=ticker,
            current_price=round(current_price, 4),
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            price_above_sma_20=current_price > sma_20 if sma_20 else False,
            price_above_sma_50=current_price > sma_50 if sma_50 else False,
            price_above_sma_200=current_price > sma_200 if sma_200 else False,
            sma_20_direction=sma_20_direction,
            sma_50_direction=sma_50_direction,
            macd=round(latest_macd, 4),
            macd_signal=round(latest_signal, 4),
            macd_histogram=round(latest_histogram, 4),
            macd_status=macd_status,
            histogram_direction=histogram_direction,
            has_golden_cross=has_golden_cross,
            has_death_cross=has_death_cross,
        )
    except Exception as e:
        logger.error("Failed to get technical summary", ticker=ticker, error=str(e))
        return TechnicalSummaryResponse(
            ticker=ticker,
            current_price=momentum_data.get("current_price"),
            sma_20=momentum_data.get("sma_20"),
            sma_50=momentum_data.get("sma_50"),
            sma_200=momentum_data.get("sma_200"),
        )


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

    # Calculate momentum indicators for all tickers
    momentum_tasks = [_calculate_momentum_indicators(ticker) for ticker in tickers]
    momentum_results = await asyncio.gather(*momentum_tasks, return_exceptions=True)

    # Check for triggered alerts today
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    triggered_stmt = (
        select(TriggeredAlert.line_id)
        .join(WatchlistLine)
        .where(
            and_(
                TriggeredAlert.triggered_at >= today_start,
                TriggeredAlert.dismissed == False,
            )
        )
    )
    triggered_result = await db.execute(triggered_stmt)
    triggered_line_ids = set(row[0] for row in triggered_result.fetchall())

    # Get watchlist item IDs that have triggered alerts
    if triggered_line_ids:
        lines_stmt = select(WatchlistLine.watchlist_item_id).where(
            WatchlistLine.id.in_(triggered_line_ids)
        )
        lines_result = await db.execute(lines_stmt)
        alerted_item_ids = set(row[0] for row in lines_result.fetchall())
    else:
        alerted_item_ids = set()

    # Build response items
    response_items = []
    for i, item in enumerate(items):
        price_data = price_results[i] if not isinstance(price_results[i], Exception) else {}
        news_count = news_results[i] if not isinstance(news_results[i], Exception) else 0
        momentum_data = momentum_results[i] if not isinstance(momentum_results[i], Exception) else {}

        # Use company name from DB if available, otherwise from API
        company_name = item.company_name or (price_data.get("company_name") if isinstance(price_data, dict) else None)

        # Update momentum in DB (async, don't wait)
        if isinstance(momentum_data, dict) and momentum_data.get("sma_20"):
            item.has_golden_cross = momentum_data.get("has_golden_cross")
            item.is_bullish_trend = momentum_data.get("is_bullish_trend")
            item.sma_20 = Decimal(str(momentum_data["sma_20"])) if momentum_data.get("sma_20") else None
            item.sma_50 = Decimal(str(momentum_data["sma_50"])) if momentum_data.get("sma_50") else None
            item.sma_200 = Decimal(str(momentum_data["sma_200"])) if momentum_data.get("sma_200") else None
            item.last_momentum_update = datetime.utcnow()

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
                has_golden_cross=momentum_data.get("has_golden_cross") if isinstance(momentum_data, dict) else None,
                is_bullish_trend=momentum_data.get("is_bullish_trend") if isinstance(momentum_data, dict) else None,
                sma_20=momentum_data.get("sma_20") if isinstance(momentum_data, dict) else None,
                sma_50=momentum_data.get("sma_50") if isinstance(momentum_data, dict) else None,
                sma_200=momentum_data.get("sma_200") if isinstance(momentum_data, dict) else None,
                has_triggered_alert=item.id in alerted_item_ids,
            )
        )

    # Commit momentum updates
    await db.commit()

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


# ============== Stock Details Routes ==============


@router.get("/{item_id}/details", response_model=WatchlistStockDetailsResponse)
async def get_stock_details(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> WatchlistStockDetailsResponse:
    """Get comprehensive stock details for a watchlist item.

    Includes: price data, technical analysis, custom lines, alerts, and news.
    """
    # Get watchlist item with lines
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.id == item_id, WatchlistItem.is_active == True)
        .options(selectinload(WatchlistItem.lines))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    # Fetch all data concurrently
    price_task = _fetch_stock_price(item.ticker)
    momentum_task = _calculate_momentum_indicators(item.ticker)
    chart_task = _get_chart_data(item.ticker)
    news_task = _fetch_news_for_details(item.ticker)

    price_data, momentum_data, chart_data, news_data = await asyncio.gather(
        price_task, momentum_task, chart_task, news_task
    )

    # Get technical summary
    technical_summary = await _get_technical_summary(item.ticker, momentum_data)

    # Get custom lines
    custom_lines = [
        WatchlistLineResponse(
            id=line.id,
            watchlist_item_id=line.watchlist_item_id,
            line_type=line.line_type,
            name=line.name,
            price_level=float(line.price_level),
            color=line.color or "#8b5cf6",
            is_active=line.is_active,
            created_at=line.created_at,
            updated_at=line.updated_at,
        )
        for line in item.lines
        if line.is_active
    ]

    # Get today's triggered alerts
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    alert_line_ids = [line.id for line in item.lines if line.line_type == "alert"]
    triggered_alerts_today = []

    if alert_line_ids:
        alerts_stmt = (
            select(TriggeredAlert)
            .where(
                and_(
                    TriggeredAlert.line_id.in_(alert_line_ids),
                    TriggeredAlert.triggered_at >= today_start,
                )
            )
            .order_by(TriggeredAlert.triggered_at.desc())
        )
        alerts_result = await db.execute(alerts_stmt)
        triggered = alerts_result.scalars().all()

        # Build alert responses with line info
        line_map = {line.id: line for line in item.lines}
        triggered_alerts_today = [
            TriggeredAlertResponse(
                id=alert.id,
                line_id=alert.line_id,
                line_name=line_map[alert.line_id].name if alert.line_id in line_map else "Unknown",
                ticker=item.ticker,
                price_level=float(line_map[alert.line_id].price_level) if alert.line_id in line_map else 0,
                triggered_price=float(alert.triggered_price),
                direction=alert.direction,
                triggered_at=alert.triggered_at,
                notified=alert.notified,
                dismissed=alert.dismissed,
            )
            for alert in triggered
        ]

    # Build chart data response with custom lines
    chart_response = ChartDataResponse(
        ticker=item.ticker,
        company_name=item.company_name,
        dates=chart_data.get("dates", []),
        ohlcv=chart_data.get("ohlcv", {}),
        moving_averages=chart_data.get("moving_averages", {}),
        support_levels=chart_data.get("support_levels", []),
        resistance_levels=chart_data.get("resistance_levels", []),
        custom_lines=custom_lines,
    )

    # Build item info
    item_info = WatchlistItemInfo(
        id=item.id,
        ticker=item.ticker,
        company_name=item.company_name or price_data.get("company_name"),
        added_at=item.added_at,
        current_price=price_data.get("current_price"),
        previous_close=price_data.get("previous_close"),
        change_amount=price_data.get("change_amount"),
        change_pct=price_data.get("change_pct"),
        news_count=len(news_data),
        has_golden_cross=momentum_data.get("has_golden_cross"),
        is_bullish_trend=momentum_data.get("is_bullish_trend"),
        sma_20=momentum_data.get("sma_20"),
        sma_50=momentum_data.get("sma_50"),
        sma_200=momentum_data.get("sma_200"),
        has_triggered_alert=len(triggered_alerts_today) > 0,
    )

    return WatchlistStockDetailsResponse(
        item=item_info,
        technical_summary=technical_summary,
        chart_data=chart_response,
        custom_lines=custom_lines,
        triggered_alerts_today=triggered_alerts_today,
        news=news_data,
    )


async def _fetch_news_for_details(ticker: str) -> list[NewsItem]:
    """Fetch news for stock details page (last 30 days)."""
    try:
        client = await get_alpha_vantage_client()
        articles = await client.get_news_sentiment(tickers=ticker, limit=30)

        return [
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
    except Exception as e:
        logger.error("Failed to fetch news for details", ticker=ticker, error=str(e))
        return []


@router.get("/{item_id}/chart-data", response_model=ChartDataResponse)
async def get_chart_data_endpoint(
    item_id: int,
    period: str = Query(default="6mo", regex="^(3mo|6mo|1y)$"),
    db: AsyncSession = Depends(get_db),
) -> ChartDataResponse:
    """Get chart data for a watchlist stock."""
    # Get watchlist item with lines
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.id == item_id, WatchlistItem.is_active == True)
        .options(selectinload(WatchlistItem.lines))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    chart_data = await _get_chart_data(item.ticker, period)

    # Get custom lines
    custom_lines = [
        WatchlistLineResponse(
            id=line.id,
            watchlist_item_id=line.watchlist_item_id,
            line_type=line.line_type,
            name=line.name,
            price_level=float(line.price_level),
            color=line.color or "#8b5cf6",
            is_active=line.is_active,
            created_at=line.created_at,
            updated_at=line.updated_at,
        )
        for line in item.lines
        if line.is_active
    ]

    return ChartDataResponse(
        ticker=item.ticker,
        company_name=item.company_name,
        dates=chart_data.get("dates", []),
        ohlcv=chart_data.get("ohlcv", {}),
        moving_averages=chart_data.get("moving_averages", {}),
        support_levels=chart_data.get("support_levels", []),
        resistance_levels=chart_data.get("resistance_levels", []),
        custom_lines=custom_lines,
    )


@router.get("/{item_id}/technical", response_model=TechnicalSummaryResponse)
async def get_technical_summary_endpoint(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> TechnicalSummaryResponse:
    """Get technical analysis summary for a watchlist stock."""
    stmt = select(WatchlistItem).where(WatchlistItem.id == item_id, WatchlistItem.is_active == True)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    momentum_data = await _calculate_momentum_indicators(item.ticker)
    return await _get_technical_summary(item.ticker, momentum_data)


# ============== Custom Lines Routes ==============


@router.get("/{item_id}/lines", response_model=list[WatchlistLineResponse])
async def get_custom_lines(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[WatchlistLineResponse]:
    """Get all custom lines (trend lines and alerts) for a watchlist stock."""
    # Verify item exists
    item_stmt = select(WatchlistItem).where(WatchlistItem.id == item_id, WatchlistItem.is_active == True)
    item_result = await db.execute(item_stmt)
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    # Get lines
    stmt = select(WatchlistLine).where(
        WatchlistLine.watchlist_item_id == item_id,
        WatchlistLine.is_active == True,
    ).order_by(WatchlistLine.created_at.desc())
    result = await db.execute(stmt)
    lines = result.scalars().all()

    return [
        WatchlistLineResponse(
            id=line.id,
            watchlist_item_id=line.watchlist_item_id,
            line_type=line.line_type,
            name=line.name,
            price_level=float(line.price_level),
            color=line.color or "#8b5cf6",
            is_active=line.is_active,
            created_at=line.created_at,
            updated_at=line.updated_at,
        )
        for line in lines
    ]


@router.post("/{item_id}/lines", response_model=WatchlistLineResponse)
async def create_custom_line(
    item_id: int,
    request: WatchlistLineCreate,
    db: AsyncSession = Depends(get_db),
) -> WatchlistLineResponse:
    """Create a new custom line (trend line or alert)."""
    # Verify item exists
    item_stmt = select(WatchlistItem).where(WatchlistItem.id == item_id, WatchlistItem.is_active == True)
    item_result = await db.execute(item_stmt)
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    # Set default color based on line type
    color = request.color
    if not color:
        color = "#f97316" if request.line_type == "alert" else "#8b5cf6"  # Orange for alerts, purple for trends

    # Create line
    line = WatchlistLine(
        watchlist_item_id=item_id,
        line_type=request.line_type,
        name=request.name,
        price_level=Decimal(str(request.price_level)),
        color=color,
        is_active=True,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)

    logger.info("Created custom line", item_id=item_id, line_type=request.line_type, name=request.name)

    return WatchlistLineResponse(
        id=line.id,
        watchlist_item_id=line.watchlist_item_id,
        line_type=line.line_type,
        name=line.name,
        price_level=float(line.price_level),
        color=line.color,
        is_active=line.is_active,
        created_at=line.created_at,
        updated_at=line.updated_at,
    )


@router.put("/{item_id}/lines/{line_id}", response_model=WatchlistLineResponse)
async def update_custom_line(
    item_id: int,
    line_id: int,
    request: WatchlistLineUpdate,
    db: AsyncSession = Depends(get_db),
) -> WatchlistLineResponse:
    """Update a custom line (e.g., drag to new price level)."""
    # Get line
    stmt = select(WatchlistLine).where(
        WatchlistLine.id == line_id,
        WatchlistLine.watchlist_item_id == item_id,
    )
    result = await db.execute(stmt)
    line = result.scalar_one_or_none()

    if not line:
        raise HTTPException(status_code=404, detail="Custom line not found")

    # Update fields
    if request.name is not None:
        line.name = request.name
    if request.price_level is not None:
        line.price_level = Decimal(str(request.price_level))
    if request.color is not None:
        line.color = request.color
    if request.is_active is not None:
        line.is_active = request.is_active

    await db.commit()
    await db.refresh(line)

    logger.info("Updated custom line", line_id=line_id, updates=request.model_dump(exclude_none=True))

    return WatchlistLineResponse(
        id=line.id,
        watchlist_item_id=line.watchlist_item_id,
        line_type=line.line_type,
        name=line.name,
        price_level=float(line.price_level),
        color=line.color,
        is_active=line.is_active,
        created_at=line.created_at,
        updated_at=line.updated_at,
    )


@router.delete("/{item_id}/lines/{line_id}")
async def delete_custom_line(
    item_id: int,
    line_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a custom line."""
    stmt = select(WatchlistLine).where(
        WatchlistLine.id == line_id,
        WatchlistLine.watchlist_item_id == item_id,
    )
    result = await db.execute(stmt)
    line = result.scalar_one_or_none()

    if not line:
        raise HTTPException(status_code=404, detail="Custom line not found")

    # Hard delete (cascade will remove related triggered_alerts)
    await db.delete(line)
    await db.commit()

    logger.info("Deleted custom line", line_id=line_id)

    return {"message": f"Line '{line.name}' deleted"}


# ============== Alerts Routes ==============


@router.get("/alerts/triggered", response_model=TriggeredAlertsResponse)
async def get_triggered_alerts(
    db: AsyncSession = Depends(get_db),
) -> TriggeredAlertsResponse:
    """Get all triggered alerts for today (not dismissed)."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    stmt = (
        select(TriggeredAlert)
        .join(WatchlistLine)
        .join(WatchlistItem)
        .where(
            and_(
                TriggeredAlert.triggered_at >= today_start,
                TriggeredAlert.dismissed == False,
                WatchlistItem.is_active == True,
            )
        )
        .order_by(TriggeredAlert.triggered_at.desc())
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    # Need to fetch line and item info for each alert
    alert_responses = []
    for alert in alerts:
        # Get line and item
        line_stmt = select(WatchlistLine).where(WatchlistLine.id == alert.line_id)
        line_result = await db.execute(line_stmt)
        line = line_result.scalar_one_or_none()

        if line:
            item_stmt = select(WatchlistItem).where(WatchlistItem.id == line.watchlist_item_id)
            item_result = await db.execute(item_stmt)
            item = item_result.scalar_one_or_none()

            if item:
                alert_responses.append(
                    TriggeredAlertResponse(
                        id=alert.id,
                        line_id=alert.line_id,
                        line_name=line.name,
                        ticker=item.ticker,
                        price_level=float(line.price_level),
                        triggered_price=float(alert.triggered_price),
                        direction=alert.direction,
                        triggered_at=alert.triggered_at,
                        notified=alert.notified,
                        dismissed=alert.dismissed,
                    )
                )

    return TriggeredAlertsResponse(
        alerts=alert_responses,
        total=len(alert_responses),
    )


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Dismiss a triggered alert."""
    stmt = select(TriggeredAlert).where(TriggeredAlert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.dismissed = True
    await db.commit()

    logger.info("Dismissed alert", alert_id=alert_id)

    return {"message": "Alert dismissed"}
