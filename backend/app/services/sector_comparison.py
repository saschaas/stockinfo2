"""Sector comparison service for stock analysis."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import StockAnalysis
from backend.app.db.session import async_session_factory
from backend.app.services.cache import cache, CacheService

logger = structlog.get_logger(__name__)


class SectorComparisonService:
    """Service for comparing stocks to their sector averages."""

    # Metrics to compare (field name, display name)
    COMPARABLE_METRICS = [
        ("pe_ratio", "P/E Ratio"),
        ("forward_pe", "Forward P/E"),
        ("price_to_book", "Price to Book"),
        ("peg_ratio", "PEG Ratio"),
        ("debt_to_equity", "Debt to Equity"),
        ("composite_score", "Composite Score"),
        ("fundamental_score", "Fundamental Score"),
        ("technical_score", "Technical Score"),
        ("competitive_score", "Competitive Score"),
        ("risk_score", "Risk Score"),
        ("rsi", "RSI"),
        ("upside_potential", "Upside Potential"),
    ]

    async def get_sector_statistics(
        self,
        sector: str,
        lookback_days: int = 180,
    ) -> Dict[str, Any]:
        """
        Calculate sector-wide averages, medians, and percentiles.

        Args:
            sector: Sector name (e.g., "Technology")
            lookback_days: Days to look back for recent data (default 180 = 6 months)

        Returns:
            Dictionary with sector statistics including:
            - sector: Sector name
            - stock_count: Number of stocks included
            - analysis_date_range: Date range of data
            - averages: Average values for each metric
            - medians: Median values for each metric
            - percentiles: 25th and 75th percentiles
        """
        # Check cache first
        cache_key = f"sector_stats:{sector}:{lookback_days}"
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for sector statistics", sector=sector)
            return cached

        async with async_session_factory() as session:
            cutoff_date = date.today() - timedelta(days=lookback_days)

            # Subquery: Get latest analysis for each ticker in date range
            latest_per_ticker = (
                select(
                    StockAnalysis.ticker,
                    func.max(StockAnalysis.analysis_date).label("latest_date"),
                )
                .where(
                    and_(
                        StockAnalysis.sector == sector,
                        StockAnalysis.analysis_date >= cutoff_date,
                    )
                )
                .group_by(StockAnalysis.ticker)
                .subquery()
            )

            # Build aggregation query dynamically
            aggregations = [
                func.count(StockAnalysis.ticker).label("stock_count"),
                func.min(StockAnalysis.analysis_date).label("oldest_date"),
                func.max(StockAnalysis.analysis_date).label("newest_date"),
            ]

            # Add aggregations for each metric
            for field_name, _ in self.COMPARABLE_METRICS:
                field = getattr(StockAnalysis, field_name)
                aggregations.extend([
                    func.avg(field).label(f"avg_{field_name}"),
                    func.percentile_cont(0.5).within_group(field).label(f"median_{field_name}"),
                    func.percentile_cont(0.25).within_group(field).label(f"p25_{field_name}"),
                    func.percentile_cont(0.75).within_group(field).label(f"p75_{field_name}"),
                    func.count(field).label(f"count_{field_name}"),
                ])

            # Execute query
            stmt = (
                select(*aggregations)
                .select_from(StockAnalysis)
                .join(
                    latest_per_ticker,
                    and_(
                        StockAnalysis.ticker == latest_per_ticker.c.ticker,
                        StockAnalysis.analysis_date == latest_per_ticker.c.latest_date,
                    ),
                )
            )

            result = await session.execute(stmt)
            row = result.one_or_none()

            if not row or row.stock_count == 0:
                logger.warning("No stocks found for sector", sector=sector)
                return {
                    "sector": sector,
                    "stock_count": 0,
                    "error": "No stocks found for this sector in the specified time range",
                }

            # Build response
            response = {
                "sector": sector,
                "stock_count": row.stock_count,
                "analysis_date_range": {
                    "from": str(row.oldest_date),
                    "to": str(row.newest_date),
                },
                "averages": {},
                "medians": {},
                "percentiles": {
                    "25th": {},
                    "75th": {},
                },
                "sample_sizes": {},
            }

            # Extract values for each metric
            for field_name, display_name in self.COMPARABLE_METRICS:
                avg_val = getattr(row, f"avg_{field_name}", None)
                median_val = getattr(row, f"median_{field_name}", None)
                p25_val = getattr(row, f"p25_{field_name}", None)
                p75_val = getattr(row, f"p75_{field_name}", None)
                count_val = getattr(row, f"count_{field_name}", None)

                response["averages"][field_name] = self._safe_float(avg_val)
                response["medians"][field_name] = self._safe_float(median_val)
                response["percentiles"]["25th"][field_name] = self._safe_float(p25_val)
                response["percentiles"]["75th"][field_name] = self._safe_float(p75_val)
                response["sample_sizes"][field_name] = count_val or 0

            # Add warning for small sample size
            if row.stock_count < 10:
                response["warning"] = (
                    f"Small sample size ({row.stock_count} stocks). "
                    "Statistics may not be representative of the full sector."
                )

            # Cache for 1 hour
            await cache.set(cache_key, response, CacheService.TTL_MEDIUM)

            logger.info(
                "Calculated sector statistics",
                sector=sector,
                stock_count=row.stock_count,
            )
            return response

    async def compare_stock_to_sector(
        self,
        ticker: str,
        sector: Optional[str] = None,
        lookback_days: int = 180,
    ) -> Dict[str, Any]:
        """
        Compare a stock's metrics to its sector averages.

        Args:
            ticker: Stock ticker symbol
            sector: Sector name (if None, auto-detect from stock's latest analysis)
            lookback_days: Days to look back for sector data

        Returns:
            Dictionary with stock comparison including:
            - ticker: Stock ticker
            - sector: Sector name
            - stock_metrics: Stock's current metrics
            - sector_averages: Sector average metrics
            - percentile_ranks: Stock's percentile rank for each metric
            - relative_strength: Overall assessment
        """
        # Check cache first
        cache_key = f"sector_comparison:{ticker}:{lookback_days}"
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for sector comparison", ticker=ticker)
            return cached

        async with async_session_factory() as session:
            # Get latest analysis for the stock
            stmt = (
                select(StockAnalysis)
                .where(StockAnalysis.ticker == ticker.upper())
                .order_by(StockAnalysis.analysis_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            stock_analysis = result.scalar_one_or_none()

            if not stock_analysis:
                return {
                    "ticker": ticker.upper(),
                    "error": "No analysis found for this stock",
                }

            # Auto-detect sector if not provided
            if sector is None:
                sector = stock_analysis.sector

            if not sector:
                return {
                    "ticker": ticker.upper(),
                    "error": "Sector information not available for this stock",
                }

        # Get sector statistics
        sector_stats = await self.get_sector_statistics(sector, lookback_days)

        if "error" in sector_stats:
            return {
                "ticker": ticker.upper(),
                "sector": sector,
                "error": sector_stats["error"],
            }

        # Extract stock metrics
        stock_metrics = {}
        for field_name, _ in self.COMPARABLE_METRICS:
            value = getattr(stock_analysis, field_name, None)
            stock_metrics[field_name] = self._safe_float(value)

        # Calculate percentile ranks
        percentile_ranks = {}
        for field_name, _ in self.COMPARABLE_METRICS:
            stock_value = stock_metrics.get(field_name)
            if stock_value is None:
                percentile_ranks[field_name] = None
                continue

            p25 = sector_stats["percentiles"]["25th"].get(field_name)
            p75 = sector_stats["percentiles"]["75th"].get(field_name)
            median = sector_stats["medians"].get(field_name)

            if p25 is None or p75 is None or median is None:
                percentile_ranks[field_name] = None
                continue

            # Estimate percentile based on position relative to quartiles
            if stock_value <= p25:
                # Bottom quartile (0-25th percentile)
                percentile = max(0, 25 * (stock_value / p25)) if p25 != 0 else 12.5
            elif stock_value <= median:
                # Second quartile (25-50th percentile)
                percentile = 25 + 25 * ((stock_value - p25) / (median - p25))
            elif stock_value <= p75:
                # Third quartile (50-75th percentile)
                percentile = 50 + 25 * ((stock_value - median) / (p75 - median))
            else:
                # Top quartile (75-100th percentile)
                percentile = min(100, 75 + 25 * ((stock_value - p75) / (p75 - median)))

            percentile_ranks[field_name] = round(percentile, 1)

        # Determine relative strength based on composite score
        composite_percentile = percentile_ranks.get("composite_score")
        if composite_percentile is None:
            relative_strength = "unknown"
        elif composite_percentile >= 75:
            relative_strength = "well_above_average"
        elif composite_percentile >= 60:
            relative_strength = "above_average"
        elif composite_percentile >= 40:
            relative_strength = "average"
        elif composite_percentile >= 25:
            relative_strength = "below_average"
        else:
            relative_strength = "well_below_average"

        # Build response
        response = {
            "ticker": ticker.upper(),
            "sector": sector,
            "analysis_date": str(stock_analysis.analysis_date),
            "stock_metrics": stock_metrics,
            "sector_averages": sector_stats["averages"],
            "sector_medians": sector_stats["medians"],
            "percentile_ranks": percentile_ranks,
            "relative_strength": relative_strength,
            "stocks_included": sector_stats["stock_count"],
            "data_freshness": f"Last {lookback_days} days",
        }

        if "warning" in sector_stats:
            response["warning"] = sector_stats["warning"]

        # Cache for 15 minutes (shorter than sector stats since stock-specific)
        await cache.set(cache_key, response, 900)

        logger.info(
            "Completed sector comparison",
            ticker=ticker,
            sector=sector,
            relative_strength=relative_strength,
        )
        return response

    async def get_sector_leaders(
        self,
        sector: str,
        metric: str = "composite_score",
        limit: int = 10,
        lookback_days: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing stocks in a sector by specific metric.

        Args:
            sector: Sector name
            metric: Metric to rank by (default: composite_score)
            limit: Number of top stocks to return (default: 10)
            lookback_days: Days to look back for recent data

        Returns:
            List of top stocks with their metrics
        """
        async with async_session_factory() as session:
            cutoff_date = date.today() - timedelta(days=lookback_days)

            # Subquery: Get latest analysis for each ticker
            latest_per_ticker = (
                select(
                    StockAnalysis.ticker,
                    func.max(StockAnalysis.analysis_date).label("latest_date"),
                )
                .where(
                    and_(
                        StockAnalysis.sector == sector,
                        StockAnalysis.analysis_date >= cutoff_date,
                    )
                )
                .group_by(StockAnalysis.ticker)
                .subquery()
            )

            # Get stocks ordered by metric
            metric_field = getattr(StockAnalysis, metric, None)
            if metric_field is None:
                logger.error("Invalid metric", metric=metric)
                return []

            stmt = (
                select(StockAnalysis)
                .join(
                    latest_per_ticker,
                    and_(
                        StockAnalysis.ticker == latest_per_ticker.c.ticker,
                        StockAnalysis.analysis_date == latest_per_ticker.c.latest_date,
                    ),
                )
                .where(metric_field.isnot(None))
                .order_by(metric_field.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            stocks = result.scalars().all()

            leaders = []
            for stock in stocks:
                leaders.append({
                    "ticker": stock.ticker,
                    "company_name": stock.company_name,
                    "analysis_date": str(stock.analysis_date),
                    metric: self._safe_float(getattr(stock, metric)),
                    "composite_score": self._safe_float(stock.composite_score),
                    "market_cap": stock.market_cap,
                })

            logger.info(
                "Retrieved sector leaders",
                sector=sector,
                metric=metric,
                count=len(leaders),
            )
            return leaders

    async def invalidate_sector_cache(self, sector: str) -> None:
        """Invalidate cached sector statistics for a sector."""
        # Invalidate all cached sector stats for this sector
        for lookback in [30, 90, 180, 365]:
            cache_key = f"sector_stats:{sector}:{lookback}"
            await cache.delete(cache_key)

        logger.info("Invalidated sector cache", sector=sector)

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert Decimal/numeric to float."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# Singleton instance
_service: Optional[SectorComparisonService] = None


def get_sector_comparison_service() -> SectorComparisonService:
    """Get sector comparison service instance."""
    global _service
    if _service is None:
        _service = SectorComparisonService()
    return _service
