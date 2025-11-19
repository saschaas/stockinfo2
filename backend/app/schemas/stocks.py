"""Pydantic schemas for stock research."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class StockResearchRequest(BaseModel):
    """Request schema for starting stock research."""

    ticker: str = Field(..., min_length=1, max_length=10)
    include_peers: bool = Field(default=True)
    include_technical: bool = Field(default=True)
    include_ai_analysis: bool = Field(default=True)

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class StockResearchResponse(BaseModel):
    """Response schema for stock research job."""

    job_id: str
    ticker: str
    status: str
    message: str


class StockAnalysisResponse(BaseModel):
    """Response schema for stock analysis."""

    ticker: str
    analysis_date: date
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None

    # Valuation metrics
    pe_ratio: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    debt_to_equity: float | None = None
    market_cap: int | None = None

    # Technical indicators
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None

    # Price data
    current_price: float | None = None
    target_price_6m: float | None = None
    price_change_1d: float | None = None
    price_change_1w: float | None = None
    price_change_1m: float | None = None
    price_change_ytd: float | None = None

    # Fund ownership
    fund_ownership: list[dict[str, Any]] | None = None
    total_fund_shares: int | None = None

    # AI analysis
    recommendation: str | None = None
    confidence_score: float | None = None
    recommendation_reasoning: str | None = None
    risks: list[str] | None = None
    opportunities: list[str] | None = None

    # Peer comparison
    peer_comparison: dict[str, Any] | None = None

    # Data sources
    data_sources: dict[str, Any] | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Any) -> "StockAnalysisResponse":
        """Create response from ORM object."""
        return cls(
            ticker=obj.ticker,
            analysis_date=obj.analysis_date,
            company_name=obj.company_name,
            sector=obj.sector,
            industry=obj.industry,
            pe_ratio=float(obj.pe_ratio) if obj.pe_ratio else None,
            forward_pe=float(obj.forward_pe) if obj.forward_pe else None,
            peg_ratio=float(obj.peg_ratio) if obj.peg_ratio else None,
            price_to_book=float(obj.price_to_book) if obj.price_to_book else None,
            debt_to_equity=float(obj.debt_to_equity) if obj.debt_to_equity else None,
            market_cap=obj.market_cap,
            rsi=float(obj.rsi) if obj.rsi else None,
            macd=float(obj.macd) if obj.macd else None,
            macd_signal=float(obj.macd_signal) if obj.macd_signal else None,
            sma_20=float(obj.sma_20) if obj.sma_20 else None,
            sma_50=float(obj.sma_50) if obj.sma_50 else None,
            sma_200=float(obj.sma_200) if obj.sma_200 else None,
            bollinger_upper=float(obj.bollinger_upper) if obj.bollinger_upper else None,
            bollinger_lower=float(obj.bollinger_lower) if obj.bollinger_lower else None,
            current_price=float(obj.current_price) if obj.current_price else None,
            target_price_6m=float(obj.target_price_6m) if obj.target_price_6m else None,
            price_change_1d=float(obj.price_change_1d) if obj.price_change_1d else None,
            price_change_1w=float(obj.price_change_1w) if obj.price_change_1w else None,
            price_change_1m=float(obj.price_change_1m) if obj.price_change_1m else None,
            price_change_ytd=float(obj.price_change_ytd) if obj.price_change_ytd else None,
            fund_ownership=obj.fund_ownership,
            total_fund_shares=obj.total_fund_shares,
            recommendation=obj.recommendation,
            confidence_score=float(obj.confidence_score) if obj.confidence_score else None,
            recommendation_reasoning=obj.recommendation_reasoning,
            risks=obj.risks,
            opportunities=obj.opportunities,
            peer_comparison=obj.peer_comparison,
            data_sources=obj.data_sources,
        )


class PriceData(BaseModel):
    """Single price data point."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockPriceHistoryResponse(BaseModel):
    """Response schema for stock price history."""

    ticker: str
    prices: list[dict[str, Any]]
