"""Yahoo Finance client for stock data."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.core.exceptions import DataSourceException
from backend.app.core.rate_limiter import get_yahoo_limiter
from backend.app.services.cache import cache, CacheService

logger = structlog.get_logger(__name__)


class YahooFinanceClient:
    """Client for Yahoo Finance data via yfinance library."""

    def __init__(self) -> None:
        self.rate_limiter = get_yahoo_limiter()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_stock_info(self, ticker: str) -> dict[str, Any]:
        """Get comprehensive stock information.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Stock information dictionary
        """
        cache_key = f"yf:info:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        await self.rate_limiter.wait_for_token()

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or info.get("regularMarketPrice") is None:
                raise DataSourceException(
                    f"No data found for ticker {ticker}",
                    source="yahoo_finance",
                )

            result = {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary"),

                # Price data
                "current_price": self._safe_decimal(info.get("regularMarketPrice")),
                "previous_close": self._safe_decimal(info.get("previousClose")),
                "open": self._safe_decimal(info.get("regularMarketOpen")),
                "day_high": self._safe_decimal(info.get("dayHigh")),
                "day_low": self._safe_decimal(info.get("dayLow")),
                "volume": info.get("volume"),
                "avg_volume": info.get("averageVolume"),

                # Valuation
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "pe_ratio": self._safe_decimal(info.get("trailingPE")),
                "forward_pe": self._safe_decimal(info.get("forwardPE")),
                "peg_ratio": self._safe_decimal(info.get("pegRatio")),
                "price_to_book": self._safe_decimal(info.get("priceToBook")),
                "price_to_sales": self._safe_decimal(info.get("priceToSalesTrailing12Months")),
                "ev_to_revenue": self._safe_decimal(info.get("enterpriseToRevenue")),
                "ev_to_ebitda": self._safe_decimal(info.get("enterpriseToEbitda")),

                # Fundamentals
                "eps": self._safe_decimal(info.get("trailingEps")),
                "forward_eps": self._safe_decimal(info.get("forwardEps")),
                "book_value": self._safe_decimal(info.get("bookValue")),
                "revenue": info.get("totalRevenue"),
                "gross_profit": info.get("grossProfits"),
                "ebitda": info.get("ebitda"),
                "net_income": info.get("netIncomeToCommon"),
                "free_cash_flow": info.get("freeCashflow"),
                "operating_cash_flow": info.get("operatingCashflow"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),

                # Margins and ratios
                "profit_margin": self._safe_decimal(info.get("profitMargins")),
                "operating_margin": self._safe_decimal(info.get("operatingMargins")),
                "gross_margin": self._safe_decimal(info.get("grossMargins")),
                "return_on_equity": self._safe_decimal(info.get("returnOnEquity")),
                "return_on_assets": self._safe_decimal(info.get("returnOnAssets")),
                "debt_to_equity": self._safe_decimal(info.get("debtToEquity")),
                "current_ratio": self._safe_decimal(info.get("currentRatio")),
                "quick_ratio": self._safe_decimal(info.get("quickRatio")),

                # Growth
                "revenue_growth": self._safe_decimal(info.get("revenueGrowth")),
                "earnings_growth": self._safe_decimal(info.get("earningsGrowth")),

                # Dividends
                "dividend_yield": self._safe_decimal(info.get("dividendYield")),
                "dividend_rate": self._safe_decimal(info.get("dividendRate")),
                "payout_ratio": self._safe_decimal(info.get("payoutRatio")),
                "ex_dividend_date": info.get("exDividendDate"),

                # Analyst info
                "target_mean_price": self._safe_decimal(info.get("targetMeanPrice")),
                "target_high_price": self._safe_decimal(info.get("targetHighPrice")),
                "target_low_price": self._safe_decimal(info.get("targetLowPrice")),
                "recommendation": info.get("recommendationKey"),
                "num_analysts": info.get("numberOfAnalystOpinions"),

                # 52-week data
                "52_week_high": self._safe_decimal(info.get("fiftyTwoWeekHigh")),
                "52_week_low": self._safe_decimal(info.get("fiftyTwoWeekLow")),
                "50_day_average": self._safe_decimal(info.get("fiftyDayAverage")),
                "200_day_average": self._safe_decimal(info.get("twoHundredDayAverage")),

                # Shares
                "shares_outstanding": info.get("sharesOutstanding"),
                "float_shares": info.get("floatShares"),
                "shares_short": info.get("sharesShort"),
                "short_ratio": self._safe_decimal(info.get("shortRatio")),

                # Beta
                "beta": self._safe_decimal(info.get("beta")),
            }

            # Cache for 5 minutes
            await cache.set(cache_key, result, CacheService.TTL_SHORT)

            logger.info("Fetched stock info", ticker=ticker)
            return result

        except Exception as e:
            logger.error("Failed to fetch stock info", ticker=ticker, error=str(e))
            raise DataSourceException(
                f"Failed to fetch data from Yahoo Finance: {e}",
                source="yahoo_finance",
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_historical_prices(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[dict[str, Any]]:
        """Get historical price data.

        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            List of price data
        """
        cache_key = f"yf:history:{ticker}:{period}:{interval}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        await self.rate_limiter.wait_for_token()

        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period, interval=interval)

            if history.empty:
                raise DataSourceException(
                    f"No historical data found for {ticker}",
                    source="yahoo_finance",
                )

            prices = []
            for idx, row in history.iterrows():
                prices.append({
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                    "open": Decimal(str(row["Open"])),
                    "high": Decimal(str(row["High"])),
                    "low": Decimal(str(row["Low"])),
                    "close": Decimal(str(row["Close"])),
                    "volume": int(row["Volume"]),
                })

            # Cache based on interval
            ttl = CacheService.TTL_SHORT if interval in ("1m", "5m") else CacheService.TTL_MEDIUM
            await cache.set(cache_key, prices, ttl)

            logger.info("Fetched historical prices", ticker=ticker, count=len(prices))
            return prices

        except Exception as e:
            logger.error("Failed to fetch historical prices", ticker=ticker, error=str(e))
            raise DataSourceException(
                f"Failed to fetch historical data: {e}",
                source="yahoo_finance",
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_market_indices(self) -> dict[str, Any]:
        """Get major market indices data.

        Returns:
            Dictionary with index data
        """
        cache_key = "yf:indices"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        indices = {
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones",
            "^IXIC": "NASDAQ",
            "^RUT": "Russell 2000",
        }

        result = {}

        for symbol, name in indices.items():
            await self.rate_limiter.wait_for_token()

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                result[symbol] = {
                    "name": name,
                    "price": self._safe_decimal(info.get("regularMarketPrice")),
                    "previous_close": self._safe_decimal(info.get("previousClose")),
                    "change": self._safe_decimal(info.get("regularMarketChange")),
                    "change_percent": self._safe_decimal(info.get("regularMarketChangePercent")),
                    "day_high": self._safe_decimal(info.get("dayHigh")),
                    "day_low": self._safe_decimal(info.get("dayLow")),
                    "volume": info.get("volume"),
                }

            except Exception as e:
                logger.warning("Failed to fetch index", symbol=symbol, error=str(e))
                result[symbol] = {"name": name, "error": str(e)}

        # Cache for 1 minute
        await cache.set(cache_key, result, 60)

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_sector_performance(self) -> list[dict[str, Any]]:
        """Get sector ETF performance.

        Returns:
            List of sector performance data
        """
        cache_key = "yf:sectors"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        sector_etfs = {
            "XLK": "Technology",
            "XLV": "Healthcare",
            "XLF": "Financials",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLE": "Energy",
            "XLI": "Industrials",
            "XLB": "Materials",
            "XLU": "Utilities",
            "XLRE": "Real Estate",
            "XLC": "Communication Services",
        }

        sectors = []

        for symbol, name in sector_etfs.items():
            await self.rate_limiter.wait_for_token()

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                change_pct = info.get("regularMarketChangePercent", 0)

                sectors.append({
                    "symbol": symbol,
                    "name": name,
                    "price": self._safe_decimal(info.get("regularMarketPrice")),
                    "change_percent": self._safe_decimal(change_pct),
                    "volume": info.get("volume"),
                })

            except Exception as e:
                logger.warning("Failed to fetch sector", symbol=symbol, error=str(e))

        # Sort by performance
        sectors.sort(key=lambda x: float(x.get("change_percent", 0) or 0), reverse=True)

        # Cache for 5 minutes
        await cache.set(cache_key, sectors, CacheService.TTL_SHORT)

        return sectors

    async def get_earnings_calendar(self, ticker: str) -> dict[str, Any]:
        """Get earnings calendar for a stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Earnings calendar data
        """
        await self.rate_limiter.wait_for_token()

        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar

            if calendar is None or (hasattr(calendar, 'empty') and calendar.empty):
                return {"ticker": ticker, "earnings_date": None}

            # Handle different return types
            if isinstance(calendar, dict):
                return {
                    "ticker": ticker,
                    "earnings_date": calendar.get("Earnings Date"),
                    "earnings_high": calendar.get("Earnings High"),
                    "earnings_low": calendar.get("Earnings Low"),
                    "earnings_average": calendar.get("Earnings Average"),
                    "revenue_average": calendar.get("Revenue Average"),
                }

            return {"ticker": ticker, "calendar": calendar}

        except Exception as e:
            logger.warning("Failed to fetch earnings calendar", ticker=ticker, error=str(e))
            return {"ticker": ticker, "error": str(e)}

    async def get_recommendations(self, ticker: str) -> list[dict[str, Any]]:
        """Get analyst recommendations.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of recommendations
        """
        await self.rate_limiter.wait_for_token()

        try:
            stock = yf.Ticker(ticker)
            recs = stock.recommendations

            if recs is None or recs.empty:
                return []

            result = []
            for idx, row in recs.tail(10).iterrows():
                result.append({
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                    "firm": row.get("Firm"),
                    "to_grade": row.get("To Grade"),
                    "from_grade": row.get("From Grade"),
                    "action": row.get("Action"),
                })

            return result

        except Exception as e:
            logger.warning("Failed to fetch recommendations", ticker=ticker, error=str(e))
            return []

    def _safe_decimal(self, value: Any) -> Decimal | None:
        """Safely convert value to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None


# Singleton instance
_client: YahooFinanceClient | None = None


def get_yahoo_finance_client() -> YahooFinanceClient:
    """Get Yahoo Finance client instance."""
    global _client
    if _client is None:
        _client = YahooFinanceClient()
    return _client
