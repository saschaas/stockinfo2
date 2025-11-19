"""Dagster assets for stock research."""

from pipelines.assets.market_sentiment import market_sentiment_asset
from pipelines.assets.fund_holdings import fund_holdings_asset
from pipelines.assets.stock_prices import stock_prices_asset

__all__ = [
    "market_sentiment_asset",
    "fund_holdings_asset",
    "stock_prices_asset",
]
