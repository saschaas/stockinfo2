"""Pydantic schemas for watchlist tracking."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WatchlistItemCreate(BaseModel):
    """Schema for adding a stock to watchlist."""

    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")


class WatchlistItemInfo(BaseModel):
    """Watchlist item with current market data."""

    id: int
    ticker: str
    company_name: str | None = None
    added_at: datetime

    # Live market data (from Yahoo Finance)
    current_price: float | None = None
    previous_close: float | None = None
    change_amount: float | None = None
    change_pct: float | None = None

    # News data
    news_count: int = 0


class WatchlistResponse(BaseModel):
    """Response schema for watchlist."""

    total: int
    items: list[WatchlistItemInfo]


class NewsItem(BaseModel):
    """Single news article."""

    title: str
    url: str | None = None
    source: str | None = None
    published_at: str | None = None
    summary: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None


class WatchlistNewsResponse(BaseModel):
    """Response schema for watchlist news."""

    ticker: str
    news: list[NewsItem]
    total: int
