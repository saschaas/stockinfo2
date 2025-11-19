"""Stock Research Agent for gathering comprehensive stock data."""

from typing import Any
from decimal import Decimal

import structlog

from backend.app.config import get_settings
from backend.app.services.yahoo_finance import get_yahoo_finance_client
from backend.app.services.alpha_vantage import get_alpha_vantage_client

logger = structlog.get_logger(__name__)
settings = get_settings()


class StockResearchAgent:
    """Agent for researching and gathering stock data."""

    def __init__(self) -> None:
        self.data_sources_used = {}

    async def research(self, ticker: str) -> dict[str, Any]:
        """Research a stock and gather comprehensive data.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Comprehensive stock data
        """
        ticker = ticker.upper()
        logger.info("Stock Research Agent starting", ticker=ticker)

        result = {"ticker": ticker}
        self.data_sources_used = {}

        # Tier 1: Direct API access (primary source)
        try:
            # Try Yahoo Finance first (faster, no API key needed)
            yf_data = await self._fetch_yahoo_data(ticker)
            result.update(yf_data)
            self.data_sources_used["basic_info"] = {"type": "api", "name": "yahoo_finance"}

        except Exception as e:
            logger.warning("Yahoo Finance failed, trying Alpha Vantage", error=str(e))

            # Fallback to Alpha Vantage
            try:
                av_data = await self._fetch_alpha_vantage_data(ticker)
                result.update(av_data)
                self.data_sources_used["basic_info"] = {"type": "api", "name": "alpha_vantage"}
            except Exception as e2:
                logger.error("All API sources failed", error=str(e2))
                result["error"] = str(e2)

        # Fetch historical prices for technical analysis
        try:
            prices = await self._fetch_historical_prices(ticker)
            result["historical_prices"] = prices
            self.data_sources_used["prices"] = {"type": "api", "name": "yahoo_finance"}
        except Exception as e:
            logger.warning("Failed to fetch historical prices", error=str(e))

        # Fetch earnings data
        try:
            earnings = await self._fetch_earnings_data(ticker)
            result["earnings"] = earnings
        except Exception as e:
            logger.warning("Failed to fetch earnings", error=str(e))

        # Fetch analyst recommendations
        try:
            recommendations = await self._fetch_recommendations(ticker)
            result["analyst_recommendations"] = recommendations
        except Exception as e:
            logger.warning("Failed to fetch recommendations", error=str(e))

        result["data_sources"] = self.data_sources_used
        logger.info("Stock Research Agent completed", ticker=ticker)

        return result

    async def _fetch_yahoo_data(self, ticker: str) -> dict[str, Any]:
        """Fetch data from Yahoo Finance."""
        client = get_yahoo_finance_client()
        info = await client.get_stock_info(ticker)

        return {
            "company_name": info.get("name"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "description": info.get("description"),
            "website": info.get("website"),

            # Price data
            "current_price": info.get("current_price"),
            "previous_close": info.get("previous_close"),
            "open": info.get("open"),
            "day_high": info.get("day_high"),
            "day_low": info.get("day_low"),
            "volume": info.get("volume"),
            "avg_volume": info.get("avg_volume"),

            # Valuation
            "market_cap": info.get("market_cap"),
            "enterprise_value": info.get("enterprise_value"),
            "pe_ratio": info.get("pe_ratio"),
            "forward_pe": info.get("forward_pe"),
            "peg_ratio": info.get("peg_ratio"),
            "price_to_book": info.get("price_to_book"),
            "price_to_sales": info.get("price_to_sales"),
            "ev_to_revenue": info.get("ev_to_revenue"),
            "ev_to_ebitda": info.get("ev_to_ebitda"),

            # Fundamentals
            "eps": info.get("eps"),
            "forward_eps": info.get("forward_eps"),
            "revenue": info.get("revenue"),
            "gross_profit": info.get("gross_profit"),
            "ebitda": info.get("ebitda"),
            "net_income": info.get("net_income"),
            "free_cash_flow": info.get("free_cash_flow"),
            "total_debt": info.get("total_debt"),
            "total_cash": info.get("total_cash"),

            # Margins
            "profit_margin": info.get("profit_margin"),
            "operating_margin": info.get("operating_margin"),
            "gross_margin": info.get("gross_margin"),
            "return_on_equity": info.get("return_on_equity"),
            "return_on_assets": info.get("return_on_assets"),
            "debt_to_equity": info.get("debt_to_equity"),

            # Growth
            "revenue_growth": info.get("revenue_growth"),
            "earnings_growth": info.get("earnings_growth"),

            # Dividends
            "dividend_yield": info.get("dividend_yield"),
            "dividend_rate": info.get("dividend_rate"),
            "payout_ratio": info.get("payout_ratio"),

            # Analyst
            "target_mean_price": info.get("target_mean_price"),
            "target_high_price": info.get("target_high_price"),
            "target_low_price": info.get("target_low_price"),
            "recommendation": info.get("recommendation"),
            "num_analysts": info.get("num_analysts"),

            # 52-week
            "52_week_high": info.get("52_week_high"),
            "52_week_low": info.get("52_week_low"),
            "50_day_average": info.get("50_day_average"),
            "200_day_average": info.get("200_day_average"),

            # Shares
            "shares_outstanding": info.get("shares_outstanding"),
            "float_shares": info.get("float_shares"),
            "short_ratio": info.get("short_ratio"),
            "beta": info.get("beta"),
        }

    async def _fetch_alpha_vantage_data(self, ticker: str) -> dict[str, Any]:
        """Fetch data from Alpha Vantage."""
        client = await get_alpha_vantage_client()

        # Get overview
        overview = await client.get_company_overview(ticker)

        # Get quote
        quote = await client.get_quote(ticker)

        return {
            "company_name": overview.get("name"),
            "sector": overview.get("sector"),
            "industry": overview.get("industry"),
            "description": overview.get("description"),

            "current_price": quote.get("price"),
            "previous_close": quote.get("previous_close"),
            "volume": quote.get("volume"),

            "market_cap": overview.get("market_cap"),
            "pe_ratio": overview.get("pe_ratio"),
            "forward_pe": overview.get("forward_pe"),
            "peg_ratio": overview.get("peg_ratio"),
            "price_to_book": overview.get("price_to_book"),
            "ev_to_revenue": overview.get("ev_to_revenue"),
            "ev_to_ebitda": overview.get("ev_to_ebitda"),

            "eps": overview.get("eps"),
            "profit_margin": overview.get("profit_margin"),
            "operating_margin": overview.get("operating_margin"),
            "return_on_equity": overview.get("return_on_equity"),
            "return_on_assets": overview.get("return_on_assets"),

            "dividend_yield": overview.get("dividend_yield"),
            "target_mean_price": overview.get("analyst_target_price"),

            "52_week_high": overview.get("52_week_high"),
            "52_week_low": overview.get("52_week_low"),
            "50_day_average": overview.get("50_day_ma"),
            "200_day_average": overview.get("200_day_ma"),

            "beta": overview.get("beta"),
            "shares_outstanding": overview.get("shares_outstanding"),
        }

    async def _fetch_historical_prices(self, ticker: str) -> list[dict]:
        """Fetch historical price data."""
        client = get_yahoo_finance_client()
        prices = await client.get_historical_prices(ticker, period="3mo", interval="1d")
        return prices

    async def _fetch_earnings_data(self, ticker: str) -> dict[str, Any]:
        """Fetch earnings calendar data."""
        client = get_yahoo_finance_client()
        return await client.get_earnings_calendar(ticker)

    async def _fetch_recommendations(self, ticker: str) -> list[dict]:
        """Fetch analyst recommendations."""
        client = get_yahoo_finance_client()
        return await client.get_recommendations(ticker)
