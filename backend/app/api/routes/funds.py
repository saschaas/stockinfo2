"""Fund tracking API routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundException
from backend.app.db.models import Fund, FundHolding
from backend.app.db.session import get_db
from backend.app.schemas.funds import (
    FundListResponse,
    FundHoldingsResponse,
    FundChangesResponse,
)

router = APIRouter()


@router.get("/", response_model=FundListResponse)
async def list_funds(
    category: str | None = Query(default=None, description="Filter by category (tech_focused, general)"),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
) -> FundListResponse:
    """List all tracked funds.

    Returns funds grouped by category with basic information.
    """
    stmt = select(Fund).order_by(Fund.category, Fund.priority)

    if category:
        stmt = stmt.where(Fund.category == category)
    if active_only:
        stmt = stmt.where(Fund.is_active == True)

    result = await db.execute(stmt)
    funds = result.scalars().all()

    return FundListResponse(
        total=len(funds),
        funds=[
            {
                "id": f.id,
                "name": f.name,
                "ticker": f.ticker,
                "cik": f.cik,
                "category": f.category,
                "priority": f.priority,
            }
            for f in funds
        ],
    )


@router.get("/{fund_id}/holdings", response_model=FundHoldingsResponse)
async def get_fund_holdings(
    fund_id: Annotated[int, Path(ge=1)],
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> FundHoldingsResponse:
    """Get current holdings for a fund.

    Returns the latest 13F filing holdings sorted by value.
    """
    # Get fund
    fund = await db.get(Fund, fund_id)
    if not fund:
        raise NotFoundException("Fund", str(fund_id))

    # Get latest filing date for this fund
    latest_date_stmt = (
        select(func.max(FundHolding.filing_date))
        .where(FundHolding.fund_id == fund_id)
    )
    result = await db.execute(latest_date_stmt)
    latest_date = result.scalar()

    if not latest_date:
        return FundHoldingsResponse(
            fund_id=fund_id,
            fund_name=fund.name,
            filing_date=None,
            holdings=[],
            total_value=0,
        )

    # Get holdings for latest filing
    holdings_stmt = (
        select(FundHolding)
        .where(FundHolding.fund_id == fund_id)
        .where(FundHolding.filing_date == latest_date)
        .order_by(FundHolding.value.desc())
        .limit(limit)
    )
    result = await db.execute(holdings_stmt)
    holdings = result.scalars().all()

    # Calculate total value
    total_stmt = (
        select(func.sum(FundHolding.value))
        .where(FundHolding.fund_id == fund_id)
        .where(FundHolding.filing_date == latest_date)
    )
    result = await db.execute(total_stmt)
    total_value = result.scalar() or 0

    return FundHoldingsResponse(
        fund_id=fund_id,
        fund_name=fund.name,
        filing_date=latest_date,
        holdings=[
            {
                "ticker": h.ticker,
                "company_name": h.company_name,
                "shares": h.shares,
                "value": float(h.value),
                "percentage": float(h.percentage) if h.percentage else None,
                "change_type": h.change_type,
                "shares_change": h.shares_change,
            }
            for h in holdings
        ],
        total_value=float(total_value),
    )


@router.get("/{fund_id}/changes", response_model=FundChangesResponse)
async def get_fund_changes(
    fund_id: Annotated[int, Path(ge=1)],
    db: AsyncSession = Depends(get_db),
) -> FundChangesResponse:
    """Get recent changes in fund holdings.

    Returns new positions, increased positions, decreased positions, and sold positions.
    """
    # Get fund
    fund = await db.get(Fund, fund_id)
    if not fund:
        raise NotFoundException("Fund", str(fund_id))

    # Get latest filing date
    latest_date_stmt = (
        select(func.max(FundHolding.filing_date))
        .where(FundHolding.fund_id == fund_id)
    )
    result = await db.execute(latest_date_stmt)
    latest_date = result.scalar()

    if not latest_date:
        return FundChangesResponse(
            fund_id=fund_id,
            fund_name=fund.name,
            filing_date=None,
            new_positions=[],
            increased=[],
            decreased=[],
            sold=[],
        )

    # Get changes by type
    changes = {"new": [], "increased": [], "decreased": [], "sold": []}

    holdings_stmt = (
        select(FundHolding)
        .where(FundHolding.fund_id == fund_id)
        .where(FundHolding.filing_date == latest_date)
        .where(FundHolding.change_type.isnot(None))
        .order_by(FundHolding.value.desc())
    )
    result = await db.execute(holdings_stmt)
    holdings = result.scalars().all()

    for h in holdings:
        change_data = {
            "ticker": h.ticker,
            "company_name": h.company_name,
            "shares": h.shares,
            "value": float(h.value),
            "shares_change": h.shares_change,
        }

        if h.change_type == "new":
            changes["new"].append(change_data)
        elif h.change_type == "increased":
            changes["increased"].append(change_data)
        elif h.change_type == "decreased":
            changes["decreased"].append(change_data)
        elif h.change_type == "sold":
            changes["sold"].append(change_data)

    return FundChangesResponse(
        fund_id=fund_id,
        fund_name=fund.name,
        filing_date=latest_date,
        new_positions=changes["new"],
        increased=changes["increased"],
        decreased=changes["decreased"],
        sold=changes["sold"],
    )


@router.post("/refresh")
async def refresh_fund_holdings(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a refresh of all fund holdings from SEC EDGAR.

    This will queue a job to check for new 13F filings and update holdings.
    """
    from backend.app.tasks.funds import check_fund_holdings

    # Send task to Celery
    task = check_fund_holdings.delay()

    return {
        "status": "queued",
        "message": "Fund holdings refresh has been queued",
        "job_id": task.id,
    }
