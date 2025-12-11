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


class WebScrapedMarketDataResponse(BaseModel):
    """Response schema for web-scraped market data."""

    date: date
    source_url: str
    source_name: str
    market_summary: str | None = None
    overall_sentiment: float | None = None
    bullish_score: float | None = None
    bearish_score: float | None = None
    trending_sectors: list[dict[str, Any]] = Field(default_factory=list)
    declining_sectors: list[dict[str, Any]] = Field(default_factory=list)
    market_themes: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    confidence_score: float | None = None
    scraping_model: str | None = None
    analysis_model: str | None = None


class CombinedMarketResponse(BaseModel):
    """Combined response with both traditional and web-scraped market data."""

    traditional: MarketSentimentResponse
    web_scraped: WebScrapedMarketDataResponse | None = None
