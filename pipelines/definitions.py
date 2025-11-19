"""Dagster definitions for stock research pipelines."""

from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    AssetSelection,
    DefaultScheduleStatus,
)

from pipelines.assets.market_sentiment import market_sentiment_asset
from pipelines.assets.fund_holdings import fund_holdings_asset
from pipelines.assets.stock_prices import stock_prices_asset

# Define jobs
market_sentiment_job = define_asset_job(
    name="market_sentiment_job",
    selection=AssetSelection.assets(market_sentiment_asset),
    description="Fetch and analyze daily market sentiment",
)

fund_holdings_job = define_asset_job(
    name="fund_holdings_job",
    selection=AssetSelection.assets(fund_holdings_asset),
    description="Update fund holdings from SEC 13F filings",
)

stock_prices_job = define_asset_job(
    name="stock_prices_job",
    selection=AssetSelection.assets(stock_prices_asset),
    description="Update stock prices",
)

# Define schedules
market_sentiment_schedule = ScheduleDefinition(
    job=market_sentiment_job,
    cron_schedule="0 16 * * 1-5",  # 4 PM EST weekdays
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)

fund_holdings_schedule = ScheduleDefinition(
    job=fund_holdings_job,
    cron_schedule="0 */4 * * *",  # Every 4 hours
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)

stock_prices_schedule = ScheduleDefinition(
    job=stock_prices_job,
    cron_schedule="*/30 9-16 * * 1-5",  # Every 30 min during market hours
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)

# Dagster definitions
defs = Definitions(
    assets=[
        market_sentiment_asset,
        fund_holdings_asset,
        stock_prices_asset,
    ],
    jobs=[
        market_sentiment_job,
        fund_holdings_job,
        stock_prices_job,
    ],
    schedules=[
        market_sentiment_schedule,
        fund_holdings_schedule,
        stock_prices_schedule,
    ],
)
