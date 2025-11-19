"""Alpha Vantage API client for stock data."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.config import get_settings
from backend.app.core.exceptions import DataSourceException, RateLimitException
from backend.app.core.rate_limiter import get_alpha_vantage_limiter
from backend.app.services.cache import cache, stock_price_key, CacheService

logger = structlog.get_logger(__name__)
settings = get_settings()


class AlphaVantageClient:
    """Client for Alpha Vantage API."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self) -> None:
        self.api_key = settings.alpha_vantage_api_key
        self.rate_limiter = get_alpha_vantage_limiter()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Make a rate-limited request to Alpha Vantage."""
        if not self.api_key:
            raise DataSourceException(
                "Alpha Vantage API key not configured",
                source="alpha_vantage",
                suggestion="Set ALPHA_VANTAGE_API_KEY in your .env file",
            )

        # Wait for rate limit
        await self.rate_limiter.wait_for_token()

        params["apikey"] = self.api_key

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if "Error Message" in data:
                raise DataSourceException(
                    data["Error Message"],
                    source="alpha_vantage",
                )
            if "Note" in data and "call frequency" in data["Note"].lower():
                raise RateLimitException(
                    "Alpha Vantage rate limit exceeded",
                    retry_after=60,
                )

            return data

        except httpx.HTTPError as e:
            logger.error("Alpha Vantage request failed", error=str(e))
            raise DataSourceException(
                f"Failed to fetch data from Alpha Vantage: {e}",
                source="alpha_vantage",
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_daily_prices(
        self,
        ticker: str,
        outputsize: str = "compact",
    ) -> list[dict[str, Any]]:
        """Get daily stock prices.

        Args:
            ticker: Stock ticker symbol
            outputsize: "compact" (100 days) or "full" (20+ years)

        Returns:
            List of price data dictionaries
        """
        # Check cache first
        cache_key = f"av:daily:{ticker}:{outputsize}"
        cached = await cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for daily prices", ticker=ticker)
            return cached

        data = await self._make_request({
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": outputsize,
        })

        time_series = data.get("Time Series (Daily)", {})
        if not time_series:
            raise DataSourceException(
                f"No price data found for {ticker}",
                source="alpha_vantage",
            )

        prices = []
        for date_str, values in time_series.items():
            prices.append({
                "date": date_str,
                "open": Decimal(values["1. open"]),
                "high": Decimal(values["2. high"]),
                "low": Decimal(values["3. low"]),
                "close": Decimal(values["4. close"]),
                "adjusted_close": Decimal(values["5. adjusted close"]),
                "volume": int(values["6. volume"]),
            })

        # Sort by date descending
        prices.sort(key=lambda x: x["date"], reverse=True)

        # Cache for 5 minutes
        await cache.set(cache_key, prices, CacheService.TTL_SHORT)

        logger.info("Fetched daily prices", ticker=ticker, count=len(prices))
        return prices

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_quote(self, ticker: str) -> dict[str, Any]:
        """Get real-time quote for a stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quote data dictionary
        """
        cache_key = f"av:quote:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        data = await self._make_request({
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
        })

        quote = data.get("Global Quote", {})
        if not quote:
            raise DataSourceException(
                f"No quote data found for {ticker}",
                source="alpha_vantage",
            )

        result = {
            "ticker": quote.get("01. symbol"),
            "open": Decimal(quote.get("02. open", "0")),
            "high": Decimal(quote.get("03. high", "0")),
            "low": Decimal(quote.get("04. low", "0")),
            "price": Decimal(quote.get("05. price", "0")),
            "volume": int(quote.get("06. volume", "0")),
            "latest_trading_day": quote.get("07. latest trading day"),
            "previous_close": Decimal(quote.get("08. previous close", "0")),
            "change": Decimal(quote.get("09. change", "0")),
            "change_percent": quote.get("10. change percent", "0%").rstrip("%"),
        }

        # Cache for 1 minute
        await cache.set(cache_key, result, 60)

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_company_overview(self, ticker: str) -> dict[str, Any]:
        """Get company overview and fundamentals.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company overview dictionary
        """
        cache_key = f"av:overview:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        data = await self._make_request({
            "function": "OVERVIEW",
            "symbol": ticker,
        })

        if not data or "Symbol" not in data:
            raise DataSourceException(
                f"No company overview found for {ticker}",
                source="alpha_vantage",
            )

        result = {
            "ticker": data.get("Symbol"),
            "name": data.get("Name"),
            "description": data.get("Description"),
            "exchange": data.get("Exchange"),
            "currency": data.get("Currency"),
            "country": data.get("Country"),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "market_cap": int(data.get("MarketCapitalization", 0)),
            "pe_ratio": self._safe_decimal(data.get("PERatio")),
            "peg_ratio": self._safe_decimal(data.get("PEGRatio")),
            "book_value": self._safe_decimal(data.get("BookValue")),
            "dividend_yield": self._safe_decimal(data.get("DividendYield")),
            "eps": self._safe_decimal(data.get("EPS")),
            "revenue_per_share": self._safe_decimal(data.get("RevenuePerShareTTM")),
            "profit_margin": self._safe_decimal(data.get("ProfitMargin")),
            "operating_margin": self._safe_decimal(data.get("OperatingMarginTTM")),
            "return_on_assets": self._safe_decimal(data.get("ReturnOnAssetsTTM")),
            "return_on_equity": self._safe_decimal(data.get("ReturnOnEquityTTM")),
            "revenue": int(data.get("RevenueTTM", 0)),
            "gross_profit": int(data.get("GrossProfitTTM", 0)),
            "diluted_eps": self._safe_decimal(data.get("DilutedEPSTTM")),
            "quarterly_earnings_growth": self._safe_decimal(data.get("QuarterlyEarningsGrowthYOY")),
            "quarterly_revenue_growth": self._safe_decimal(data.get("QuarterlyRevenueGrowthYOY")),
            "analyst_target_price": self._safe_decimal(data.get("AnalystTargetPrice")),
            "trailing_pe": self._safe_decimal(data.get("TrailingPE")),
            "forward_pe": self._safe_decimal(data.get("ForwardPE")),
            "price_to_sales": self._safe_decimal(data.get("PriceToSalesRatioTTM")),
            "price_to_book": self._safe_decimal(data.get("PriceToBookRatio")),
            "ev_to_revenue": self._safe_decimal(data.get("EVToRevenue")),
            "ev_to_ebitda": self._safe_decimal(data.get("EVToEBITDA")),
            "beta": self._safe_decimal(data.get("Beta")),
            "52_week_high": self._safe_decimal(data.get("52WeekHigh")),
            "52_week_low": self._safe_decimal(data.get("52WeekLow")),
            "50_day_ma": self._safe_decimal(data.get("50DayMovingAverage")),
            "200_day_ma": self._safe_decimal(data.get("200DayMovingAverage")),
            "shares_outstanding": int(data.get("SharesOutstanding", 0)),
            "dividend_date": data.get("DividendDate"),
            "ex_dividend_date": data.get("ExDividendDate"),
        }

        # Cache for 1 hour
        await cache.set(cache_key, result, CacheService.TTL_MEDIUM)

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_income_statement(self, ticker: str) -> dict[str, Any]:
        """Get income statement data.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Income statement data
        """
        cache_key = f"av:income:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        data = await self._make_request({
            "function": "INCOME_STATEMENT",
            "symbol": ticker,
        })

        result = {
            "ticker": data.get("symbol"),
            "annual_reports": data.get("annualReports", []),
            "quarterly_reports": data.get("quarterlyReports", []),
        }

        # Cache for 24 hours
        await cache.set(cache_key, result, CacheService.TTL_LONG)

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_balance_sheet(self, ticker: str) -> dict[str, Any]:
        """Get balance sheet data.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Balance sheet data
        """
        cache_key = f"av:balance:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        data = await self._make_request({
            "function": "BALANCE_SHEET",
            "symbol": ticker,
        })

        result = {
            "ticker": data.get("symbol"),
            "annual_reports": data.get("annualReports", []),
            "quarterly_reports": data.get("quarterlyReports", []),
        }

        # Cache for 24 hours
        await cache.set(cache_key, result, CacheService.TTL_LONG)

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_earnings(self, ticker: str) -> dict[str, Any]:
        """Get earnings data including upcoming earnings date.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Earnings data
        """
        cache_key = f"av:earnings:{ticker}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        data = await self._make_request({
            "function": "EARNINGS",
            "symbol": ticker,
        })

        result = {
            "ticker": data.get("symbol"),
            "annual_earnings": data.get("annualEarnings", []),
            "quarterly_earnings": data.get("quarterlyEarnings", []),
        }

        # Cache for 1 hour
        await cache.set(cache_key, result, CacheService.TTL_MEDIUM)

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_news_sentiment(
        self,
        tickers: str | list[str] | None = None,
        topics: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get news and sentiment data.

        Args:
            tickers: Stock ticker(s) to filter news
            topics: Topics to filter (e.g., "technology", "earnings")
            limit: Maximum number of articles

        Returns:
            List of news articles with sentiment
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "limit": limit,
        }

        if tickers:
            if isinstance(tickers, list):
                params["tickers"] = ",".join(tickers)
            else:
                params["tickers"] = tickers

        if topics:
            params["topics"] = topics

        data = await self._make_request(params)

        articles = []
        for item in data.get("feed", []):
            articles.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "source": item.get("source"),
                "published_at": item.get("time_published"),
                "summary": item.get("summary"),
                "overall_sentiment": item.get("overall_sentiment_score"),
                "overall_sentiment_label": item.get("overall_sentiment_label"),
                "ticker_sentiment": item.get("ticker_sentiment", []),
            })

        return articles

    def _safe_decimal(self, value: Any) -> Decimal | None:
        """Safely convert value to Decimal."""
        if value is None or value == "None" or value == "-":
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None


# Singleton instance
_client: AlphaVantageClient | None = None


async def get_alpha_vantage_client() -> AlphaVantageClient:
    """Get Alpha Vantage client instance."""
    global _client
    if _client is None:
        _client = AlphaVantageClient()
    return _client


async def close_alpha_vantage_client() -> None:
    """Close Alpha Vantage client."""
    global _client
    if _client:
        await _client.close()
        _client = None
