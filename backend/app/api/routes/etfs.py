"""ETF tracking API routes."""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ETF, ETFHolding
from backend.app.db.session import get_db
from backend.app.schemas.etfs import (
    ETFCreate,
    ETFUpdate,
    ETFInfo,
    ETFListResponse,
    ETFHoldingsResponse,
    ETFChangesResponse,
    ETFUpdateInfo,
    ETFUpdatesResponse,
    ETFRefreshResponse,
    ETFSingleRefreshResponse,
)

router = APIRouter()


# ============================================================================
# List and CRUD Operations
# ============================================================================


@router.get("/", response_model=ETFListResponse)
async def list_etfs(
    category: str | None = Query(default=None, description="Filter by category"),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
) -> ETFListResponse:
    """List all tracked ETFs."""
    stmt = select(ETF).order_by(ETF.category, ETF.priority)

    if category:
        stmt = stmt.where(ETF.category == category)
    if active_only:
        stmt = stmt.where(ETF.is_active == True)

    result = await db.execute(stmt)
    etfs = result.scalars().all()

    return ETFListResponse(
        total=len(etfs),
        etfs=[
            {
                "id": e.id,
                "name": e.name,
                "ticker": e.ticker,
                "url": e.url,
                "category": e.category,
                "priority": e.priority,
                "is_active": e.is_active,
                "last_scrape_at": e.last_scrape_at.isoformat() if e.last_scrape_at else None,
                "last_scrape_success": e.last_scrape_success,
            }
            for e in etfs
        ],
    )


@router.get("/updates", response_model=ETFUpdatesResponse)
async def check_etf_updates(
    since: str | None = Query(default=None, description="ISO timestamp to check for updates since"),
    db: AsyncSession = Depends(get_db),
) -> ETFUpdatesResponse:
    """Check which ETFs have new data since a given timestamp.

    Used by frontend for notification badges.
    """
    # Parse 'since' timestamp
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Get all active ETFs
    stmt = select(ETF).where(ETF.is_active == True)
    result = await db.execute(stmt)
    etfs = result.scalars().all()

    updates = []
    has_any_updates = False

    for etf in etfs:
        # Get latest holding date
        holding_stmt = (
            select(func.max(ETFHolding.holding_date))
            .where(ETFHolding.etf_id == etf.id)
        )
        holding_result = await db.execute(holding_stmt)
        latest_holding_date = holding_result.scalar()

        # Get latest data update (created_at)
        update_stmt = (
            select(func.max(ETFHolding.created_at))
            .where(ETFHolding.etf_id == etf.id)
        )
        update_result = await db.execute(update_stmt)
        last_data_update = update_result.scalar()

        # Check if there's new data since the 'since' timestamp
        has_new_data = False
        if since_dt and last_data_update:
            has_new_data = last_data_update > since_dt
        elif last_data_update and not since_dt:
            # If no since, consider any data as "new" (first load)
            has_new_data = True

        if has_new_data:
            has_any_updates = True

        updates.append(ETFUpdateInfo(
            etf_id=etf.id,
            etf_name=etf.name,
            ticker=etf.ticker,
            latest_holding_date=latest_holding_date.isoformat() if latest_holding_date else None,
            last_data_update=last_data_update.isoformat() if last_data_update else None,
            has_new_data=has_new_data,
        ))

    return ETFUpdatesResponse(
        etfs=updates,
        has_any_updates=has_any_updates,
        checked_at=datetime.now().isoformat(),
    )


# ============================================================================
# Aggregated Holdings and Changes
# ============================================================================


@router.get("/aggregate/holdings", response_model=ETFHoldingsResponse)
async def get_aggregated_holdings(
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ETFHoldingsResponse:
    """Get aggregated holdings across all active ETFs."""
    # Get all active ETFs
    etfs_stmt = select(ETF).where(ETF.is_active == True)
    etfs_result = await db.execute(etfs_stmt)
    active_etfs = etfs_result.scalars().all()

    if not active_etfs:
        return ETFHoldingsResponse(
            etf_id=0,
            etf_name="ALL ETFs",
            holding_date=None,
            holdings=[],
            total_value=0,
        )

    # Get latest holding date across all ETFs
    latest_date_stmt = select(func.max(ETFHolding.holding_date))
    result = await db.execute(latest_date_stmt)
    latest_date = result.scalar()

    if not latest_date:
        return ETFHoldingsResponse(
            etf_id=0,
            etf_name="ALL ETFs",
            holding_date=None,
            holdings=[],
            total_value=0,
        )

    # Aggregate holdings by ticker
    aggregated_holdings: dict[str, dict] = {}
    total_value = 0.0

    for etf in active_etfs:
        # Get latest holding date for this ETF
        etf_latest_stmt = (
            select(func.max(ETFHolding.holding_date))
            .where(ETFHolding.etf_id == etf.id)
        )
        etf_result = await db.execute(etf_latest_stmt)
        etf_latest_date = etf_result.scalar()

        if not etf_latest_date:
            continue

        # Get holdings for this ETF
        holdings_stmt = (
            select(ETFHolding)
            .where(ETFHolding.etf_id == etf.id)
            .where(ETFHolding.holding_date == etf_latest_date)
        )
        holdings_result = await db.execute(holdings_stmt)
        holdings = holdings_result.scalars().all()

        for h in holdings:
            key = h.ticker.upper() if h.ticker else h.company_name

            if key not in aggregated_holdings:
                aggregated_holdings[key] = {
                    "ticker": h.ticker,
                    "company_name": h.company_name,
                    "shares": 0,
                    "market_value": 0.0,
                    "weight_pct": 0.0,
                    "etf_count": 0,
                    "etf_names": [],
                }

            aggregated_holdings[key]["shares"] += h.shares or 0
            aggregated_holdings[key]["market_value"] += float(h.market_value or 0)
            aggregated_holdings[key]["weight_pct"] += float(h.weight_pct or 0)
            aggregated_holdings[key]["etf_count"] += 1
            if etf.name not in aggregated_holdings[key]["etf_names"]:
                aggregated_holdings[key]["etf_names"].append(etf.name)

            total_value += float(h.market_value or 0)

    # Sort by market value and limit
    sorted_holdings = sorted(
        aggregated_holdings.values(),
        key=lambda x: x["market_value"],
        reverse=True,
    )[:limit]

    # Calculate average weight for aggregated holdings
    for h in sorted_holdings:
        if h["etf_count"] > 0:
            h["weight_pct"] = h["weight_pct"] / h["etf_count"]

    return ETFHoldingsResponse(
        etf_id=0,
        etf_name="ALL ETFs",
        holding_date=latest_date,
        holdings=sorted_holdings,
        total_value=total_value,
    )


@router.get("/aggregate/changes", response_model=ETFChangesResponse)
async def get_aggregated_changes(
    db: AsyncSession = Depends(get_db),
) -> ETFChangesResponse:
    """Get aggregated position changes across all active ETFs."""
    # Get all active ETFs
    etfs_stmt = select(ETF).where(ETF.is_active == True)
    etfs_result = await db.execute(etfs_stmt)
    active_etfs = etfs_result.scalars().all()

    if not active_etfs:
        return ETFChangesResponse(
            etf_id=0,
            etf_name="ALL ETFs",
            holding_date=None,
            new_positions=[],
            increased=[],
            decreased=[],
            sold=[],
        )

    new_positions: dict[str, dict] = {}
    increased: dict[str, dict] = {}
    decreased: dict[str, dict] = {}
    sold: dict[str, dict] = {}
    latest_date = None

    for etf in active_etfs:
        # Get latest holding date for this ETF
        etf_latest_stmt = (
            select(func.max(ETFHolding.holding_date))
            .where(ETFHolding.etf_id == etf.id)
        )
        etf_result = await db.execute(etf_latest_stmt)
        etf_latest_date = etf_result.scalar()

        if not etf_latest_date:
            continue

        if latest_date is None or etf_latest_date > latest_date:
            latest_date = etf_latest_date

        # Get holdings with changes
        holdings_stmt = (
            select(ETFHolding)
            .where(ETFHolding.etf_id == etf.id)
            .where(ETFHolding.holding_date == etf_latest_date)
            .where(ETFHolding.change_type.isnot(None))
        )
        holdings_result = await db.execute(holdings_stmt)
        holdings = holdings_result.scalars().all()

        for h in holdings:
            key = h.ticker.upper() if h.ticker else h.company_name
            holding_data = {
                "ticker": h.ticker,
                "company_name": h.company_name,
                "shares": h.shares or 0,
                "market_value": float(h.market_value or 0),
                "weight_pct": float(h.weight_pct or 0),
                "shares_change": h.shares_change,
                "weight_change": float(h.weight_change or 0) if h.weight_change else None,
                "etf_count": 1,
                "etf_names": [etf.name],
            }

            target_dict = None
            if h.change_type == "new":
                target_dict = new_positions
            elif h.change_type == "increased":
                target_dict = increased
            elif h.change_type == "decreased":
                target_dict = decreased
            elif h.change_type == "sold":
                target_dict = sold

            if target_dict is not None:
                if key in target_dict:
                    target_dict[key]["shares"] += holding_data["shares"]
                    target_dict[key]["market_value"] += holding_data["market_value"]
                    target_dict[key]["etf_count"] += 1
                    target_dict[key]["etf_names"].append(etf.name)
                else:
                    target_dict[key] = holding_data

    return ETFChangesResponse(
        etf_id=0,
        etf_name="ALL ETFs",
        holding_date=latest_date,
        new_positions=list(new_positions.values())[:50],
        increased=list(increased.values())[:50],
        decreased=list(decreased.values())[:50],
        sold=list(sold.values())[:50],
    )


# ============================================================================
# Individual ETF Holdings and Changes
# ============================================================================


@router.get("/{etf_id}/holdings", response_model=ETFHoldingsResponse)
async def get_etf_holdings(
    etf_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ETFHoldingsResponse:
    """Get holdings for a specific ETF."""
    # Get ETF
    etf_stmt = select(ETF).where(ETF.id == etf_id)
    etf_result = await db.execute(etf_stmt)
    etf = etf_result.scalar_one_or_none()

    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF with id {etf_id} not found")

    # Get latest holding date
    latest_stmt = (
        select(func.max(ETFHolding.holding_date))
        .where(ETFHolding.etf_id == etf_id)
    )
    latest_result = await db.execute(latest_stmt)
    latest_date = latest_result.scalar()

    if not latest_date:
        return ETFHoldingsResponse(
            etf_id=etf.id,
            etf_name=etf.name,
            holding_date=None,
            holdings=[],
            total_value=0,
        )

    # Get holdings
    holdings_stmt = (
        select(ETFHolding)
        .where(ETFHolding.etf_id == etf_id)
        .where(ETFHolding.holding_date == latest_date)
        .order_by(ETFHolding.market_value.desc())
        .limit(limit)
    )
    holdings_result = await db.execute(holdings_stmt)
    holdings = holdings_result.scalars().all()

    total_value = sum(float(h.market_value or 0) for h in holdings)

    return ETFHoldingsResponse(
        etf_id=etf.id,
        etf_name=etf.name,
        holding_date=latest_date,
        holdings=[
            {
                "ticker": h.ticker,
                "company_name": h.company_name,
                "cusip": h.cusip,
                "shares": h.shares,
                "market_value": float(h.market_value) if h.market_value else None,
                "weight_pct": float(h.weight_pct) if h.weight_pct else None,
                "change_type": h.change_type,
                "shares_change": h.shares_change,
                "weight_change": float(h.weight_change) if h.weight_change else None,
            }
            for h in holdings
        ],
        total_value=total_value,
    )


@router.get("/{etf_id}/changes", response_model=ETFChangesResponse)
async def get_etf_changes(
    etf_id: int,
    db: AsyncSession = Depends(get_db),
) -> ETFChangesResponse:
    """Get position changes for a specific ETF."""
    # Get ETF
    etf_stmt = select(ETF).where(ETF.id == etf_id)
    etf_result = await db.execute(etf_stmt)
    etf = etf_result.scalar_one_or_none()

    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF with id {etf_id} not found")

    # Get latest holding date
    latest_stmt = (
        select(func.max(ETFHolding.holding_date))
        .where(ETFHolding.etf_id == etf_id)
    )
    latest_result = await db.execute(latest_stmt)
    latest_date = latest_result.scalar()

    if not latest_date:
        return ETFChangesResponse(
            etf_id=etf.id,
            etf_name=etf.name,
            holding_date=None,
            new_positions=[],
            increased=[],
            decreased=[],
            sold=[],
        )

    # Get holdings with changes
    holdings_stmt = (
        select(ETFHolding)
        .where(ETFHolding.etf_id == etf_id)
        .where(ETFHolding.holding_date == latest_date)
    )
    holdings_result = await db.execute(holdings_stmt)
    holdings = holdings_result.scalars().all()

    new_positions = []
    increased = []
    decreased = []
    sold = []

    for h in holdings:
        holding_data = {
            "ticker": h.ticker,
            "company_name": h.company_name,
            "shares": h.shares,
            "market_value": float(h.market_value) if h.market_value else None,
            "weight_pct": float(h.weight_pct) if h.weight_pct else None,
            "shares_change": h.shares_change,
            "weight_change": float(h.weight_change) if h.weight_change else None,
        }

        if h.change_type == "new":
            new_positions.append(holding_data)
        elif h.change_type == "increased":
            increased.append(holding_data)
        elif h.change_type == "decreased":
            decreased.append(holding_data)
        elif h.change_type == "sold":
            sold.append(holding_data)

    return ETFChangesResponse(
        etf_id=etf.id,
        etf_name=etf.name,
        holding_date=latest_date,
        new_positions=new_positions,
        increased=increased,
        decreased=decreased,
        sold=sold,
    )


# ============================================================================
# ETF CRUD Operations
# ============================================================================


@router.post("/", response_model=ETFInfo)
async def add_etf(
    data: ETFCreate,
    db: AsyncSession = Depends(get_db),
) -> ETFInfo:
    """Add a new ETF to track."""
    # Check if ETF with same ticker already exists
    existing_stmt = select(ETF).where(ETF.ticker == data.ticker.upper())
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"ETF with ticker {data.ticker} already exists"
            )
        else:
            # Reactivate inactive ETF
            existing.is_active = True
            existing.url = data.url
            existing.agent_command = data.agent_command
            existing.description = data.description
            existing.category = data.category
            existing.updated_at = datetime.now()
            await db.commit()
            await db.refresh(existing)
            return ETFInfo(
                id=existing.id,
                name=existing.name,
                ticker=existing.ticker,
                url=existing.url,
                agent_command=existing.agent_command,
                description=existing.description,
                category=existing.category,
                priority=existing.priority,
                is_active=existing.is_active,
                last_scrape_at=existing.last_scrape_at,
                last_scrape_success=existing.last_scrape_success,
                last_scrape_error=existing.last_scrape_error,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )

    # Get max priority for category
    priority_stmt = (
        select(func.max(ETF.priority))
        .where(ETF.category == data.category)
    )
    priority_result = await db.execute(priority_stmt)
    max_priority = priority_result.scalar() or 0

    # Create new ETF
    etf = ETF(
        name=data.name,
        ticker=data.ticker.upper(),
        url=data.url,
        agent_command=data.agent_command,
        description=data.description,
        category=data.category,
        priority=max_priority + 1,
    )
    db.add(etf)
    await db.commit()
    await db.refresh(etf)

    # Trigger initial data fetch
    from backend.app.tasks.etfs import refresh_single_etf
    refresh_single_etf.delay(etf.id)

    return ETFInfo(
        id=etf.id,
        name=etf.name,
        ticker=etf.ticker,
        url=etf.url,
        agent_command=etf.agent_command,
        description=etf.description,
        category=etf.category,
        priority=etf.priority,
        is_active=etf.is_active,
        last_scrape_at=etf.last_scrape_at,
        last_scrape_success=etf.last_scrape_success,
        last_scrape_error=etf.last_scrape_error,
        created_at=etf.created_at,
        updated_at=etf.updated_at,
    )


@router.put("/{etf_id}", response_model=ETFInfo)
async def update_etf(
    etf_id: int,
    data: ETFUpdate,
    db: AsyncSession = Depends(get_db),
) -> ETFInfo:
    """Update an ETF configuration."""
    stmt = select(ETF).where(ETF.id == etf_id)
    result = await db.execute(stmt)
    etf = result.scalar_one_or_none()

    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF with id {etf_id} not found")

    # Update fields
    if data.name is not None:
        etf.name = data.name
    if data.url is not None:
        etf.url = data.url
    if data.agent_command is not None:
        etf.agent_command = data.agent_command
    if data.description is not None:
        etf.description = data.description
    if data.category is not None:
        etf.category = data.category
    if data.is_active is not None:
        etf.is_active = data.is_active

    etf.updated_at = datetime.now()
    await db.commit()
    await db.refresh(etf)

    return ETFInfo(
        id=etf.id,
        name=etf.name,
        ticker=etf.ticker,
        url=etf.url,
        agent_command=etf.agent_command,
        description=etf.description,
        category=etf.category,
        priority=etf.priority,
        is_active=etf.is_active,
        last_scrape_at=etf.last_scrape_at,
        last_scrape_success=etf.last_scrape_success,
        last_scrape_error=etf.last_scrape_error,
        created_at=etf.created_at,
        updated_at=etf.updated_at,
    )


@router.delete("/{etf_id}")
async def delete_etf(
    etf_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete (deactivate) an ETF."""
    stmt = select(ETF).where(ETF.id == etf_id)
    result = await db.execute(stmt)
    etf = result.scalar_one_or_none()

    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF with id {etf_id} not found")

    etf.is_active = False
    etf.updated_at = datetime.now()
    await db.commit()

    return {"message": f"ETF {etf.ticker} deactivated successfully"}


# ============================================================================
# Refresh Operations
# ============================================================================


@router.post("/refresh", response_model=ETFRefreshResponse)
async def refresh_all_etfs(
    db: AsyncSession = Depends(get_db),
) -> ETFRefreshResponse:
    """Trigger refresh of all active ETFs."""
    from backend.app.tasks.etfs import refresh_all_etfs as refresh_task

    # Count active ETFs
    stmt = select(func.count(ETF.id)).where(ETF.is_active == True)
    result = await db.execute(stmt)
    count = result.scalar() or 0

    # Trigger background task
    refresh_task.delay()

    return ETFRefreshResponse(
        message=f"Refresh started for {count} ETF(s)",
        etfs_queued=count,
    )


@router.post("/{etf_id}/refresh", response_model=ETFSingleRefreshResponse)
async def refresh_single_etf(
    etf_id: int,
    db: AsyncSession = Depends(get_db),
) -> ETFSingleRefreshResponse:
    """Trigger refresh of a single ETF."""
    from backend.app.tasks.etfs import refresh_single_etf as refresh_task

    stmt = select(ETF).where(ETF.id == etf_id)
    result = await db.execute(stmt)
    etf = result.scalar_one_or_none()

    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF with id {etf_id} not found")

    # Trigger background task
    refresh_task.delay(etf_id)

    return ETFSingleRefreshResponse(
        etf_id=etf.id,
        etf_name=etf.name,
        message=f"Refresh started for {etf.ticker}",
        success=True,
    )
