"""Fund holdings Dagster asset."""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any

import yaml
from dagster import asset, Output, MetadataValue
import structlog

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def load_fund_config() -> list[dict[str, Any]]:
    """Load fund configuration from config file."""
    try:
        with open("config/config.yaml", "r") as f:
            config = yaml.safe_load(f)

        funds = []
        for category in ["tech_focused", "general"]:
            for fund in config.get("funds", {}).get(category, []):
                if fund.get("cik"):
                    funds.append({
                        **fund,
                        "category": category,
                    })

        return funds
    except Exception as e:
        logger.error("Failed to load fund config", error=str(e))
        return []


async def fetch_fund_holdings(fund: dict[str, Any]) -> dict[str, Any]:
    """Fetch holdings for a single fund."""
    from backend.app.services.sec_edgar import get_sec_edgar_client

    client = await get_sec_edgar_client()

    try:
        holdings_data = await client.get_fund_holdings_with_changes(fund["cik"])

        return {
            "fund": fund,
            "holdings": holdings_data.get("holdings", []),
            "filing_date": holdings_data.get("filing_date"),
            "previous_date": holdings_data.get("previous_date"),
            "total_value": holdings_data.get("total_value", Decimal(0)),
            "success": True,
        }

    except Exception as e:
        logger.error("Failed to fetch holdings", fund=fund["name"], error=str(e))
        return {
            "fund": fund,
            "holdings": [],
            "error": str(e),
            "success": False,
        }


async def save_holdings_to_db(fund_data: dict[str, Any]) -> int:
    """Save fund holdings to database."""
    from sqlalchemy import select, and_, func
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import Fund, FundHolding

    if not fund_data.get("success") or not fund_data.get("holdings"):
        return 0

    async with async_session_factory() as session:
        fund_info = fund_data["fund"]

        # Get or create fund
        stmt = select(Fund).where(Fund.cik == fund_info["cik"])
        result = await session.execute(stmt)
        fund = result.scalar_one_or_none()

        if not fund:
            fund = Fund(
                name=fund_info["name"],
                ticker=fund_info.get("ticker"),
                cik=fund_info["cik"],
                category=fund_info.get("category", "general"),
                priority=fund_info.get("priority", 10),
            )
            session.add(fund)
            await session.flush()

        filing_date = fund_data.get("filing_date")
        if not filing_date:
            return 0

        # Parse date if string
        if isinstance(filing_date, str):
            filing_date = date.fromisoformat(filing_date)

        # Check if we already have ALL holdings for this filing by counting
        count_stmt = select(func.count(FundHolding.id)).where(
            and_(
                FundHolding.fund_id == fund.id,
                FundHolding.filing_date == filing_date
            )
        )
        result = await session.execute(count_stmt)
        existing_count = result.scalar()

        # If we have holdings and the count matches, skip
        expected_count = len([h for h in fund_data["holdings"] if h.get("shares", 0) != 0])
        if existing_count > 0 and existing_count >= expected_count:
            logger.info(
                "Holdings already exist",
                fund=fund.name,
                date=filing_date,
                count=existing_count
            )
            return 0

        # Add holdings with duplicate checking
        count = 0
        for holding in fund_data["holdings"]:
            # Skip sold positions (shares = 0)
            if holding.get("shares", 0) == 0:
                continue

            ticker = holding.get("ticker") or holding.get("cusip", "")[:10]

            # Check if this specific holding already exists
            check_stmt = select(FundHolding).where(
                and_(
                    FundHolding.fund_id == fund.id,
                    FundHolding.ticker == ticker,
                    FundHolding.filing_date == filing_date
                )
            )
            existing_result = await session.execute(check_stmt)
            if existing_result.scalar_one_or_none():
                # This specific holding already exists, skip it
                continue

            fund_holding = FundHolding(
                fund_id=fund.id,
                ticker=ticker,
                company_name=holding.get("company_name"),
                cusip=holding.get("cusip"),
                filing_date=filing_date,
                shares=holding.get("shares", 0),
                value=holding.get("value", Decimal(0)),
                percentage=Decimal(str(holding.get("percentage", 0))),
                shares_change=holding.get("shares_change"),
                change_type=holding.get("change_type"),
            )
            session.add(fund_holding)
            count += 1

        await session.commit()
        logger.info("Saved holdings", fund=fund.name, count=count)
        return count


@asset(
    description="Fund holdings from SEC 13F filings for tracked funds",
    group_name="funds",
    compute_kind="python",
)
def fund_holdings_asset() -> Output[dict]:
    """Fetch and update fund holdings from SEC 13F filings."""

    async def run():
        logger.info("Starting fund holdings update")

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
                    "total_value": float(fund_data.get("total_value", 0)),
                })

                results["funds_processed"] += 1
                results["total_holdings"] += len(fund_data["holdings"])
            else:
                results["errors"].append({
                    "fund": fund["name"],
                    "error": fund_data.get("error"),
                })

            # Small delay between funds to respect rate limits
            await asyncio.sleep(1)

        logger.info(
            "Completed fund holdings update",
            funds=results["funds_processed"],
            holdings=results["total_holdings"],
        )

        return results

    result = run_async(run())

    return Output(
        value=result,
        metadata={
            "date": MetadataValue.text(result["date"]),
            "funds_processed": MetadataValue.int(result["funds_processed"]),
            "total_holdings": MetadataValue.int(result["total_holdings"]),
            "errors": MetadataValue.int(len(result["errors"])),
        },
    )
