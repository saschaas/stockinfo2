"""Pydantic schemas for market sentiment."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class IndexData(BaseModel):
    """Individual index data."""

    close: float | None = None
    change_pct: float | None = None


class MarketSentimentResponse(BaseModel):
    """Response schema for market sentiment."""

    date: date
    indices: dict[str, IndexData] | None = None
    overall_sentiment: float | None = None
    bullish_score: float | None = None
    bearish_score: float | None = None
    hot_sectors: list[dict[str, Any]] = Field(default_factory=list)
    negative_sectors: list[dict[str, Any]] = Field(default_factory=list)
    top_news: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None


class SentimentHistoryItem(BaseModel):
    """Single item in sentiment history."""

    date: date
    sp500_change_pct: float | None = None
    nasdaq_change_pct: float | None = None
    dow_change_pct: float | None = None
    overall_sentiment: float | None = None


class MarketSentimentHistoryResponse(BaseModel):
    """Response schema for market sentiment history."""

    days: int
    history: list[dict[str, Any]]
