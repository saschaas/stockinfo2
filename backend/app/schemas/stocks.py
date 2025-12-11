"""Pydantic schemas for stock research."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class OllamaModel(BaseModel):
    """Single Ollama model info."""

    name: str
    display_name: str
    size: int = 0
    modified_at: str = ""


class OllamaModelResponse(BaseModel):
    """Response schema for available Ollama models."""

    models: list[OllamaModel]
    default_model: str
    default_available: bool
    error: Optional[str] = None


class StockResearchRequest(BaseModel):
    """Request schema for starting stock research."""

    ticker: str = Field(..., min_length=1, max_length=10)
    include_peers: bool = Field(default=True)
    include_technical: bool = Field(default=True)
    include_ai_analysis: bool = Field(default=True)
    llm_model: Optional[str] = Field(default=None, description="Ollama model to use for AI analysis")

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
    description: str | None = None

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

    # Growth Analysis fields
    portfolio_allocation: float | None = None
    price_target_base: float | None = None
    price_target_optimistic: float | None = None
    price_target_pessimistic: float | None = None
    upside_potential: float | None = None
    composite_score: float | None = None
    fundamental_score: float | None = None
    sentiment_score: float | None = None
    technical_score: float | None = None
    competitive_score: float | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    key_strengths: list[str] | None = None
    key_risks: list[str] | None = None
    catalyst_points: list[str] | None = None
    monitoring_points: list[str] | None = None
    data_completeness_score: float | None = None
    missing_data_categories: list[str] | None = None
    ai_summary: str | None = None
    ai_reasoning: str | None = None

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
            description=obj.description,
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
            # Growth Analysis fields
            portfolio_allocation=float(obj.portfolio_allocation) if obj.portfolio_allocation else None,
            price_target_base=float(obj.price_target_base) if obj.price_target_base else None,
            price_target_optimistic=float(obj.price_target_optimistic) if obj.price_target_optimistic else None,
            price_target_pessimistic=float(obj.price_target_pessimistic) if obj.price_target_pessimistic else None,
            upside_potential=float(obj.upside_potential) if obj.upside_potential else None,
            composite_score=float(obj.composite_score) if obj.composite_score else None,
            fundamental_score=float(obj.fundamental_score) if obj.fundamental_score else None,
            sentiment_score=float(obj.sentiment_score) if obj.sentiment_score else None,
            technical_score=float(obj.technical_score) if obj.technical_score else None,
            competitive_score=float(obj.competitive_score) if obj.competitive_score else None,
            risk_score=float(obj.risk_score) if obj.risk_score else None,
            risk_level=obj.risk_level,
            key_strengths=obj.key_strengths,
            key_risks=obj.key_risks,
            catalyst_points=obj.catalyst_points,
            monitoring_points=obj.monitoring_points,
            data_completeness_score=float(obj.data_completeness_score) if obj.data_completeness_score else None,
            missing_data_categories=obj.missing_data_categories,
            ai_summary=obj.ai_summary,
            ai_reasoning=obj.ai_reasoning,
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


class SectorStatistics(BaseModel):
    """Sector-wide statistics."""

    sector: str
    stock_count: int
    analysis_date_range: dict[str, str]
    averages: dict[str, Optional[float]]
    medians: dict[str, Optional[float]]
    percentiles: dict[str, dict[str, Optional[float]]]
    sample_sizes: dict[str, int]
    warning: Optional[str] = None


class SectorComparisonResponse(BaseModel):
    """Response schema for stock sector comparison."""

    ticker: str
    sector: str
    analysis_date: str
    stock_metrics: dict[str, Optional[float]]
    sector_averages: dict[str, Optional[float]]
    sector_medians: dict[str, Optional[float]]
    percentile_ranks: dict[str, Optional[float]]
    relative_strength: str
    stocks_included: int
    data_freshness: str
    warning: Optional[str] = None
    error: Optional[str] = None


class SectorLeaderResponse(BaseModel):
    """Individual sector leader stock."""

    ticker: str
    company_name: Optional[str]
    analysis_date: str
    composite_score: Optional[float]
    market_cap: Optional[int]


class TechnicalAnalysisRequest(BaseModel):
    """Request schema for technical analysis."""

    ticker: str = Field(..., min_length=1, max_length=10)
    period: str = Field(default="6mo", description="Data period: 1mo, 3mo, 6mo, 1y, 2y")

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class TechnicalAnalysisResponse(BaseModel):
    """Response schema for technical analysis job."""

    job_id: str
    ticker: str
    status: str
    message: str


class TechnicalAnalysisResult(BaseModel):
    """Complete technical analysis result."""

    ticker: str
    analysis_date: datetime
    current_price: float

    # Trend analysis
    trend_direction: str
    trend_strength_score: float
    sma_20: float
    sma_50: float
    sma_200: float
    adx: float
    adx_signal: str
    price_above_sma_20: bool
    price_above_sma_50: bool
    price_above_sma_200: bool
    golden_cross: bool
    death_cross: bool

    # Momentum analysis
    rsi: float
    rsi_signal: str
    macd: float
    macd_signal: float
    macd_histogram: float
    macd_cross: Optional[str]
    stoch_k: float
    stoch_d: float
    stoch_signal: str
    roc: float
    roc_signal: str
    momentum_score: float

    # Volatility analysis
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    bb_signal: str
    price_position: str
    atr: float
    atr_percent: float
    volatility_level: str
    volatility_score: float

    # Volume analysis
    current_volume: int
    avg_volume_20d: int
    volume_ratio: float
    volume_signal: str
    obv: float
    obv_trend: str
    volume_score: float

    # Support/Resistance
    pivot: float
    resistance_1: float
    resistance_2: float
    resistance_3: float
    support_1: float
    support_2: float
    support_3: float
    support_levels: list[float]
    resistance_levels: list[float]
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    support_distance_pct: float
    resistance_distance_pct: float

    # Chart patterns
    patterns: list[str]
    trend_channel: Optional[str]
    consolidation: bool
    breakout_signal: Optional[str]

    # Overall scoring
    trend_score: float
    price_action_score: Optional[float] = None  # Support/Resistance based entry quality score (0-10)
    composite_technical_score: float
    overall_signal: str
    signal_confidence: float

    # Entry Analysis (comprehensive entry point evaluation)
    entry_analysis: Optional[dict[str, Any]] = None

    # Chart data
    chart_data: dict[str, Any]

    # Data sources
    data_sources: dict[str, Any]
