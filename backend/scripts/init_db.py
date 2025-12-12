#!/usr/bin/env python3
"""Database initialization script.

This script initializes the database with:
- All required tables
- Initial fund data from configuration
- Any necessary seed data
"""

import asyncio
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

import yaml
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.db.models import Base, Fund, MarketSentiment
from backend.app.config import settings

logger = structlog.get_logger(__name__)


async def create_tables(engine) -> None:
    """Create all database tables."""
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def load_fund_config() -> list[dict]:
    """Load fund configuration from config file."""
    config_path = project_root / "config" / "config.yaml"

    if not config_path.exists():
        logger.warning("Config file not found, using empty fund list", path=str(config_path))
        return []

    with open(config_path) as f:
        config = yaml.safe_load(f)

    funds = []

    # Load tech-focused funds
    tech_funds = config.get("funds", {}).get("tech_focused", [])
    for i, fund in enumerate(tech_funds):
        funds.append({
            "name": fund["name"],
            "ticker": fund["ticker"],
            "cik": fund["cik"],
            "fund_type": "fund",
            "category": "tech_focused",
            "priority": i + 1,
            "is_active": True,
        })

    # Load general funds
    general_funds = config.get("funds", {}).get("general", [])
    for i, fund in enumerate(general_funds):
        funds.append({
            "name": fund["name"],
            "ticker": fund["ticker"],
            "cik": fund["cik"],
            "fund_type": "fund",
            "category": "general",
            "priority": i + 1,
            "is_active": True,
        })

    return funds


async def seed_funds(session: AsyncSession, funds: list[dict]) -> int:
    """Seed funds into database."""
    count = 0

    for fund_data in funds:
        # Check if fund already exists (use LIMIT 1 to handle duplicates)
        result = await session.execute(
            text("SELECT id FROM funds WHERE cik = :cik LIMIT 1"),
            {"cik": fund_data["cik"]}
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.debug("Fund already exists, skipping", ticker=fund_data["ticker"])
            continue

        fund = Fund(**fund_data)
        session.add(fund)
        count += 1
        logger.info("Added fund", ticker=fund_data["ticker"], name=fund_data["name"])

    await session.commit()
    return count


async def seed_initial_sentiment(session: AsyncSession) -> None:
    """Create initial market sentiment if none exists."""
    result = await session.execute(
        text("SELECT id FROM market_sentiment LIMIT 1")
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.debug("Market sentiment already exists, skipping")
        return

    # Create neutral initial sentiment
    sentiment = MarketSentiment(
        date=date.today(),
        sp500_close=Decimal("0"),
        sp500_change_pct=Decimal("0"),
        nasdaq_close=Decimal("0"),
        nasdaq_change_pct=Decimal("0"),
        dow_close=Decimal("0"),
        dow_change_pct=Decimal("0"),
        overall_sentiment=Decimal("0.5"),
        bullish_score=Decimal("0.5"),
        bearish_score=Decimal("0.5"),
        hot_sectors=[],
        negative_sectors=[],
        top_news=[],
        news_count=0,
    )
    session.add(sentiment)
    await session.commit()
    logger.info("Created initial market sentiment placeholder")


async def verify_connection(engine) -> bool:
    """Verify database connection."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False


async def main() -> int:
    """Main initialization function."""
    logger.info("Starting database initialization...")

    # Create engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )

    # Verify connection
    if not await verify_connection(engine):
        logger.error("Could not connect to database")
        return 1

    logger.info("Database connection verified")

    # Create tables
    await create_tables(engine)

    # Create session
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        # Load and seed funds
        funds = await load_fund_config()
        funds_added = await seed_funds(session, funds)
        logger.info("Fund seeding complete", added=funds_added, total=len(funds))

        # Seed initial sentiment
        await seed_initial_sentiment(session)

    # Close engine
    await engine.dispose()

    logger.info("Database initialization complete")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
