"""Watchlist price alert monitoring Celery tasks."""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytz
import structlog
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from backend.app.celery_app import celery_app
from backend.app.db.session import async_session_factory
from backend.app.db.models import WatchlistItem, WatchlistLine, TriggeredAlert
from backend.app.services.yahoo_finance import get_yahoo_finance_client

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


def is_market_hours() -> bool:
    """Check if current time is within US market hours (9:30 AM - 4:00 PM ET)."""
    eastern = pytz.timezone("America/New_York")
    now = datetime.now(eastern)

    # Weekend check
    if now.weekday() >= 5:
        return False

    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now <= market_close


@celery_app.task(name="backend.app.tasks.alerts.check_watchlist_alerts")
def check_watchlist_alerts() -> dict[str, Any]:
    """Check all active alerts against current prices.

    Runs every 5 minutes during market hours (9:30 AM - 4:00 PM ET, Mon-Fri).
    Creates TriggeredAlert records when prices cross alert levels.

    Returns:
        dict with triggered alerts info
    """

    async def run():
        if not is_market_hours():
            logger.info("Market closed, skipping alert check")
            return {"status": "skipped", "reason": "market_closed"}

        logger.info("Starting watchlist alert check")

        async with async_session_factory() as session:
            # Get all watchlist items with active alert lines
            stmt = (
                select(WatchlistItem)
                .where(WatchlistItem.is_active == True)
                .options(selectinload(WatchlistItem.lines))
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            if not items:
                return {"status": "no_items", "triggered": 0}

            # Filter to items with active alert lines
            items_with_alerts = [
                item for item in items
                if any(line.line_type == "alert" and line.is_active for line in item.lines)
            ]

            if not items_with_alerts:
                logger.info("No watchlist items with active alerts")
                return {"status": "no_alerts", "triggered": 0}

            triggered_count = 0
            triggered_alerts = []
            yahoo_client = get_yahoo_finance_client()
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            for item in items_with_alerts:
                alert_lines = [
                    line for line in item.lines
                    if line.line_type == "alert" and line.is_active
                ]

                if not alert_lines:
                    continue

                try:
                    # Fetch current price
                    info = await yahoo_client.get_stock_info(item.ticker)
                    current_price = info.get("current_price") or info.get("regularMarketPrice")

                    if not current_price:
                        logger.warning("No price data for ticker", ticker=item.ticker)
                        continue

                    current_price = float(current_price)

                    # Get previous close for direction detection
                    previous_close = info.get("previous_close") or info.get("regularMarketPreviousClose")
                    if previous_close:
                        previous_close = float(previous_close)
                    else:
                        previous_close = current_price  # Fallback

                    for line in alert_lines:
                        price_level = float(line.price_level)

                        # Check if already triggered today
                        existing_stmt = select(TriggeredAlert).where(
                            and_(
                                TriggeredAlert.line_id == line.id,
                                TriggeredAlert.triggered_at >= today_start,
                            )
                        )
                        existing_result = await session.execute(existing_stmt)
                        if existing_result.scalar_one_or_none():
                            continue  # Already triggered today

                        # Check if price crossed the alert level
                        # Use previous_close as reference point
                        crossed_up = previous_close < price_level <= current_price
                        crossed_down = previous_close > price_level >= current_price

                        # Also check if current price is at or past the level
                        # (for cases where price moved significantly)
                        at_or_past_up = current_price >= price_level > previous_close
                        at_or_past_down = current_price <= price_level < previous_close

                        if crossed_up or crossed_down or at_or_past_up or at_or_past_down:
                            direction = "crossed_up" if (crossed_up or at_or_past_up) else "crossed_down"

                            # Create triggered alert
                            triggered = TriggeredAlert(
                                line_id=line.id,
                                triggered_price=Decimal(str(current_price)),
                                direction=direction,
                                notified=False,
                                dismissed=False,
                            )
                            session.add(triggered)
                            triggered_count += 1

                            alert_info = {
                                "ticker": item.ticker,
                                "line_name": line.name,
                                "price_level": price_level,
                                "current_price": current_price,
                                "direction": direction,
                            }
                            triggered_alerts.append(alert_info)

                            logger.info(
                                "Alert triggered",
                                ticker=item.ticker,
                                line_name=line.name,
                                price_level=price_level,
                                current_price=current_price,
                                direction=direction,
                            )

                except Exception as e:
                    logger.warning(
                        "Failed to check alerts for ticker",
                        ticker=item.ticker,
                        error=str(e),
                    )
                    continue

            await session.commit()

            logger.info(
                "Watchlist alert check completed",
                items_checked=len(items_with_alerts),
                triggered=triggered_count,
            )

            return {
                "status": "completed",
                "items_checked": len(items_with_alerts),
                "triggered": triggered_count,
                "alerts": triggered_alerts,
            }

    return run_async(run())
