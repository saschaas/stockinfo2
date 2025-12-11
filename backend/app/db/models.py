"""SQLAlchemy database models for Stock Research Tool."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base

# Portable JSON type: uses JSONB for PostgreSQL, JSON for SQLite
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


class StockPrice(Base):
    """Stock price data with time-series optimization."""

    __tablename__ = "stock_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    adjusted_close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, default="api")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uix_stock_price_ticker_date"),
        Index("idx_stock_price_ticker_date", "ticker", "date"),
    )


class Fund(Base):
    """Fund/ETF information for tracking."""

    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    cik: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    fund_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="fund"
    )  # fund or etf
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general"
    )  # tech_focused or general
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    holdings: Mapped[list["FundHolding"]] = relationship(
        "FundHolding", back_populates="fund"
    )


class FundHolding(Base):
    """Fund holdings from 13F filings."""

    __tablename__ = "fund_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("funds.id"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    cusip: Mapped[str] = mapped_column(String(20), nullable=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=True)
    shares: Mapped[int] = mapped_column(BigInteger, nullable=False)
    value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )  # Value in USD
    percentage: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), nullable=True
    )  # % of portfolio
    shares_change: Mapped[int] = mapped_column(
        BigInteger, nullable=True
    )  # Change from previous filing
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # new, increased, decreased, sold
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    fund: Mapped["Fund"] = relationship("Fund", back_populates="holdings")

    __table_args__ = (
        Index("idx_holding_fund_date", "fund_id", "filing_date"),
        Index("idx_holding_ticker_date", "ticker", "filing_date"),
    )


class MarketSentiment(Base):
    """Daily market sentiment analysis."""

    __tablename__ = "market_sentiment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    # Index values
    sp500_close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    sp500_change_pct: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)
    nasdaq_close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    nasdaq_change_pct: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)
    dow_close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    dow_change_pct: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)

    # Sentiment scores (0-1 scale)
    overall_sentiment: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)
    bullish_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)
    bearish_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)

    # Sector analysis
    hot_sectors: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    negative_sectors: Mapped[dict] = mapped_column(PortableJSON, nullable=True)

    # News summary
    top_news: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    news_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # source_metadata
    analysis_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ollama"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WebScrapedMarketData(Base):
    """Market data extracted from web scraping with AI analysis."""

    __tablename__ = "web_scraped_market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    # Source information
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "market_overview_perplexity"
    data_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="market_overview"
    )

    # Raw scraped data
    raw_scraped_data: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    scraping_model: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # LLM used for extraction

    # AI analysis results
    market_summary: Mapped[str] = mapped_column(Text, nullable=True)
    overall_sentiment: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)
    bullish_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)
    bearish_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)

    # Sector analysis
    trending_sectors: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    declining_sectors: Mapped[list] = mapped_column(PortableJSON, nullable=True)

    # Market themes/narratives
    market_themes: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    key_events: Mapped[list] = mapped_column(PortableJSON, nullable=True)

    # Analysis metadata
    analysis_model: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # LLM used for analysis
    analysis_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Quality indicators
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)
    data_completeness: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # 0-100

    # Extraction metadata
    extraction_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="mcp_playwright"
    )
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StockAnalysis(Base):
    """Comprehensive stock analysis results."""

    __tablename__ = "stock_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Company info
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Valuation metrics
    pe_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    forward_pe: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    peg_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    price_to_book: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    debt_to_equity: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    market_cap: Mapped[int] = mapped_column(BigInteger, nullable=True)

    # Technical indicators
    rsi: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)
    macd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    macd_signal: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    sma_20: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    sma_50: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    sma_200: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    bollinger_upper: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    bollinger_lower: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)

    # Price data
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    target_price_6m: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    price_change_1d: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)
    price_change_1w: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)
    price_change_1m: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)
    price_change_ytd: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=True)

    # Fund ownership
    fund_ownership: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    total_fund_shares: Mapped[int] = mapped_column(BigInteger, nullable=True)

    # AI analysis
    recommendation: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # strong_buy, buy, hold, sell, strong_sell
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=True)
    recommendation_reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    risks: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    opportunities: Mapped[list] = mapped_column(PortableJSON, nullable=True)

    # Growth analysis (comprehensive multi-factor analysis)
    portfolio_allocation: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # Suggested % of portfolio
    price_target_base: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    price_target_optimistic: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    price_target_pessimistic: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=True)
    upside_potential: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=True)  # % to base target

    # Scoring breakdown
    composite_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10
    fundamental_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10
    technical_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10
    competitive_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 1-10 (higher = riskier)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=True)  # low, moderate, high, very high

    # Key insights
    key_strengths: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    key_risks: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    catalyst_points: Mapped[list] = mapped_column(PortableJSON, nullable=True)
    monitoring_points: Mapped[list] = mapped_column(PortableJSON, nullable=True)

    # Data quality
    data_completeness_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    missing_data_categories: Mapped[list] = mapped_column(PortableJSON, nullable=True)

    # AI qualitative analysis
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)
    ai_reasoning: Mapped[str] = mapped_column(Text, nullable=True)

    # Peer comparison
    peer_comparison: Mapped[dict] = mapped_column(PortableJSON, nullable=True)

    # Technical analysis (comprehensive)
    technical_analysis: Mapped[dict] = mapped_column(PortableJSON, nullable=True)

    # Data provenance
    data_sources: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_analysis_ticker_date", "ticker", "analysis_date"),
        UniqueConstraint(
            "ticker", "analysis_date", name="uix_analysis_ticker_date"
        ),
    )


class DataSource(Base):
    """Track data provenance for transparency."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # stock_price, analysis, etc.
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # api, mcp_playwright, vision
    source_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # alpha_vantage, yahoo, etc.
    url: Mapped[str] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    was_cached: Mapped[bool] = mapped_column(Boolean, default=False)
    source_metadata: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_datasource_entity", "entity_type", "entity_id"),)


class ResearchJob(Base):
    """Track research job status for UI progress updates."""

    __tablename__ = "research_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    job_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # stock_research, market_sentiment, etc.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, running, completed, failed
    progress: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0-100
    current_step: Mapped[str] = mapped_column(String(200), nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=True)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)

    # Input/Output
    input_data: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    result_data: Mapped[dict] = mapped_column(PortableJSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    error_suggestion: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # AI-generated fix suggestion

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserConfig(Base):
    """User configuration preferences."""

    __tablename__ = "user_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    config_value: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
