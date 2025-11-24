"""
Peer Comparison Service

Fetches and compares stock metrics against competitors/peers
Uses Yahoo Finance to get peer data and perform comparative analysis
"""

import logging
from typing import Dict, List, Optional, Any
import asyncio

from backend.app.services.yahoo_finance import get_yahoo_finance_client
from backend.app.services.cache import get_cache, TTL_LONG

logger = logging.getLogger(__name__)


class PeerComparisonService:
    """Service for comparing stocks against industry peers"""

    def __init__(self):
        self.yahoo_client = get_yahoo_finance_client()
        self.cache = get_cache()

    async def get_peers_for_stock(
        self,
        ticker: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get peer tickers for a given stock

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of peers to return

        Returns:
            List of peer ticker symbols
        """
        cache_key = f"peers:{ticker}"

        # Check cache
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached[:limit]

        try:
            # Get stock info including sector/industry
            info = await self.yahoo_client.get_stock_info(ticker)

            if not info:
                return []

            sector = info.get("sector", "")
            industry = info.get("industry", "")

            # For now, return empty list - in production, would use:
            # 1. Yahoo Finance recommendations API
            # 2. SEC filing competitors
            # 3. Industry ETF holdings
            # 4. Market cap + sector/industry matching

            # Placeholder - would need proper peer discovery API
            peers = []

            # Cache result
            if self.cache and peers:
                await self.cache.set(cache_key, peers, ttl=TTL_LONG)

            return peers[:limit]

        except Exception as e:
            logger.error(f"Error fetching peers for {ticker}: {e}")
            return []

    async def get_peer_comparison(
        self,
        ticker: str,
        peers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive comparison with peers

        Args:
            ticker: Primary stock ticker
            peers: Optional list of peer tickers (auto-discovered if not provided)

        Returns:
            Dict with comparative metrics
        """
        if not peers:
            peers = await self.get_peers_for_stock(ticker)

        if not peers:
            logger.warning(f"No peers found for {ticker}")
            return {
                "ticker": ticker,
                "peers": [],
                "comparison": {},
                "relative_position": {}
            }

        cache_key = f"peer_comparison:{ticker}:{'-'.join(sorted(peers))}"

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        try:
            # Fetch data for primary ticker and all peers
            all_tickers = [ticker] + peers

            # Fetch in parallel
            tasks = [self.yahoo_client.get_stock_info(t) for t in all_tickers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out errors
            ticker_data = {}
            for t, result in zip(all_tickers, results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch data for {t}: {result}")
                    continue
                if result:
                    ticker_data[t] = result

            if ticker not in ticker_data:
                logger.error(f"Failed to fetch primary ticker {ticker}")
                return {
                    "ticker": ticker,
                    "peers": peers,
                    "comparison": {},
                    "relative_position": {}
                }

            # Extract key metrics for comparison
            metrics_to_compare = [
                "trailingPE",
                "forwardPE",
                "priceToSalesTrailing12Months",
                "priceToBook",
                "pegRatio",
                "debtToEquity",
                "returnOnEquity",
                "returnOnAssets",
                "profitMargins",
                "revenueGrowth",
                "earningsGrowth",
                "grossMargins",
                "operatingMargins",
                "beta",
                "marketCap"
            ]

            comparison_data = {}
            for metric in metrics_to_compare:
                values = {}
                for t, data in ticker_data.items():
                    val = data.get(metric)
                    if val is not None and val != 0:
                        values[t] = float(val)

                if values:
                    comparison_data[metric] = values

            # Calculate relative position
            relative_position = {}
            primary_data = ticker_data[ticker]

            for metric, values in comparison_data.items():
                if ticker in values:
                    primary_value = values[ticker]
                    peer_values = [v for t, v in values.items() if t != ticker]

                    if peer_values:
                        avg_peer = sum(peer_values) / len(peer_values)
                        max_peer = max(peer_values)
                        min_peer = min(peer_values)

                        # Determine if higher is better for this metric
                        higher_is_better = metric in [
                            "returnOnEquity",
                            "returnOnAssets",
                            "profitMargins",
                            "revenueGrowth",
                            "earningsGrowth",
                            "grossMargins",
                            "operatingMargins"
                        ]

                        lower_is_better = metric in [
                            "trailingPE",
                            "forwardPE",
                            "priceToSalesTrailing12Months",
                            "priceToBook",
                            "pegRatio",
                            "debtToEquity",
                            "beta"
                        ]

                        # Calculate percentile
                        all_values = sorted(peer_values + [primary_value])
                        rank = all_values.index(primary_value) + 1
                        percentile = (rank / len(all_values)) * 100

                        # Determine position
                        if avg_peer > 0:
                            diff_pct = ((primary_value - avg_peer) / avg_peer) * 100
                        else:
                            diff_pct = 0

                        position = "inline"
                        if higher_is_better:
                            if primary_value > avg_peer * 1.2:
                                position = "above_average"
                            elif primary_value < avg_peer * 0.8:
                                position = "below_average"
                        elif lower_is_better:
                            if primary_value < avg_peer * 0.8:
                                position = "below_average"  # Better (lower)
                            elif primary_value > avg_peer * 1.2:
                                position = "above_average"  # Worse (higher)

                        relative_position[metric] = {
                            "value": primary_value,
                            "peer_average": avg_peer,
                            "peer_min": min_peer,
                            "peer_max": max_peer,
                            "diff_from_avg_pct": diff_pct,
                            "percentile": percentile,
                            "position": position
                        }

            result = {
                "ticker": ticker,
                "peers": [t for t in peers if t in ticker_data],
                "comparison": comparison_data,
                "relative_position": relative_position,
                "timestamp": "now"
            }

            # Cache result
            if self.cache:
                await self.cache.set(cache_key, result, ttl=TTL_LONG)

            return result

        except Exception as e:
            logger.error(f"Error comparing {ticker} with peers: {e}")
            return {
                "ticker": ticker,
                "peers": peers,
                "comparison": {},
                "relative_position": {}
            }

    async def get_valuation_comparison(
        self,
        ticker: str,
        peers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get focused valuation comparison

        Args:
            ticker: Primary stock ticker
            peers: Optional list of peer tickers

        Returns:
            Dict with valuation metrics comparison
        """
        full_comparison = await self.get_peer_comparison(ticker, peers)

        valuation_metrics = [
            "trailingPE",
            "forwardPE",
            "priceToSalesTrailing12Months",
            "priceToBook",
            "pegRatio"
        ]

        valuation_data = {
            "ticker": ticker,
            "peers": full_comparison.get("peers", []),
            "valuation": {}
        }

        for metric in valuation_metrics:
            if metric in full_comparison.get("relative_position", {}):
                valuation_data["valuation"][metric] = full_comparison["relative_position"][metric]

        return valuation_data

    async def get_growth_comparison(
        self,
        ticker: str,
        peers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get focused growth metrics comparison

        Args:
            ticker: Primary stock ticker
            peers: Optional list of peer tickers

        Returns:
            Dict with growth metrics comparison
        """
        full_comparison = await self.get_peer_comparison(ticker, peers)

        growth_metrics = [
            "revenueGrowth",
            "earningsGrowth",
            "grossMargins",
            "operatingMargins",
            "profitMargins"
        ]

        growth_data = {
            "ticker": ticker,
            "peers": full_comparison.get("peers", []),
            "growth": {}
        }

        for metric in growth_metrics:
            if metric in full_comparison.get("relative_position", {}):
                growth_data["growth"][metric] = full_comparison["relative_position"][metric]

        return growth_data


# Singleton instance
_peer_comparison_service: Optional[PeerComparisonService] = None


def get_peer_comparison_service() -> PeerComparisonService:
    """Get or create peer comparison service instance"""
    global _peer_comparison_service
    if _peer_comparison_service is None:
        _peer_comparison_service = PeerComparisonService()
    return _peer_comparison_service
