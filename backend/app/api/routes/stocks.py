"""Stock research API routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundException
from backend.app.db.models import StockAnalysis, StockPrice
from backend.app.db.session import get_db
from backend.app.schemas.stocks import (
    SectorComparisonResponse,
    SectorLeaderResponse,
    SectorStatistics,
    StockAnalysisResponse,
    StockPriceHistoryResponse,
    StockResearchRequest,
    StockResearchResponse,
)
from backend.app.services.sector_comparison import get_sector_comparison_service

router = APIRouter()


@router.get("/{ticker}", response_model=StockAnalysisResponse)
async def get_stock_analysis(
    ticker: Annotated[str, Path(min_length=1, max_length=10)],
    db: AsyncSession = Depends(get_db),
) -> StockAnalysisResponse:
    """Get the latest analysis for a stock.

    Returns comprehensive stock analysis including:
    - Valuation metrics (P/E, PEG, P/B, etc.)
    - Technical indicators (RSI, MACD, Bollinger Bands)
    - Price performance
    - Fund ownership
    - AI-generated recommendation and reasoning
    """
    ticker = ticker.upper()

    stmt = (
        select(StockAnalysis)
        .where(StockAnalysis.ticker == ticker)
        .order_by(StockAnalysis.analysis_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise NotFoundException("Stock analysis", ticker)

    return StockAnalysisResponse.from_orm(analysis)


@router.get("/{ticker}/prices", response_model=StockPriceHistoryResponse)
async def get_stock_prices(
    ticker: Annotated[str, Path(min_length=1, max_length=10)],
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> StockPriceHistoryResponse:
    """Get historical price data for a stock."""
    ticker = ticker.upper()

    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)

    stmt = (
        select(StockPrice)
        .where(StockPrice.ticker == ticker)
        .where(StockPrice.date >= start_date)
        .order_by(StockPrice.date.asc())
    )
    result = await db.execute(stmt)
    prices = result.scalars().all()

    if not prices:
        raise NotFoundException("Stock prices", ticker)

    return StockPriceHistoryResponse(
        ticker=ticker,
        prices=[
            {
                "date": p.date,
                "open": float(p.open),
                "high": float(p.high),
                "low": float(p.low),
                "close": float(p.close),
                "volume": p.volume,
            }
            for p in prices
        ],
    )


@router.post("/research", response_model=StockResearchResponse)
async def start_stock_research(
    request: StockResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> StockResearchResponse:
    """Start a comprehensive stock research job.

    This will:
    1. Fetch stock data from multiple sources
    2. Download and parse financial statements
    3. Calculate valuation and technical metrics
    4. Compare with industry peers
    5. Generate AI-powered recommendation

    Returns a job ID that can be used to track progress via WebSocket.
    """
    from backend.app.tasks.research import research_stock

    # Send task to Celery
    task = research_stock.delay(
        ticker=request.ticker.upper(),
        include_peers=True,
        include_technical=True,
        include_ai_analysis=True,
    )

    return StockResearchResponse(
        job_id=task.id,
        ticker=request.ticker.upper(),
        status="queued",
        message=f"Research job queued for {request.ticker.upper()}",
    )


@router.get("/{ticker}/peers")
async def get_stock_peers(
    ticker: Annotated[str, Path(min_length=1, max_length=10)],
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get peer stocks for comparison."""
    ticker = ticker.upper()

    # Get the analysis with peer comparison
    stmt = (
        select(StockAnalysis)
        .where(StockAnalysis.ticker == ticker)
        .order_by(StockAnalysis.analysis_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis or not analysis.peer_comparison:
        return {
            "ticker": ticker,
            "peers": [],
            "message": "No peer comparison data available",
        }

    return {
        "ticker": ticker,
        "sector": analysis.sector,
        "industry": analysis.industry,
        "peers": analysis.peer_comparison.get("peers", [])[:limit],
    }


@router.get("/{ticker}/fund-ownership")
async def get_fund_ownership(
    ticker: Annotated[str, Path(min_length=1, max_length=10)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get fund ownership details for a stock."""
    ticker = ticker.upper()

    # Get the analysis with fund ownership
    stmt = (
        select(StockAnalysis)
        .where(StockAnalysis.ticker == ticker)
        .order_by(StockAnalysis.analysis_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise NotFoundException("Stock analysis", ticker)

    return {
        "ticker": ticker,
        "total_fund_shares": analysis.total_fund_shares,
        "funds": analysis.fund_ownership or [],
    }


@router.get("/{ticker}/sector-comparison", response_model=SectorComparisonResponse)
async def get_stock_sector_comparison(
    ticker: Annotated[str, Path(min_length=1, max_length=10)],
    lookback_days: int = Query(default=180, ge=30, le=365, description="Days to look back for sector data"),
    db: AsyncSession = Depends(get_db),
) -> SectorComparisonResponse:
    """Compare stock to its sector averages.

    Returns:
    - Stock's current metrics
    - Sector average and median values
    - Percentile rankings showing where the stock stands in its sector
    - Relative strength assessment
    - Data freshness and sample size information
    """
    ticker = ticker.upper()

    service = get_sector_comparison_service()
    result = await service.compare_stock_to_sector(
        ticker=ticker,
        lookback_days=lookback_days,
    )

    return SectorComparisonResponse(**result)


@router.get("/sectors/{sector}/stats", response_model=SectorStatistics)
async def get_sector_statistics(
    sector: Annotated[str, Path(min_length=1)],
    lookback_days: int = Query(default=180, ge=30, le=365, description="Days to look back for sector data"),
    db: AsyncSession = Depends(get_db),
) -> SectorStatistics:
    """Get comprehensive statistics for a sector.

    Returns:
    - Number of stocks analyzed in the sector
    - Average values for all comparable metrics
    - Median values (less affected by outliers)
    - 25th and 75th percentile values
    - Sample sizes for each metric
    - Date range of included analyses
    """
    service = get_sector_comparison_service()
    result = await service.get_sector_statistics(
        sector=sector,
        lookback_days=lookback_days,
    )

    return SectorStatistics(**result)


@router.get("/sectors/{sector}/leaders", response_model=list[SectorLeaderResponse])
async def get_sector_leaders(
    sector: Annotated[str, Path(min_length=1)],
    metric: str = Query(default="composite_score", description="Metric to rank by"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of top stocks to return"),
    lookback_days: int = Query(default=180, ge=30, le=365, description="Days to look back for sector data"),
    db: AsyncSession = Depends(get_db),
) -> list[SectorLeaderResponse]:
    """Get top performing stocks in a sector by specific metric.

    Available metrics:
    - composite_score: Overall score combining all factors (default)
    - fundamental_score: Financial health and valuation
    - technical_score: Technical indicators
    - pe_ratio: Price to earnings ratio
    - risk_score: Risk assessment (lower is better)
    """
    service = get_sector_comparison_service()
    result = await service.get_sector_leaders(
        sector=sector,
        metric=metric,
        limit=limit,
        lookback_days=lookback_days,
    )

    return [SectorLeaderResponse(**stock) for stock in result]
