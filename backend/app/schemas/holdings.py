"""Pydantic schemas for stock holdings tracking."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HoldingItemCreate(BaseModel):
    """Schema for adding a stock to holdings."""

    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    quantity: float = Field(..., gt=0, description="Number of shares owned")
    cost_basis: float | None = Field(None, ge=0, description="Average cost per share")


class HoldingItemUpdate(BaseModel):
    """Schema for updating a holding item."""

    quantity: float | None = Field(None, gt=0, description="Number of shares owned")
    cost_basis: float | None = Field(None, ge=0, description="Average cost per share")


class HoldingOrderItem(BaseModel):
    """Single item in order update request."""

    id: int = Field(..., description="Holding item ID")
    sort_order: int = Field(..., ge=0, description="New sort order position")


class HoldingOrderUpdate(BaseModel):
    """Schema for bulk updating holding item order."""

    items: list[HoldingOrderItem] = Field(..., min_length=1, description="List of items with new sort orders")


class HoldingItemInfo(BaseModel):
    """Holding item with current market data."""

    id: int
    ticker: str
    company_name: str | None = None
    quantity: float
    cost_basis: float | None = None
    added_at: datetime
    sort_order: int = 0  # Custom sort order for user-defined ordering

    # Live market data (from Yahoo Finance)
    current_price: float | None = None
    previous_close: float | None = None
    change_amount: float | None = None
    change_pct: float | None = None

    # Portfolio metrics (calculated from quantity, cost_basis, current_price)
    market_value: float | None = None  # quantity * current_price
    total_cost: float | None = None  # quantity * cost_basis
    profit_loss: float | None = None  # market_value - total_cost
    profit_loss_pct: float | None = None  # (profit_loss / total_cost) * 100

    # News data - recent_news_count is for today and yesterday only (for display in table)
    news_count: int = 0  # Total news count for the modal
    recent_news_count: int = 0  # News from today and yesterday (for table display)
    news_sentiment: str | None = None  # Aggregated sentiment

    # Momentum indicators
    has_golden_cross: bool | None = None
    is_bullish_trend: bool | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None

    # Alert status
    has_triggered_alert: bool = False


class HoldingResponse(BaseModel):
    """Response schema for holdings."""

    total: int
    items: list[HoldingItemInfo]
    # Portfolio summary
    total_market_value: float | None = None
    total_cost: float | None = None
    total_profit_loss: float | None = None
    total_profit_loss_pct: float | None = None


class NewsItem(BaseModel):
    """Single news article."""

    title: str
    url: str | None = None
    source: str | None = None
    published_at: str | None = None
    summary: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None


class HoldingNewsResponse(BaseModel):
    """Response schema for holding news."""

    ticker: str
    news: list[NewsItem]
    total: int
    days_fetched: int = 30  # Number of days of news fetched


# ============== Custom Lines Schemas ==============


class HoldingLineCreate(BaseModel):
    """Schema for creating a custom line (trend or alert)."""

    line_type: Literal["trend", "alert"] = Field(
        ..., description="Type of line: 'trend' for visual reference, 'alert' for price notifications"
    )
    name: str = Field(..., min_length=1, max_length=100, description="Name/label for the line")
    price_level: float = Field(..., gt=0, description="Price level for the horizontal line")
    color: str | None = Field(default=None, description="Hex color for the line (e.g., '#8b5cf6')")


class HoldingLineUpdate(BaseModel):
    """Schema for updating a custom line."""

    name: str | None = Field(None, min_length=1, max_length=100)
    price_level: float | None = Field(None, gt=0)
    color: str | None = None
    is_active: bool | None = None


class HoldingLineResponse(BaseModel):
    """Response schema for a custom line."""

    id: int
    holding_item_id: int
    line_type: str
    name: str
    price_level: float
    color: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============== Technical Analysis Schemas ==============


class TechnicalSummaryResponse(BaseModel):
    """Technical analysis summary for a holding stock."""

    ticker: str
    current_price: float | None = None

    # SMA Trends
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    price_above_sma_20: bool = False
    price_above_sma_50: bool = False
    price_above_sma_200: bool = False
    sma_20_direction: str = "flat"  # "up", "down", "flat"
    sma_50_direction: str = "flat"

    # MACD
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    macd_status: str = "neutral"  # "bullish_crossover", "bearish_crossover", "bullish", "bearish", "neutral"
    histogram_direction: str = "flat"  # "increasing", "decreasing", "flat"

    # Golden cross status
    has_golden_cross: bool = False
    has_death_cross: bool = False


class ChartDataResponse(BaseModel):
    """Chart data for displaying interactive stock chart."""

    ticker: str
    company_name: str | None = None
    dates: list[str]
    ohlcv: dict[str, list[float]]  # {open: [], high: [], low: [], close: [], volume: []}
    moving_averages: dict[str, list[float | None]]  # {sma_20: [], sma_50: [], sma_200: []}
    support_levels: list[float] = []
    resistance_levels: list[float] = []
    custom_lines: list[HoldingLineResponse] = []

    # Entry analysis
    entry_level: float | None = None
    stop_loss: float | None = None
    target_price: float | None = None


# ============== Alert Schemas ==============


class TriggeredAlertResponse(BaseModel):
    """Response schema for a triggered alert."""

    id: int
    line_id: int
    line_name: str
    ticker: str
    price_level: float
    triggered_price: float
    direction: str  # "crossed_up" or "crossed_down"
    triggered_at: datetime
    notified: bool
    dismissed: bool


class TriggeredAlertsResponse(BaseModel):
    """Response schema for list of triggered alerts."""

    alerts: list[TriggeredAlertResponse]
    total: int


# ============== Stock Details Schemas ==============


class HoldingStockDetailsResponse(BaseModel):
    """Comprehensive stock details for holding item."""

    item: HoldingItemInfo
    technical_summary: TechnicalSummaryResponse
    chart_data: ChartDataResponse
    custom_lines: list[HoldingLineResponse]
    triggered_alerts_today: list[TriggeredAlertResponse]
    news: list[NewsItem]
