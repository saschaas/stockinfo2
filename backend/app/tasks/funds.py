"""Fund tracking Celery tasks."""

import asyncio
from typing import Any

import structlog

from backend.app.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="backend.app.tasks.funds.check_fund_holdings")
def check_fund_holdings() -> dict[str, Any]:
    """Check for new 13F filings and update fund holdings.

    This task is scheduled to run every 4 hours.
    """
    from pipelines.assets.fund_holdings import (
        load_fund_config,
        fetch_fund_holdings,
        save_holdings_to_db,
    )
    from datetime import date

    async def run():
        logger.info("Starting fund holdings check")

        # Load fund configuration
        funds = load_fund_config()
        logger.info("Loaded fund config", count=len(funds))

        if not funds:
            return {
                "date": date.today().isoformat(),
                "funds_processed": 0,
                "total_holdings": 0,
                "errors": ["No funds configured"],
            }

        results = {
            "date": date.today().isoformat(),
            "funds_processed": 0,
            "total_holdings": 0,
            "fund_results": [],
            "errors": [],
        }

        for fund in funds:
            logger.info("Processing fund", name=fund["name"])

            # Fetch holdings
            fund_data = await fetch_fund_holdings(fund)

            if fund_data["success"]:
                # Save to database
                count = await save_holdings_to_db(fund_data)

                results["fund_results"].append({
                    "name": fund["name"],
                    "ticker": fund.get("ticker"),
                    "holdings_count": len(fund_data["holdings"]),
                    "saved_count": count,
                    "filing_date": fund_data.get("filing_date"),
                })

                results["funds_processed"] += 1
                results["total_holdings"] += len(fund_data["holdings"])
            else:
                results["errors"].append({
                    "fund": fund["name"],
                    "error": fund_data.get("error"),
                })

            # Small delay between funds
            await asyncio.sleep(1)

        logger.info(
            "Fund holdings check completed",
            funds=results["funds_processed"],
            holdings=results["total_holdings"],
        )

        return results

    return run_async(run())


@celery_app.task(name="backend.app.tasks.funds.refresh_single_fund")
def refresh_single_fund(fund_id: int) -> dict[str, Any]:
    """Refresh holdings for a specific fund.

    Args:
        fund_id: Database ID of the fund to refresh

    Returns:
        Refresh results
    """
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import Fund
    from pipelines.assets.fund_holdings import fetch_fund_holdings, save_holdings_to_db

    async def run():
        async with async_session_factory() as session:
            fund = await session.get(Fund, fund_id)
            if not fund:
                return {"error": f"Fund {fund_id} not found"}

            fund_config = {
                "name": fund.name,
                "ticker": fund.ticker,
                "cik": fund.cik,
                "category": fund.category,
            }

        logger.info("Refreshing single fund", name=fund.name)

        fund_data = await fetch_fund_holdings(fund_config)

        if fund_data["success"]:
            count = await save_holdings_to_db(fund_data)
            return {
                "fund_id": fund_id,
                "name": fund.name,
                "holdings_count": len(fund_data["holdings"]),
                "saved_count": count,
                "filing_date": fund_data.get("filing_date"),
            }
        else:
            return {
                "fund_id": fund_id,
                "name": fund.name,
                "error": fund_data.get("error"),
            }

    return run_async(run())
