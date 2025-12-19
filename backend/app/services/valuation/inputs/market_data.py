"""
Market Data Service for Valuation Inputs.

Provides market-level inputs including:
- Risk-free rate (10-Year Treasury yield)
- Equity risk premium
- Size premiums
"""

from datetime import datetime

import structlog

from ..models import DataQuality, MarketInputs

logger = structlog.get_logger(__name__)


class MarketDataService:
    """
    Provides market-level inputs for valuation.

    Risk-Free Rate Strategy:
    1. Yahoo Finance (^TNX - 10-Year Treasury Yield) - PRIMARY
    2. Hardcoded fallback (4.0%) - if Yahoo fails
    """

    # Hardcoded fallback (updated periodically)
    FALLBACK_RF_RATE = 0.04  # 4.0%

    # Historical equity risk premium
    DEFAULT_ERP = 0.055  # 5.5% historical average

    # Size premiums based on market cap (Kroll/Duff & Phelps data approximation)
    SIZE_PREMIUM_TIERS = [
        (50_000_000_000, -0.004),  # >$50B: -0.4%
        (10_000_000_000, 0.0),  # $10B-$50B: 0%
        (5_000_000_000, 0.008),  # $5B-$10B: 0.8%
        (3_000_000_000, 0.012),  # $3B-$5B: 1.2%
        (1_200_000_000, 0.016),  # $1.2B-$3B: 1.6%
        (600_000_000, 0.020),  # $600M-$1.2B: 2.0%
        (300_000_000, 0.026),  # $300M-$600M: 2.6%
        (150_000_000, 0.032),  # $150M-$300M: 3.2%
        (0, 0.05),  # <$150M: 5.0%
    ]

    def __init__(self):
        """Initialize the market data service."""
        self._cached_rf_rate: float | None = None
        self._cache_time: datetime | None = None
        self._cache_duration_minutes = 60  # Cache for 1 hour

    async def get_risk_free_rate(self) -> tuple[float, str, DataQuality]:
        """
        Get current risk-free rate from best available source.

        Returns:
            Tuple of (rate as decimal, source name, data quality)
        """
        # Check cache first
        if self._is_cache_valid():
            logger.debug("Using cached risk-free rate", rate=self._cached_rf_rate)
            return self._cached_rf_rate, "yahoo_finance_cached", DataQuality.HIGH

        # Try Yahoo Finance (^TNX)
        try:
            rate = await self._fetch_from_yahoo()
            if rate is not None and 0.01 < rate < 0.15:  # Sanity check: 1% to 15%
                self._cached_rf_rate = rate
                self._cache_time = datetime.now()
                logger.info("Fetched risk-free rate from Yahoo Finance", rate=rate)
                return rate, "yahoo_finance", DataQuality.HIGH
        except Exception as e:
            logger.warning("Yahoo Finance risk-free rate fetch failed", error=str(e))

        # Fallback to hardcoded value
        logger.warning("Using hardcoded risk-free rate fallback", rate=self.FALLBACK_RF_RATE)
        return self.FALLBACK_RF_RATE, "hardcoded", DataQuality.LOW

    async def _fetch_from_yahoo(self) -> float | None:
        """Fetch 10-Year Treasury yield from Yahoo Finance (^TNX)."""
        try:
            # Import here to avoid circular imports
            from backend.app.services.yahoo_finance import get_yahoo_finance_client

            client = get_yahoo_finance_client()
            info = await client.get_stock_info("^TNX")

            if info:
                # ^TNX quotes the yield as a percentage (e.g., 4.35 for 4.35%)
                current_price = info.get("current_price")
                if current_price is not None:
                    # Convert percentage to decimal
                    return float(current_price) / 100.0

            return None

        except Exception as e:
            logger.warning("Failed to fetch from Yahoo Finance", error=str(e))
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached risk-free rate is still valid."""
        if self._cached_rf_rate is None or self._cache_time is None:
            return False

        elapsed = (datetime.now() - self._cache_time).total_seconds() / 60
        return elapsed < self._cache_duration_minutes

    def get_size_premium(self, market_cap: float) -> float:
        """
        Get size premium based on market capitalization.

        Based on Kroll/Duff & Phelps size premium data.

        Args:
            market_cap: Market capitalization in dollars

        Returns:
            Size premium as decimal (e.g., 0.02 for 2%)
        """
        if market_cap <= 0:
            return 0.02  # Default 2% for unknown size

        for threshold, premium in self.SIZE_PREMIUM_TIERS:
            if market_cap >= threshold:
                return premium

        return 0.05  # Very small cap

    def get_equity_risk_premium(self) -> float:
        """
        Get equity risk premium.

        Currently uses historical average (~5.5%).
        Could be enhanced to use implied ERP from market data.

        Returns:
            ERP as decimal
        """
        return self.DEFAULT_ERP

    async def get_market_inputs(self, market_cap: float = 0) -> MarketInputs:
        """
        Get all market-level inputs for valuation.

        Args:
            market_cap: Company's market cap for size premium calculation

        Returns:
            MarketInputs dataclass with all market data
        """
        rf_rate, rf_source, rf_quality = await self.get_risk_free_rate()

        return MarketInputs(
            risk_free_rate=rf_rate,
            equity_risk_premium=self.get_equity_risk_premium(),
            sp500_return=rf_rate + self.DEFAULT_ERP,  # Expected market return
            sector_premium=0.0,  # Could be enhanced with sector-specific data
            rf_source=rf_source,
            rf_as_of_date=datetime.now(),
            data_quality=rf_quality,
        )
