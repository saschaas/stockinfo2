"""Stock prices Dagster asset."""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

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


async def get_tickers_to_update() -> list[str]:
    """Get list of tickers that need price updates."""
    from sqlalchemy import select, distinct
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import FundHolding, StockAnalysis

    async with async_session_factory() as session:
        # Get tickers from fund holdings
        holdings_stmt = select(distinct(FundHolding.ticker))
        result = await session.execute(holdings_stmt)
        holding_tickers = {row[0] for row in result.fetchall() if row[0]}

        # Get tickers from recent analyses
        analysis_stmt = select(distinct(StockAnalysis.ticker))
        result = await session.execute(analysis_stmt)
        analysis_tickers = {row[0] for row in result.fetchall() if row[0]}

        # Combine and return
        all_tickers = holding_tickers | analysis_tickers

        # Add major indices
        all_tickers.update(["SPY", "QQQ", "DIA", "IWM"])

        return list(all_tickers)


async def fetch_stock_prices(tickers: list[str]) -> list[dict[str, Any]]:
    """Fetch current prices for stocks."""
    from backend.app.services.yahoo_finance import get_yahoo_finance_client

    client = get_yahoo_finance_client()
    results = []

    for ticker in tickers:
        try:
            # Get latest price data
            prices = await client.get_historical_prices(
                ticker,
                period="5d",
                interval="1d",
            )

            if prices:
                latest = prices[-1]
                results.append({
                    "ticker": ticker,
                    "date": latest["date"],
                    "open": latest["open"],
                    "high": latest["high"],
                    "low": latest["low"],
                    "close": latest["close"],
                    "volume": latest["volume"],
                    "success": True,
                })
            else:
                results.append({
                    "ticker": ticker,
                    "error": "No price data",
                    "success": False,
                })

        except Exception as e:
            logger.warning("Failed to fetch price", ticker=ticker, error=str(e))
            results.append({
                "ticker": ticker,
                "error": str(e),
                "success": False,
            })

        # Small delay between requests
        await asyncio.sleep(0.2)

    return results


async def save_prices_to_db(prices: list[dict[str, Any]]) -> int:
    """Save stock prices to database."""
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import StockPrice

    count = 0

    async with async_session_factory() as session:
        for price_data in prices:
            if not price_data.get("success"):
                continue

            ticker = price_data["ticker"]
            price_date = price_data["date"]

            # Parse date if string
            if isinstance(price_date, str):
                price_date = date.fromisoformat(price_date)

            # Check if price already exists
            stmt = select(StockPrice).where(
                StockPrice.ticker == ticker,
                StockPrice.date == price_date,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.open = price_data["open"]
                existing.high = price_data["high"]
                existing.low = price_data["low"]
                existing.close = price_data["close"]
                existing.volume = price_data["volume"]
            else:
                # Create new
                stock_price = StockPrice(
                    ticker=ticker,
                    date=price_date,
                    open=price_data["open"],
                    high=price_data["high"],
                    low=price_data["low"],
                    close=price_data["close"],
                    volume=price_data["volume"],
                    data_source="yahoo_finance",
                )
                session.add(stock_price)

            count += 1

        await session.commit()

    return count


@asset(
    description="Stock prices for tracked tickers",
    group_name="prices",
    compute_kind="python",
)
def stock_prices_asset() -> Output[dict]:
    """Fetch and update stock prices for tracked tickers."""

    async def run():
        logger.info("Starting stock prices update")

        # Get tickers to update
        tickers = await get_tickers_to_update()
        logger.info("Found tickers to update", count=len(tickers))

        if not tickers:
            return {
                "date": date.today().isoformat(),
                "tickers_processed": 0,
                "prices_saved": 0,
            }

        # Fetch prices
        prices = await fetch_stock_prices(tickers)
        successful = [p for p in prices if p.get("success")]
        failed = [p for p in prices if not p.get("success")]

        logger.info(
            "Fetched prices",
            successful=len(successful),
            failed=len(failed),
        )

        # Save to database
        saved_count = await save_prices_to_db(prices)

        result = {
            "date": date.today().isoformat(),
            "tickers_processed": len(tickers),
            "prices_fetched": len(successful),
            "prices_saved": saved_count,
            "failed_tickers": [p["ticker"] for p in failed],
        }

        logger.info("Completed stock prices update", saved=saved_count)
        return result

    result = run_async(run())

    return Output(
        value=result,
        metadata={
            "date": MetadataValue.text(result["date"]),
            "tickers_processed": MetadataValue.int(result["tickers_processed"]),
            "prices_saved": MetadataValue.int(result["prices_saved"]),
            "failed_count": MetadataValue.int(len(result.get("failed_tickers", []))),
        },
    )
