"""ETF tracking Celery tasks."""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import structlog

from backend.app.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


async def save_etf_holdings_to_db(etf_id: int, holdings: list[dict], holding_date: date | None) -> int:
    """
    Save ETF holdings to database, calculating changes from previous holdings.

    Args:
        etf_id: ETF database ID
        holdings: List of holding dictionaries
        holding_date: Date of holdings data

    Returns:
        Number of holdings saved
    """
    from sqlalchemy import select, func, and_
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ETF, ETFHolding

    if not holdings:
        return 0

    if holding_date is None:
        holding_date = date.today()

    async with async_session_factory() as session:
        # Check if we already have holdings for this date
        existing_stmt = select(func.count(ETFHolding.id)).where(
            and_(
                ETFHolding.etf_id == etf_id,
                ETFHolding.holding_date == holding_date
            )
        )
        existing_result = await session.execute(existing_stmt)
        existing_count = existing_result.scalar() or 0

        if existing_count > 0:
            logger.info(
                "Holdings already exist for this date",
                etf_id=etf_id,
                holding_date=holding_date,
                count=existing_count
            )
            return 0

        # Get previous holdings for change calculation
        prev_date_stmt = (
            select(func.max(ETFHolding.holding_date))
            .where(ETFHolding.etf_id == etf_id)
            .where(ETFHolding.holding_date < holding_date)
        )
        prev_date_result = await session.execute(prev_date_stmt)
        prev_date = prev_date_result.scalar()

        previous_holdings: dict[str, ETFHolding] = {}
        if prev_date:
            prev_holdings_stmt = (
                select(ETFHolding)
                .where(ETFHolding.etf_id == etf_id)
                .where(ETFHolding.holding_date == prev_date)
            )
            prev_result = await session.execute(prev_holdings_stmt)
            for h in prev_result.scalars().all():
                key = h.ticker.upper() if h.ticker else h.company_name
                previous_holdings[key] = h

        # Track which previous holdings are still present
        current_tickers = set()

        saved_count = 0
        for holding in holdings:
            ticker = holding.get("ticker", "").upper() if holding.get("ticker") else None
            company_name = holding.get("company_name")

            if not ticker and not company_name:
                continue

            key = ticker or company_name
            current_tickers.add(key)

            # Calculate changes
            shares = holding.get("shares")
            weight_pct = holding.get("weight_pct")
            shares_change = None
            weight_change = None
            change_type = None

            prev = previous_holdings.get(key)
            if prev:
                # Existing position
                if shares is not None and prev.shares is not None:
                    shares_change = shares - prev.shares
                    if shares_change > 0:
                        change_type = "increased"
                    elif shares_change < 0:
                        change_type = "decreased"
                    else:
                        change_type = None  # unchanged

                if weight_pct is not None and prev.weight_pct is not None:
                    weight_change = float(weight_pct) - float(prev.weight_pct)
            else:
                # New position
                change_type = "new"

            # Create holding record
            etf_holding = ETFHolding(
                etf_id=etf_id,
                ticker=ticker or "",
                company_name=company_name,
                cusip=holding.get("cusip"),
                holding_date=holding_date,
                shares=shares,
                market_value=Decimal(str(holding.get("market_value", 0))) if holding.get("market_value") else None,
                weight_pct=Decimal(str(weight_pct)) if weight_pct else None,
                shares_change=shares_change,
                weight_change=Decimal(str(weight_change)) if weight_change else None,
                change_type=change_type,
            )
            session.add(etf_holding)
            saved_count += 1

        # Add "sold" entries for positions that are no longer present
        for key, prev in previous_holdings.items():
            if key not in current_tickers:
                sold_holding = ETFHolding(
                    etf_id=etf_id,
                    ticker=prev.ticker,
                    company_name=prev.company_name,
                    cusip=prev.cusip,
                    holding_date=holding_date,
                    shares=0,
                    market_value=Decimal("0"),
                    weight_pct=Decimal("0"),
                    shares_change=-prev.shares if prev.shares else None,
                    weight_change=-prev.weight_pct if prev.weight_pct else None,
                    change_type="sold",
                )
                session.add(sold_holding)
                saved_count += 1

        # Update ETF last_scrape status
        etf = await session.get(ETF, etf_id)
        if etf:
            etf.last_scrape_at = datetime.now()
            etf.last_scrape_success = True
            etf.last_scrape_error = None

        await session.commit()

        logger.info(
            "Saved ETF holdings",
            etf_id=etf_id,
            holding_date=holding_date,
            saved_count=saved_count
        )

        return saved_count


@celery_app.task(name="backend.app.tasks.etfs.refresh_all_etfs")
def refresh_all_etfs() -> dict[str, Any]:
    """Refresh holdings for all active ETFs.

    This task is scheduled to run daily at midnight.
    """
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ETF
    from backend.app.agents.etf_data_agent import ETFDataAgent, ETFExtractionConfig

    async def run():
        logger.info("Starting ETF holdings refresh for all ETFs")

        # Get all active ETFs
        async with async_session_factory() as session:
            stmt = select(ETF).where(ETF.is_active == True)
            result = await session.execute(stmt)
            etfs = result.scalars().all()

            # Copy attributes before session closes
            etf_configs = [
                {
                    "id": e.id,
                    "name": e.name,
                    "ticker": e.ticker,
                    "url": e.url,
                    "agent_command": e.agent_command,
                }
                for e in etfs
            ]

        if not etf_configs:
            logger.info("No active ETFs to refresh")
            return {
                "date": date.today().isoformat(),
                "etfs_processed": 0,
                "total_holdings": 0,
                "errors": ["No ETFs configured"],
            }

        results = {
            "date": date.today().isoformat(),
            "etfs_processed": 0,
            "total_holdings": 0,
            "etf_results": [],
            "errors": [],
        }

        agent = ETFDataAgent()

        try:
            for etf_config in etf_configs:
                logger.info("Processing ETF", name=etf_config["name"], ticker=etf_config["ticker"])

                config = ETFExtractionConfig(
                    etf_id=etf_config["id"],
                    ticker=etf_config["ticker"],
                    name=etf_config["name"],
                    url=etf_config["url"],
                    agent_command=etf_config["agent_command"],
                )

                extraction_result = await agent.extract_holdings(config)

                if extraction_result.success:
                    # Save to database
                    count = await save_etf_holdings_to_db(
                        etf_config["id"],
                        extraction_result.holdings,
                        extraction_result.holding_date
                    )

                    results["etf_results"].append({
                        "etf_id": etf_config["id"],
                        "name": etf_config["name"],
                        "ticker": etf_config["ticker"],
                        "holdings_count": len(extraction_result.holdings),
                        "saved_count": count,
                        "holding_date": extraction_result.holding_date.isoformat() if extraction_result.holding_date else None,
                        "extraction_method": extraction_result.extraction_method,
                    })

                    results["etfs_processed"] += 1
                    results["total_holdings"] += len(extraction_result.holdings)
                else:
                    # Update ETF with error status
                    async with async_session_factory() as session:
                        etf = await session.get(ETF, etf_config["id"])
                        if etf:
                            etf.last_scrape_at = datetime.now()
                            etf.last_scrape_success = False
                            etf.last_scrape_error = extraction_result.error
                            await session.commit()

                    results["errors"].append({
                        "etf_id": etf_config["id"],
                        "name": etf_config["name"],
                        "error": extraction_result.error,
                    })

                # Small delay between ETFs
                await asyncio.sleep(2)

        finally:
            await agent.close()

        logger.info(
            "ETF holdings refresh completed",
            etfs=results["etfs_processed"],
            holdings=results["total_holdings"],
            errors=len(results["errors"]),
        )

        return results

    return run_async(run())


@celery_app.task(name="backend.app.tasks.etfs.refresh_single_etf")
def refresh_single_etf(etf_id: int) -> dict[str, Any]:
    """Refresh holdings for a specific ETF.

    Args:
        etf_id: Database ID of the ETF to refresh

    Returns:
        Refresh results
    """
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ETF
    from backend.app.agents.etf_data_agent import ETFDataAgent, ETFExtractionConfig

    async def run():
        # Get ETF from database
        async with async_session_factory() as session:
            etf = await session.get(ETF, etf_id)
            if not etf:
                return {"error": f"ETF {etf_id} not found"}

            etf_config = {
                "id": etf.id,
                "name": etf.name,
                "ticker": etf.ticker,
                "url": etf.url,
                "agent_command": etf.agent_command,
            }

        logger.info("Refreshing single ETF", name=etf_config["name"], ticker=etf_config["ticker"])

        agent = ETFDataAgent()

        try:
            config = ETFExtractionConfig(
                etf_id=etf_config["id"],
                ticker=etf_config["ticker"],
                name=etf_config["name"],
                url=etf_config["url"],
                agent_command=etf_config["agent_command"],
            )

            extraction_result = await agent.extract_holdings(config)

            if extraction_result.success:
                # Save to database
                count = await save_etf_holdings_to_db(
                    etf_config["id"],
                    extraction_result.holdings,
                    extraction_result.holding_date
                )

                # Update description if extracted
                if extraction_result.description:
                    async with async_session_factory() as session:
                        etf = await session.get(ETF, etf_id)
                        if etf and not etf.description:
                            etf.description = extraction_result.description
                            await session.commit()

                return {
                    "etf_id": etf_config["id"],
                    "name": etf_config["name"],
                    "ticker": etf_config["ticker"],
                    "success": True,
                    "holdings_count": len(extraction_result.holdings),
                    "saved_count": count,
                    "holding_date": extraction_result.holding_date.isoformat() if extraction_result.holding_date else None,
                    "extraction_method": extraction_result.extraction_method,
                    "description_updated": bool(extraction_result.description),
                }
            else:
                # Update ETF with error status
                async with async_session_factory() as session:
                    etf = await session.get(ETF, etf_id)
                    if etf:
                        etf.last_scrape_at = datetime.now()
                        etf.last_scrape_success = False
                        etf.last_scrape_error = extraction_result.error
                        await session.commit()

                return {
                    "etf_id": etf_config["id"],
                    "name": etf_config["name"],
                    "ticker": etf_config["ticker"],
                    "success": False,
                    "error": extraction_result.error,
                }

        finally:
            await agent.close()

    return run_async(run())
