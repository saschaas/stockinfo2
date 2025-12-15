"""Fund tracking API routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundException
from backend.app.db.models import Fund, FundHolding
from backend.app.db.session import get_db
from backend.app.services.cusip_mapper import get_ticker_or_cusip, lookup_cusips_batch, is_cusip
from backend.app.schemas.funds import (
    FundListResponse,
    FundHoldingsResponse,
    FundChangesResponse,
)
from backend.app.services.fund_validator import get_fund_validator

router = APIRouter()


# Request/Response models
class AddFundRequest(BaseModel):
    """Request body for adding a new fund."""

    cik: str = Field(..., description="Central Index Key (CIK)")
    name: str | None = Field(None, description="Optional fund name")
    category: str = Field(default="general", description="Fund category")


class ValidateFundResponse(BaseModel):
    """Response for fund validation."""

    is_valid: bool
    fund_type: str | None
    name: str | None
    has_13f_filings: bool
    latest_filing_date: str | None
    error: str | None


class FundSearchResult(BaseModel):
    """Single search result."""

    cik: str
    name: str
    ticker: str | None
    has_13f_filings: bool
    is_recommended: bool
    latest_filing_date: str | None


class FundSearchResponse(BaseModel):
    """Response for fund search."""

    query: str
    results: list[FundSearchResult]


class AddFundResponse(BaseModel):
    """Response for adding a fund."""

    id: int
    name: str
    cik: str
    fund_type: str
    category: str
    message: str


@router.get("/", response_model=FundListResponse)
async def list_funds(
    category: str | None = Query(default=None, description="Filter by category (tech_focused, general)"),
    active_only: bool = Query(default=True),
    funds_only: bool = Query(default=True, description="Exclude ETFs, show only funds"),
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
    if funds_only:
        stmt = stmt.where(Fund.fund_type == "fund")

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


@router.get("/aggregate/holdings", response_model=FundHoldingsResponse)
async def get_aggregated_holdings(
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> FundHoldingsResponse:
    """Get aggregated holdings across all active funds.

    Returns combined holdings from all funds, aggregated by ticker/company name.
    """
    # Get all active funds
    funds_stmt = select(Fund).where(Fund.is_active == True)
    funds_result = await db.execute(funds_stmt)
    active_funds = funds_result.scalars().all()

    if not active_funds:
        return FundHoldingsResponse(
            fund_id=0,
            fund_name="ALL FUNDS",
            filing_date=None,
            holdings=[],
            total_value=0,
        )

    # Get latest filing date across all funds
    latest_date_stmt = select(func.max(FundHolding.filing_date))
    result = await db.execute(latest_date_stmt)
    latest_date = result.scalar()

    if not latest_date:
        return FundHoldingsResponse(
            fund_id=0,
            fund_name="ALL FUNDS",
            filing_date=None,
            holdings=[],
            total_value=0,
        )

    # Step 1: Aggregate holdings by CUSIP first (without ticker lookup)
    aggregated_holdings: dict[str, dict] = {}
    total_value = 0

    for fund in active_funds:
        # Get latest filing date for this fund
        fund_latest_date_stmt = (
            select(func.max(FundHolding.filing_date))
            .where(FundHolding.fund_id == fund.id)
        )
        fund_result = await db.execute(fund_latest_date_stmt)
        fund_latest_date = fund_result.scalar()

        if not fund_latest_date:
            continue

        # Get holdings for this fund
        holdings_stmt = (
            select(FundHolding)
            .where(FundHolding.fund_id == fund.id)
            .where(FundHolding.filing_date == fund_latest_date)
        )
        holdings_result = await db.execute(holdings_stmt)
        holdings = holdings_result.scalars().all()

        for h in holdings:
            # Use CUSIP + company name as aggregation key
            key = f"{h.ticker}_{h.company_name}"

            if key not in aggregated_holdings:
                aggregated_holdings[key] = {
                    "ticker": h.ticker,
                    "company_name": h.company_name,
                    "shares": 0,
                    "value": 0,
                    "fund_count": 0,
                    "fund_names": [],
                }
            aggregated_holdings[key]["shares"] += h.shares or 0
            aggregated_holdings[key]["value"] += float(h.value)
            aggregated_holdings[key]["fund_count"] += 1
            if fund.name not in aggregated_holdings[key]["fund_names"]:
                aggregated_holdings[key]["fund_names"].append(fund.name)
            total_value += float(h.value)

    # Step 2: Sort by value and get top N + buffer for merging
    # We take more than limit because some might merge after ticker resolution
    sorted_holdings = sorted(
        aggregated_holdings.values(),
        key=lambda x: x["value"],
        reverse=True
    )[:limit * 2]  # Take 2x limit as buffer

    # Step 3: Batch lookup CUSIPs only for the top holdings
    cusips_to_lookup = list(set(
        h["ticker"] for h in sorted_holdings if is_cusip(h["ticker"])
    ))
    cusip_to_ticker_map = await lookup_cusips_batch(cusips_to_lookup)

    # Step 4: Build final list with resolved tickers
    holdings_list = []
    for data in sorted_holdings:
        ticker = data["ticker"]
        if is_cusip(ticker):
            actual_ticker = cusip_to_ticker_map.get(ticker)
        else:
            actual_ticker = ticker

        percentage = (data["value"] / total_value * 100) if total_value > 0 else 0
        holdings_list.append({
            "ticker": ticker,
            "actual_ticker": actual_ticker,
            "company_name": data["company_name"],
            "shares": data["shares"],
            "value": data["value"],
            "percentage": percentage,
            "fund_count": data["fund_count"],
            "fund_names": data["fund_names"],
            "change_type": None,
            "shares_change": None,
        })

    # Limit to requested size
    holdings_list = holdings_list[:limit]

    return FundHoldingsResponse(
        fund_id=0,
        fund_name="ALL FUNDS",
        filing_date=latest_date,
        holdings=holdings_list,
        total_value=total_value,
    )


@router.get("/aggregate/changes", response_model=FundChangesResponse)
async def get_aggregated_changes(
    db: AsyncSession = Depends(get_db),
) -> FundChangesResponse:
    """Get aggregated changes across all active funds.

    Returns combined new positions, increased, decreased, and sold positions
    from all funds, aggregated by ticker.
    """
    # Get all active funds
    funds_stmt = select(Fund).where(Fund.is_active == True)
    funds_result = await db.execute(funds_stmt)
    active_funds = funds_result.scalars().all()

    if not active_funds:
        return FundChangesResponse(
            fund_id=0,
            fund_name="ALL FUNDS",
            filing_date=None,
            new_positions=[],
            increased=[],
            decreased=[],
            sold=[],
        )

    # Get latest filing date across all funds
    latest_date_stmt = select(func.max(FundHolding.filing_date))
    result = await db.execute(latest_date_stmt)
    latest_date = result.scalar()

    if not latest_date:
        return FundChangesResponse(
            fund_id=0,
            fund_name="ALL FUNDS",
            filing_date=None,
            new_positions=[],
            increased=[],
            decreased=[],
            sold=[],
        )

    # Step 1: Aggregate changes by CUSIP first (without ticker lookup)
    aggregated_changes: dict[str, dict[str, dict]] = {
        "new": {},
        "increased": {},
        "decreased": {},
        "sold": {}
    }
    total_portfolio_value = 0

    for fund in active_funds:
        # Get latest filing date for this fund
        fund_latest_date_stmt = (
            select(func.max(FundHolding.filing_date))
            .where(FundHolding.fund_id == fund.id)
        )
        fund_result = await db.execute(fund_latest_date_stmt)
        fund_latest_date = fund_result.scalar()

        if not fund_latest_date:
            continue

        # Get total value for this fund (for percentage calculations)
        total_value_stmt = (
            select(func.sum(FundHolding.value))
            .where(FundHolding.fund_id == fund.id)
            .where(FundHolding.filing_date == fund_latest_date)
        )
        total_result = await db.execute(total_value_stmt)
        fund_total_value = total_result.scalar() or 0
        total_portfolio_value += float(fund_total_value)

        # Get changes for this fund
        holdings_stmt = (
            select(FundHolding)
            .where(FundHolding.fund_id == fund.id)
            .where(FundHolding.filing_date == fund_latest_date)
            .where(FundHolding.change_type.isnot(None))
        )
        holdings_result = await db.execute(holdings_stmt)
        holdings = holdings_result.scalars().all()

        for h in holdings:
            if not h.change_type or h.change_type == "unchanged":
                continue

            # Calculate value_change
            if h.change_type == "new":
                value_change = float(h.value)
            elif h.change_type == "sold":
                value_change = -float(h.value)
            elif h.shares and h.shares_change:
                value_change = (h.shares_change / h.shares) * float(h.value)
            else:
                value_change = 0.0

            # Use CUSIP + company name as aggregation key
            key = f"{h.ticker}_{h.company_name}"
            change_dict = aggregated_changes[h.change_type]

            if key not in change_dict:
                change_dict[key] = {
                    "ticker": h.ticker,
                    "company_name": h.company_name,
                    "shares": 0,
                    "value": 0,
                    "shares_change": 0,
                    "value_change": 0,
                    "fund_count": 0,
                    "fund_names": [],
                }

            change_dict[key]["shares"] += h.shares or 0
            change_dict[key]["value"] += float(h.value)
            change_dict[key]["shares_change"] += h.shares_change or 0
            change_dict[key]["value_change"] += value_change
            change_dict[key]["fund_count"] += 1
            if fund.name not in change_dict[key]["fund_names"]:
                change_dict[key]["fund_names"].append(fund.name)

    # Step 2: Sort each category and get top entries
    TOP_CHANGES_LIMIT = 50
    sorted_changes: dict[str, list[dict]] = {}
    for change_type, changes_dict in aggregated_changes.items():
        sorted_changes[change_type] = sorted(
            changes_dict.values(),
            key=lambda x: abs(x["value_change"]),
            reverse=True
        )[:TOP_CHANGES_LIMIT]

    # Step 3: Collect unique CUSIPs from top changes only
    cusips_to_lookup = set()
    for change_type, changes in sorted_changes.items():
        for data in changes:
            if is_cusip(data["ticker"]):
                cusips_to_lookup.add(data["ticker"])

    # Step 4: Batch lookup CUSIPs
    cusip_to_ticker_map = await lookup_cusips_batch(list(cusips_to_lookup))

    # Step 5: Build final result with resolved tickers
    result_changes: dict[str, list[dict]] = {
        "new": [],
        "increased": [],
        "decreased": [],
        "sold": []
    }

    for change_type, changes in sorted_changes.items():
        for data in changes:
            ticker = data["ticker"]
            if is_cusip(ticker):
                actual_ticker = cusip_to_ticker_map.get(ticker)
            else:
                actual_ticker = ticker

            percentage = (data["value"] / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            result_changes[change_type].append({
                "ticker": ticker,
                "actual_ticker": actual_ticker,
                "company_name": data["company_name"],
                "shares": data["shares"],
                "value": data["value"],
                "shares_change": data["shares_change"],
                "percentage": percentage,
                "value_change": data["value_change"],
                "fund_count": data["fund_count"],
                "fund_names": data["fund_names"],
            })

    return FundChangesResponse(
        fund_id=0,
        fund_name="ALL FUNDS",
        filing_date=latest_date,
        new_positions=result_changes["new"],
        increased=result_changes["increased"],
        decreased=result_changes["decreased"],
        sold=result_changes["sold"],
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

    # Batch lookup CUSIPs
    cusips_to_lookup = list(set(h.ticker for h in holdings if is_cusip(h.ticker)))
    cusip_to_ticker_map = await lookup_cusips_batch(cusips_to_lookup)

    return FundHoldingsResponse(
        fund_id=fund_id,
        fund_name=fund.name,
        filing_date=latest_date,
        holdings=[
            {
                "ticker": h.ticker,
                "actual_ticker": cusip_to_ticker_map.get(h.ticker) if is_cusip(h.ticker) else h.ticker,
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

    # Batch lookup CUSIPs
    cusips_to_lookup = list(set(h.ticker for h in holdings if is_cusip(h.ticker)))
    cusip_to_ticker_map = await lookup_cusips_batch(cusips_to_lookup)

    for h in holdings:
        # Calculate value_change based on change type
        if h.change_type == "new":
            value_change = float(h.value)  # Entire position is new
        elif h.change_type == "sold":
            value_change = -float(h.value)  # Entire position removed
        elif h.shares and h.shares_change:
            # For increased/decreased, calculate proportional value change
            value_change = (h.shares_change / h.shares) * float(h.value)
        else:
            value_change = 0.0

        change_data = {
            "ticker": h.ticker,
            "actual_ticker": cusip_to_ticker_map.get(h.ticker) if is_cusip(h.ticker) else h.ticker,
            "company_name": h.company_name,
            "shares": h.shares,
            "value": float(h.value),
            "shares_change": h.shares_change,
            "percentage": float(h.percentage) if h.percentage else 0.0,
            "value_change": value_change,
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


@router.get("/search", response_model=FundSearchResponse)
async def search_funds(
    query: str = Query(..., min_length=2, description="Search query (name, ticker, or CIK)"),
    limit: int = Query(default=5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> FundSearchResponse:
    """Search for funds in SEC database and local tracked funds.

    Returns matching entities with information about whether they have 13F filings.
    Results from local database are prioritized, followed by results with 13F filings.
    """
    import structlog
    from backend.app.services.sec_edgar import get_sec_edgar_client

    logger = structlog.get_logger(__name__)
    results = []
    seen_ciks = set()

    # First, search local database for matching funds
    query_upper = query.upper()
    query_padded = query.strip().lstrip("0").zfill(10) if query.strip().isdigit() else None

    logger.info("Searching local database", query=query, query_padded=query_padded)

    # Build search conditions
    if query_padded:
        # If query is all digits, search by CIK
        local_stmt = select(Fund).where(Fund.cik == query_padded)
    else:
        # Otherwise search by name, ticker, or CIK substring
        local_stmt = select(Fund).where(
            (Fund.name.ilike(f"%{query}%")) |
            (Fund.ticker.ilike(f"%{query}%")) |
            (Fund.cik.like(f"%{query}%"))
        )

    local_result = await db.execute(local_stmt)
    local_funds = local_result.scalars().all()

    logger.info("Local database search completed", query=query, local_funds_count=len(local_funds))

    # Add local funds first (highest priority)
    for fund in local_funds:
        if fund.cik in seen_ciks:
            continue
        seen_ciks.add(fund.cik)

        # Get latest filing date if available
        latest_filing_stmt = (
            select(func.max(FundHolding.filing_date))
            .where(FundHolding.fund_id == fund.id)
        )
        filing_result = await db.execute(latest_filing_stmt)
        latest_date = filing_result.scalar()

        results.append(
            FundSearchResult(
                cik=fund.cik,
                name=fund.name,
                ticker=fund.ticker,
                has_13f_filings=True,  # Already in database means validated
                is_recommended=True,  # Local funds are always recommended
                latest_filing_date=latest_date.isoformat() if latest_date else None,
            )
        )

    # Then search SEC database for additional matches
    client = await get_sec_edgar_client()
    search_results = await client.search_companies(query, limit * 3)

    # Check each SEC result for 13F filings
    for company in search_results:
        # Skip if already added from local database
        if company["cik"] in seen_ciks:
            continue
        seen_ciks.add(company["cik"])

        has_filings = False
        latest_date = None

        try:
            # Quick check for 13F filings
            filings = await client.get_13f_filings(company["cik"])
            has_filings = len(filings) > 0
            if filings:
                latest_date = filings[0].get("filing_date")
        except Exception:
            # If we can't check filings, assume no filings
            pass

        results.append(
            FundSearchResult(
                cik=company["cik"],
                name=company["name"],
                ticker=company.get("ticker"),
                has_13f_filings=has_filings,
                is_recommended=has_filings,  # Recommend entities with 13F filings
                latest_filing_date=latest_date,
            )
        )

    # Sort results: local funds first, then recommended (with 13F filings), then by name
    results.sort(key=lambda x: (
        x.cik not in [f.cik for f in local_funds],  # Local funds first
        not x.is_recommended,  # Then recommended
        x.name  # Then alphabetically
    ))

    return FundSearchResponse(
        query=query,
        results=results[:limit],
    )


@router.get("/validate/{cik}", response_model=ValidateFundResponse)
async def validate_fund(
    cik: Annotated[str, Path(description="CIK to validate")],
    name: str | None = Query(default=None, description="Optional fund name"),
) -> ValidateFundResponse:
    """Validate that a CIK belongs to a fund with available data.

    Returns validation results including whether the entity is a fund (not ETF)
    and if 13F filing data is available.
    """
    validator = get_fund_validator()
    result = await validator.validate_fund(cik, name)
    return ValidateFundResponse(**result)


@router.post("/", response_model=AddFundResponse)
async def add_fund(
    request: AddFundRequest,
    db: AsyncSession = Depends(get_db),
) -> AddFundResponse:
    """Add a new fund to the tracked list.

    Validates that the CIK belongs to a fund (not ETF) and has available data
    before adding it to the database.
    """
    # Validate the fund first
    validator = get_fund_validator()
    validation = await validator.validate_fund(request.cik, request.name)

    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=validation.get("error", "Fund validation failed"),
        )

    # Check if fund already exists
    cik_padded = request.cik.strip().lstrip("0").zfill(10)
    stmt = select(Fund).where(Fund.cik == cik_padded)
    result = await db.execute(stmt)
    existing_fund = result.scalar_one_or_none()

    if existing_fund:
        # If fund exists but is inactive, reactivate it
        if not existing_fund.is_active:
            existing_fund.is_active = True
            await db.commit()

            # Trigger automatic holdings fetch for the reactivated fund
            from backend.app.tasks.funds import refresh_single_fund

            refresh_single_fund.delay(existing_fund.id)

            return AddFundResponse(
                id=existing_fund.id,
                name=existing_fund.name,
                cik=existing_fund.cik,
                fund_type=existing_fund.fund_type,
                category=existing_fund.category,
                message="Fund reactivated successfully. Holdings are being fetched in the background.",
            )
        else:
            raise HTTPException(
                status_code=409,
                detail="Fund already exists in the tracked list",
            )

    # Get the highest priority for the category
    max_priority_stmt = select(func.max(Fund.priority)).where(
        Fund.category == request.category
    )
    result = await db.execute(max_priority_stmt)
    max_priority = result.scalar() or 0

    # Create new fund
    new_fund = Fund(
        name=validation["name"] or request.name or f"Fund {cik_padded}",
        cik=cik_padded,
        fund_type=validation["fund_type"],
        category=request.category,
        priority=max_priority + 1,
        is_active=True,
    )

    db.add(new_fund)
    await db.commit()
    await db.refresh(new_fund)

    # Trigger automatic holdings fetch for the new fund
    from backend.app.tasks.funds import refresh_single_fund

    refresh_single_fund.delay(new_fund.id)

    return AddFundResponse(
        id=new_fund.id,
        name=new_fund.name,
        cik=new_fund.cik,
        fund_type=new_fund.fund_type,
        category=new_fund.category,
        message="Fund added successfully. Holdings are being fetched in the background.",
    )


@router.delete("/{fund_id}")
async def remove_fund(
    fund_id: Annotated[int, Path(ge=1)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a fund from the tracked list.

    This deactivates the fund rather than deleting it to preserve historical data.
    """
    # Get fund
    fund = await db.get(Fund, fund_id)
    if not fund:
        raise NotFoundException("Fund", str(fund_id))

    # Deactivate the fund
    fund.is_active = False
    await db.commit()

    return {
        "status": "success",
        "message": f"Fund '{fund.name}' has been removed from the tracked list",
        "fund_id": fund_id,
    }
