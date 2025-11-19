"""CRUD operations for database models."""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.app.db.models import (
    Fund,
    FundHolding,
    MarketSentiment,
    StockAnalysis,
    StockPrice,
    ResearchJob,
    DataSource,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Fund CRUD
# =============================================================================

async def get_fund(db: AsyncSession, fund_id: int) -> Fund | None:
    """Get a fund by ID."""
    return await db.get(Fund, fund_id)


async def get_fund_by_cik(db: AsyncSession, cik: str) -> Fund | None:
    """Get a fund by CIK."""
    stmt = select(Fund).where(Fund.cik == cik)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_funds(
    db: AsyncSession,
    category: str | None = None,
    active_only: bool = True,
) -> list[Fund]:
    """Get all funds with optional filtering."""
    stmt = select(Fund).order_by(Fund.category, Fund.priority)

    if category:
        stmt = stmt.where(Fund.category == category)
    if active_only:
        stmt = stmt.where(Fund.is_active == True)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_fund(db: AsyncSession, **kwargs) -> Fund:
    """Create a new fund."""
    fund = Fund(**kwargs)
    db.add(fund)
    await db.commit()
    await db.refresh(fund)
    return fund


async def update_fund(db: AsyncSession, fund_id: int, **kwargs) -> Fund | None:
    """Update a fund."""
    fund = await get_fund(db, fund_id)
    if not fund:
        return None

    for key, value in kwargs.items():
        if hasattr(fund, key):
            setattr(fund, key, value)

    await db.commit()
    await db.refresh(fund)
    return fund


# =============================================================================
# Fund Holdings CRUD
# =============================================================================

async def get_fund_holdings(
    db: AsyncSession,
    fund_id: int,
    filing_date: date | None = None,
    limit: int = 100,
) -> list[FundHolding]:
    """Get holdings for a fund."""
    if not filing_date:
        # Get latest filing date
        date_stmt = select(func.max(FundHolding.filing_date)).where(
            FundHolding.fund_id == fund_id
        )
        result = await db.execute(date_stmt)
        filing_date = result.scalar()

    if not filing_date:
        return []

    stmt = (
        select(FundHolding)
        .where(FundHolding.fund_id == fund_id)
        .where(FundHolding.filing_date == filing_date)
        .order_by(FundHolding.value.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_fund_holdings(
    db: AsyncSession,
    fund_id: int,
    holdings: list[dict[str, Any]],
    filing_date: date,
) -> int:
    """Create multiple fund holdings."""
    count = 0
    for holding_data in holdings:
        holding = FundHolding(
            fund_id=fund_id,
            filing_date=filing_date,
            **holding_data,
        )
        db.add(holding)
        count += 1

    await db.commit()
    return count


async def get_ticker_fund_ownership(
    db: AsyncSession,
    ticker: str,
) -> list[dict[str, Any]]:
    """Get all funds that own a specific ticker."""
    # Get latest filing for each fund
    subquery = (
        select(
            FundHolding.fund_id,
            func.max(FundHolding.filing_date).label("latest_date"),
        )
        .group_by(FundHolding.fund_id)
        .subquery()
    )

    stmt = (
        select(FundHolding, Fund)
        .join(Fund, Fund.id == FundHolding.fund_id)
        .join(
            subquery,
            and_(
                FundHolding.fund_id == subquery.c.fund_id,
                FundHolding.filing_date == subquery.c.latest_date,
            ),
        )
        .where(FundHolding.ticker == ticker.upper())
        .order_by(FundHolding.value.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "fund_name": row.Fund.name,
            "fund_ticker": row.Fund.ticker,
            "shares": row.FundHolding.shares,
            "value": float(row.FundHolding.value),
            "percentage": float(row.FundHolding.percentage) if row.FundHolding.percentage else None,
            "change_type": row.FundHolding.change_type,
        }
        for row in rows
    ]


# =============================================================================
# Market Sentiment CRUD
# =============================================================================

async def get_latest_sentiment(db: AsyncSession) -> MarketSentiment | None:
    """Get the latest market sentiment."""
    stmt = select(MarketSentiment).order_by(MarketSentiment.date.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_sentiment_by_date(
    db: AsyncSession,
    sentiment_date: date,
) -> MarketSentiment | None:
    """Get market sentiment for a specific date."""
    stmt = select(MarketSentiment).where(MarketSentiment.date == sentiment_date)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_sentiment_history(
    db: AsyncSession,
    days: int = 7,
) -> list[MarketSentiment]:
    """Get market sentiment history."""
    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)

    stmt = (
        select(MarketSentiment)
        .where(MarketSentiment.date >= start_date)
        .order_by(MarketSentiment.date.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert_sentiment(db: AsyncSession, **kwargs) -> MarketSentiment:
    """Create or update market sentiment for a date."""
    sentiment_date = kwargs.get("date", date.today())

    existing = await get_sentiment_by_date(db, sentiment_date)
    if existing:
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    sentiment = MarketSentiment(**kwargs)
    db.add(sentiment)
    await db.commit()
    await db.refresh(sentiment)
    return sentiment


# =============================================================================
# Stock Analysis CRUD
# =============================================================================

async def get_stock_analysis(
    db: AsyncSession,
    ticker: str,
    analysis_date: date | None = None,
) -> StockAnalysis | None:
    """Get stock analysis."""
    ticker = ticker.upper()

    if analysis_date:
        stmt = select(StockAnalysis).where(
            StockAnalysis.ticker == ticker,
            StockAnalysis.analysis_date == analysis_date,
        )
    else:
        stmt = (
            select(StockAnalysis)
            .where(StockAnalysis.ticker == ticker)
            .order_by(StockAnalysis.analysis_date.desc())
            .limit(1)
        )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_analysis(db: AsyncSession, ticker: str, **kwargs) -> StockAnalysis:
    """Create or update stock analysis."""
    ticker = ticker.upper()
    analysis_date = kwargs.get("analysis_date", date.today())

    existing = await get_stock_analysis(db, ticker, analysis_date)
    if existing:
        for key, value in kwargs.items():
            if hasattr(existing, key) and key != "ticker":
                setattr(existing, key, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    analysis = StockAnalysis(ticker=ticker, **kwargs)
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


# =============================================================================
# Stock Price CRUD
# =============================================================================

async def get_stock_prices(
    db: AsyncSession,
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
) -> list[StockPrice]:
    """Get stock prices."""
    ticker = ticker.upper()
    stmt = select(StockPrice).where(StockPrice.ticker == ticker)

    if start_date:
        stmt = stmt.where(StockPrice.date >= start_date)
    if end_date:
        stmt = stmt.where(StockPrice.date <= end_date)

    stmt = stmt.order_by(StockPrice.date.desc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert_stock_price(db: AsyncSession, ticker: str, price_date: date, **kwargs) -> StockPrice:
    """Create or update stock price."""
    ticker = ticker.upper()

    stmt = select(StockPrice).where(
        StockPrice.ticker == ticker,
        StockPrice.date == price_date,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    price = StockPrice(ticker=ticker, date=price_date, **kwargs)
    db.add(price)
    await db.commit()
    await db.refresh(price)
    return price


# =============================================================================
# Research Job CRUD
# =============================================================================

async def get_research_job(db: AsyncSession, job_id: str) -> ResearchJob | None:
    """Get a research job by ID."""
    stmt = select(ResearchJob).where(ResearchJob.job_id == job_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_research_job(db: AsyncSession, job_id: str, **kwargs) -> ResearchJob:
    """Create a new research job."""
    job = ResearchJob(job_id=job_id, **kwargs)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_research_job(db: AsyncSession, job_id: str, **kwargs) -> ResearchJob | None:
    """Update a research job."""
    job = await get_research_job(db, job_id)
    if not job:
        return None

    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)

    await db.commit()
    await db.refresh(job)
    return job
