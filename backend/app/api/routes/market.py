"""Market sentiment API routes."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import MarketSentiment, WebScrapedMarketData
from backend.app.db.session import get_db
from backend.app.schemas.market import (
    MarketSentimentResponse,
    MarketSentimentHistoryResponse,
    WebScrapedMarketDataResponse,
    CombinedMarketResponse,
)

router = APIRouter()


@router.get("/sentiment", response_model=CombinedMarketResponse)
async def get_market_sentiment(
    db: AsyncSession = Depends(get_db),
) -> CombinedMarketResponse:
    """Get current market sentiment analysis.

    Returns both traditional and web-scraped market data including:
    - Traditional: Major index performance, sentiment scores, sectors, news
    - Web-scraped: Market summary, sentiment, sectors, themes from configured website

    Auto-triggers a refresh if no data exists or if data has all zero values (placeholder).
    """
    # Get the latest traditional sentiment
    stmt = select(MarketSentiment).order_by(MarketSentiment.date.desc()).limit(1)
    result = await db.execute(stmt)
    sentiment = result.scalar_one_or_none()

    # Auto-trigger refresh if:
    # 1. No data exists
    # 2. Data has all zero values (placeholder)
    # 3. Data is not from today (stale)
    should_refresh = (
        not sentiment or
        (sentiment.sp500_close == 0 and sentiment.nasdaq_close == 0 and sentiment.dow_close == 0) or
        sentiment.date < date.today()
    )

    if should_refresh:
        from backend.app.tasks.market import refresh_market_sentiment as refresh_task
        refresh_task.delay()
        # Note: This will be async, so first load may show stale data, but subsequent loads will have fresh data

    if not sentiment:
        traditional_response = MarketSentimentResponse(
            date=date.today(),
            message="No sentiment data available. Run market analysis first.",
        )
    else:
        traditional_response = MarketSentimentResponse(
            date=sentiment.date,
            indices={
                "sp500": {
                    "close": float(sentiment.sp500_close) if sentiment.sp500_close else None,
                    "change_pct": float(sentiment.sp500_change_pct) if sentiment.sp500_change_pct else None,
                },
                "nasdaq": {
                    "close": float(sentiment.nasdaq_close) if sentiment.nasdaq_close else None,
                    "change_pct": float(sentiment.nasdaq_change_pct) if sentiment.nasdaq_change_pct else None,
                },
                "dow": {
                    "close": float(sentiment.dow_close) if sentiment.dow_close else None,
                    "change_pct": float(sentiment.dow_change_pct) if sentiment.dow_change_pct else None,
                },
            },
            overall_sentiment=float(sentiment.overall_sentiment) if sentiment.overall_sentiment else None,
            bullish_score=float(sentiment.bullish_score) if sentiment.bullish_score else None,
            bearish_score=float(sentiment.bearish_score) if sentiment.bearish_score else None,
            hot_sectors=sentiment.hot_sectors or [],
            negative_sectors=sentiment.negative_sectors or [],
            top_news=sentiment.top_news or [],
        )

    # Get web-scraped data
    stmt = select(WebScrapedMarketData).order_by(WebScrapedMarketData.date.desc()).limit(1)
    result = await db.execute(stmt)
    web_data = result.scalar_one_or_none()

    web_scraped_response = None
    if web_data:
        web_scraped_response = WebScrapedMarketDataResponse(
            date=web_data.date,
            source_url=web_data.source_url,
            source_name=web_data.source_name,
            market_summary=web_data.market_summary,
            overall_sentiment=float(web_data.overall_sentiment) if web_data.overall_sentiment else None,
            bullish_score=float(web_data.bullish_score) if web_data.bullish_score else None,
            bearish_score=float(web_data.bearish_score) if web_data.bearish_score else None,
            trending_sectors=web_data.trending_sectors or [],
            declining_sectors=web_data.declining_sectors or [],
            market_themes=web_data.market_themes or [],
            key_events=web_data.key_events or [],
            confidence_score=float(web_data.confidence_score) if web_data.confidence_score else None,
            scraping_model=web_data.scraping_model,
            analysis_model=web_data.analysis_model,
        )

    return CombinedMarketResponse(
        traditional=traditional_response,
        web_scraped=web_scraped_response,
    )


@router.get("/sentiment/history", response_model=MarketSentimentHistoryResponse)
async def get_market_sentiment_history(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> MarketSentimentHistoryResponse:
    """Get market sentiment history for the specified number of days."""
    start_date = date.today() - timedelta(days=days)

    stmt = (
        select(MarketSentiment)
        .where(MarketSentiment.date >= start_date)
        .order_by(MarketSentiment.date.desc())
    )
    result = await db.execute(stmt)
    sentiments = result.scalars().all()

    history = []
    for s in sentiments:
        history.append({
            "date": s.date,
            "sp500_change_pct": float(s.sp500_change_pct) if s.sp500_change_pct else None,
            "nasdaq_change_pct": float(s.nasdaq_change_pct) if s.nasdaq_change_pct else None,
            "dow_change_pct": float(s.dow_change_pct) if s.dow_change_pct else None,
            "overall_sentiment": float(s.overall_sentiment) if s.overall_sentiment else None,
        })

    return MarketSentimentHistoryResponse(
        days=days,
        history=history,
    )


@router.post("/sentiment/refresh")
async def refresh_market_sentiment(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a refresh of market sentiment analysis.

    This will queue a job to fetch latest market data and run sentiment analysis.
    """
    from backend.app.tasks.market import refresh_market_sentiment as refresh_task

    # Send task to Celery
    task = refresh_task.delay()

    return {
        "status": "queued",
        "message": "Market sentiment refresh has been queued",
        "job_id": task.id,
    }


@router.post("/sentiment/refresh-web-scraped")
async def refresh_web_scraped_market_data(
    website_key: str | None = None,
    scraping_model: str | None = None,
    analysis_model: str | None = None,
) -> dict:
    """Trigger a refresh of web-scraped market data.

    Args:
        website_key: Optional website config key (defaults to user config)
        scraping_model: Optional LLM model for scraping (defaults to user config)
        analysis_model: Optional LLM model for analysis (defaults to user config)
    """
    from backend.app.tasks.market import refresh_web_scraped_market as refresh_task

    # Send task to Celery
    task = refresh_task.delay(
        website_config_key=website_key,
        scraping_model=scraping_model,
        analysis_model=analysis_model,
    )

    return {
        "status": "queued",
        "message": "Web-scraped market data refresh has been queued",
        "job_id": task.id,
    }


@router.get("/scraping-config")
async def get_market_scraping_config(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get available market scraping website configurations.

    Returns websites from both config.yaml and user-configured custom websites
    from the database.
    """
    from backend.app.config import get_settings
    from backend.app.db.models import ScrapedWebsite

    settings = get_settings()
    configs = settings.web_scraping_configs

    # Get config.yaml websites (filter for market-related configs)
    market_configs = {
        key: {
            "name": key,
            "url": cfg.url_pattern,
            "source": "config",  # From config.yaml
            "data_use": "dashboard_sentiment",
        }
        for key, cfg in configs.items()
        if key.startswith("market_overview_")
    }

    # Get custom websites from database
    stmt = select(ScrapedWebsite).where(ScrapedWebsite.is_active == True)
    result = await db.execute(stmt)
    custom_websites = result.scalars().all()

    # Add custom websites to the list
    for website in custom_websites:
        market_configs[website.key] = {
            "name": website.name,
            "url": website.url,
            "source": "custom",  # User-defined
            "data_use": website.data_use,
            "description": website.description,
        }

    return {
        "available_websites": market_configs,
    }


@router.post("/scraping-config")
async def set_market_scraping_config(
    website_key: str,
    scraping_model: str | None = None,
    analysis_model: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save user's market scraping configuration."""
    from backend.app.db.models import UserConfig

    # Save website selection
    stmt = select(UserConfig).where(UserConfig.config_key == "market_scraping_website")
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.config_value = {"website_key": website_key}
    else:
        config = UserConfig(
            config_key="market_scraping_website",
            config_value={"website_key": website_key},
            description="Selected website for market data scraping",
        )
        db.add(config)

    # Save scraping model if provided
    if scraping_model:
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_scraping_llm_model"
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.config_value = {"model": scraping_model}
        else:
            config = UserConfig(
                config_key="market_scraping_llm_model",
                config_value={"model": scraping_model},
                description="LLM model for market data scraping",
            )
            db.add(config)

    # Save analysis model if provided
    if analysis_model:
        stmt = select(UserConfig).where(
            UserConfig.config_key == "market_analysis_llm_model"
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.config_value = {"model": analysis_model}
        else:
            config = UserConfig(
                config_key="market_analysis_llm_model",
                config_value={"model": analysis_model},
                description="LLM model for market analysis",
            )
            db.add(config)

    await db.commit()

    return {
        "status": "success",
        "message": "Market scraping configuration saved",
        "config": {
            "website_key": website_key,
            "scraping_model": scraping_model,
            "analysis_model": analysis_model,
        },
    }


@router.get("/indices/history")
async def get_indices_history(
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Get historical data for major market indices.

    Returns the last N days of price data for S&P 500, NASDAQ, and Dow Jones.
    """
    from backend.app.services.yahoo_finance import get_yahoo_finance_client

    client = get_yahoo_finance_client()

    # Map days to period parameter
    if days <= 5:
        period = "5d"
    elif days <= 30:
        period = "1mo"
    elif days <= 90:
        period = "3mo"
    elif days <= 180:
        period = "6mo"
    else:
        period = "1y"

    indices = {
        "^GSPC": "sp500",
        "^IXIC": "nasdaq",
        "^DJI": "dow",
    }

    result = {}
    for symbol, key in indices.items():
        try:
            history = await client.get_historical_prices(
                symbol,
                period=period,
                interval="1d",
            )
            result[key] = [
                {
                    "date": point["date"],
                    "close": float(point["close"]) if point["close"] else None,
                }
                for point in history
            ]
        except Exception as e:
            result[key] = []

    return result


def _normalize_stock_data(item: dict, category: str) -> dict:
    """
    Normalize scraped stock data to a consistent format.

    Different sources may return data with different field names.
    This function maps common variations to expected field names.
    """
    import re

    normalized = {}

    # Map ticker/symbol fields
    normalized["ticker"] = item.get("ticker") or item.get("symbol") or item.get("TICKER") or item.get("Symbol") or "N/A"

    # Map name fields
    normalized["name"] = item.get("name") or item.get("company_name") or item.get("Name") or item.get("company") or normalized["ticker"]

    # Map price fields
    price = item.get("price") or item.get("Price") or item.get("current_price")
    if price is not None:
        try:
            normalized["price"] = float(str(price).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            normalized["price"] = None
    else:
        normalized["price"] = None

    # Map change percentage - handle various formats
    change_pct = item.get("change_pct") or item.get("change_percent") or item.get("pct_change") or item.get("percent_change")

    # If change_pct not found directly, try to parse from combined string like "+1.15 (+13.39%)"
    if change_pct is None:
        price_change = item.get("price_change") or item.get("change") or ""
        if isinstance(price_change, str) and "%" in price_change:
            # Extract percentage from string like "+1.15 (+13.39%)" or "-5.2%"
            match = re.search(r'([+-]?\d+\.?\d*)%', price_change)
            if match:
                try:
                    change_pct = float(match.group(1))
                except (ValueError, TypeError):
                    change_pct = None

    if change_pct is not None:
        try:
            normalized["change_pct"] = float(str(change_pct).replace("%", "").replace("+", ""))
        except (ValueError, TypeError):
            normalized["change_pct"] = 0.0
    else:
        normalized["change_pct"] = 0.0

    # Map absolute change
    change_abs = item.get("change_abs") or item.get("change_absolute") or item.get("price_change_abs")
    if change_abs is not None:
        try:
            normalized["change_abs"] = float(str(change_abs).replace("$", "").replace(",", "").replace("+", ""))
        except (ValueError, TypeError):
            normalized["change_abs"] = None
    else:
        normalized["change_abs"] = None

    # Map volume
    volume = item.get("volume") or item.get("Volume")
    if volume is not None:
        try:
            # Handle volume strings like "1.2M" or "500K"
            vol_str = str(volume).upper().replace(",", "")
            if "M" in vol_str:
                normalized["volume"] = int(float(vol_str.replace("M", "")) * 1_000_000)
            elif "K" in vol_str:
                normalized["volume"] = int(float(vol_str.replace("K", "")) * 1_000)
            elif "B" in vol_str:
                normalized["volume"] = int(float(vol_str.replace("B", "")) * 1_000_000_000)
            else:
                normalized["volume"] = int(float(vol_str))
        except (ValueError, TypeError):
            normalized["volume"] = None
    else:
        normalized["volume"] = None

    # Copy any additional fields for hot_stocks category
    if category == "hot_stocks":
        normalized["reason"] = item.get("reason") or item.get("description") or None
        normalized["sentiment"] = item.get("sentiment") or None

    return normalized


async def _get_yahoo_finance_top_movers(category: str) -> tuple[list, dict | None]:
    """Fetch top gainers or losers from Yahoo Finance API.

    Args:
        category: Either "top_gainers" or "top_losers"

    Returns:
        Tuple of (data list, source info dict or None if failed)
    """
    from backend.app.services.yahoo_finance import get_yahoo_finance_client

    try:
        client = get_yahoo_finance_client()
        if category == "top_gainers":
            data = await client.get_top_gainers(limit=10)
        else:
            data = await client.get_top_losers(limit=10)

        if data:
            source_info = {
                "source_key": f"yahoo_finance_{category.replace('top_', '')}",
                "source_url": "https://finance.yahoo.com/",
                "date": date.today().isoformat(),
                "scraping_model": None,
            }
            return data, source_info
    except Exception as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.warning(f"Failed to fetch Yahoo Finance {category}", error=str(e))

    return [], None


async def _get_alpha_vantage_news(db) -> tuple[list, dict | None]:
    """Fetch news from Alpha Vantage (stored in MarketSentiment).

    Returns:
        Tuple of (news list, source info dict or None if no data)
    """
    stmt = select(MarketSentiment).order_by(MarketSentiment.date.desc()).limit(1)
    result = await db.execute(stmt)
    sentiment = result.scalar_one_or_none()

    if sentiment and sentiment.top_news:
        source_info = {
            "source_key": "alpha_vantage_news",
            "source_url": "https://www.alphavantage.co/",
            "date": sentiment.date.isoformat(),
            "scraping_model": None,
        }
        return sentiment.top_news, source_info

    return [], None


@router.get("/scraped-data/{category}")
async def get_scraped_category_data(
    category: str,
    days: int = Query(default=1, ge=1, le=30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get scraped data for a specific category.

    This retrieves category-specific data (e.g., top_gainers, top_losers, hot_stocks)
    from configured data sources only (based on category mappings in user config).
    Data from multiple sources is combined if multiple sources are configured.

    Supports both web-scraped sources and traditional API sources:
    - alpha_vantage_news: News from Alpha Vantage
    - yahoo_finance_gainers: Top gainers from Yahoo Finance
    - yahoo_finance_losers: Top losers from Yahoo Finance

    Args:
        category: Data category to retrieve (e.g., "top_gainers", "top_losers", "hot_stocks")
        days: Number of days to look back (default: 1, max: 30)

    Returns:
        Combined data from configured sources for the specified category
    """
    from backend.app.db.models import ScrapedCategoryData, UserConfig
    from backend.app.schemas.config import DATA_USE_CATEGORIES, DATA_USE_DISPLAY_NAMES

    # Traditional API source keys
    API_SOURCES = {
        "alpha_vantage_news",
        "alpha_vantage_sentiment",
        "yahoo_finance_gainers",
        "yahoo_finance_losers",
    }

    # Validate category
    if category not in DATA_USE_CATEGORIES:
        return {
            "success": False,
            "error": f"Invalid category '{category}'. Must be one of: {DATA_USE_CATEGORIES}",
            "data": [],
        }

    # Get configured source mappings for this category
    stmt = select(UserConfig).where(UserConfig.config_key == "category_source_mappings")
    result = await db.execute(stmt)
    mappings_config = result.scalar_one_or_none()

    configured_sources = None
    if mappings_config and mappings_config.config_value:
        category_mappings = mappings_config.config_value
        if category in category_mappings and category_mappings[category]:
            configured_sources = category_mappings[category]

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    # Categories that contain stock data and should be normalized
    STOCK_CATEGORIES = {"top_gainers", "top_losers", "hot_stocks"}

    # Combine data from all sources
    combined_data = []
    sources = []

    # Determine which API sources are configured (if any)
    api_sources_to_fetch = set()
    web_sources_to_fetch = []

    if configured_sources:
        for src in configured_sources:
            if src in API_SOURCES:
                api_sources_to_fetch.add(src)
            else:
                web_sources_to_fetch.append(src)
    else:
        # No specific sources configured - don't include any data
        pass

    # Fetch data from traditional API sources
    if "yahoo_finance_gainers" in api_sources_to_fetch and category == "top_gainers":
        data, source_info = await _get_yahoo_finance_top_movers("top_gainers")
        if data and source_info:
            sources.append(source_info)
            # Normalize stock data
            normalized = [_normalize_stock_data(item, category) for item in data if isinstance(item, dict)]
            combined_data.extend(normalized)

    if "yahoo_finance_losers" in api_sources_to_fetch and category == "top_losers":
        data, source_info = await _get_yahoo_finance_top_movers("top_losers")
        if data and source_info:
            sources.append(source_info)
            # Normalize stock data
            normalized = [_normalize_stock_data(item, category) for item in data if isinstance(item, dict)]
            combined_data.extend(normalized)

    if "alpha_vantage_news" in api_sources_to_fetch and category == "news":
        data, source_info = await _get_alpha_vantage_news(db)
        if data and source_info:
            sources.append(source_info)
            combined_data.extend(data)

    # Fetch data from web-scraped sources (if any configured)
    if web_sources_to_fetch:
        query_conditions = [
            ScrapedCategoryData.category == category,
            ScrapedCategoryData.date >= start_date,
            ScrapedCategoryData.date <= end_date,
            ScrapedCategoryData.source_key.in_(web_sources_to_fetch),
        ]

        stmt = (
            select(ScrapedCategoryData)
            .where(*query_conditions)
            .order_by(ScrapedCategoryData.date.desc(), ScrapedCategoryData.created_at.desc())
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        for record in records:
            sources.append({
                "source_key": record.source_key,
                "source_url": record.source_url,
                "date": record.date.isoformat(),
                "scraping_model": record.scraping_model,
            })

            # Extract the actual data items
            data = record.data
            items = []

            if isinstance(data, dict):
                # Check for common data keys
                if "stocks" in data:
                    items = data["stocks"]
                elif "sectors" in data:
                    items = data["sectors"]
                elif "ratings" in data:
                    items = data["ratings"]
                elif "articles" in data:
                    items = data["articles"]
                elif "holdings" in data:
                    items = data["holdings"]
                elif "changes" in data:
                    items = data["changes"]
                else:
                    # If no known key, include the whole data object
                    items = [data]
            elif isinstance(data, list):
                items = data

            # Normalize stock data for stock-related categories
            if category in STOCK_CATEGORIES and items:
                items = [_normalize_stock_data(item, category) for item in items if isinstance(item, dict)]

            combined_data.extend(items)

    # Sort by change_pct for top_gainers/top_losers
    if category == "top_gainers":
        combined_data.sort(key=lambda x: x.get("change_pct", 0) if isinstance(x, dict) else 0, reverse=True)
    elif category == "top_losers":
        combined_data.sort(key=lambda x: x.get("change_pct", 0) if isinstance(x, dict) else 0)
    elif category == "news" and len(sources) > 1:
        # Interleave news from multiple sources to show variety
        # Group items by source, then interleave
        from itertools import zip_longest

        source_groups = {}
        for item in combined_data:
            # Try to identify source from item fields
            source_key = None
            if isinstance(item, dict):
                # Alpha Vantage news has 'source' and 'published_at' fields
                if "published_at" in item and "source" in item:
                    source_key = "alpha_vantage"
                # Web-scraped news may have different structure
                elif "category" in item or "sentiment" in item:
                    source_key = "web_scraped"
                else:
                    source_key = "other"

            if source_key not in source_groups:
                source_groups[source_key] = []
            source_groups[source_key].append(item)

        # Interleave items from different sources
        interleaved = []
        for items in zip_longest(*source_groups.values(), fillvalue=None):
            for item in items:
                if item is not None:
                    interleaved.append(item)
        combined_data = interleaved

    return {
        "success": True,
        "category": category,
        "category_display": DATA_USE_DISPLAY_NAMES.get(category, category),
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "sources": sources,
        "data": combined_data,
        "count": len(combined_data),
        "configured_sources": configured_sources,  # None means all sources, list means only those sources
        "has_configured_sources": configured_sources is not None,
    }


@router.get("/scraped-data")
async def get_all_scraped_categories(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get summary of all available scraped category data.

    Returns a list of categories that have data available, with counts and source information.
    """
    from sqlalchemy import func
    from backend.app.db.models import ScrapedCategoryData
    from backend.app.schemas.config import DATA_USE_DISPLAY_NAMES

    today = date.today()

    # Get counts by category for today
    stmt = (
        select(
            ScrapedCategoryData.category,
            func.count(ScrapedCategoryData.id).label("source_count"),
        )
        .where(ScrapedCategoryData.date == today)
        .group_by(ScrapedCategoryData.category)
    )
    result = await db.execute(stmt)
    category_counts = result.all()

    categories = []
    for row in category_counts:
        categories.append({
            "category": row.category,
            "display_name": DATA_USE_DISPLAY_NAMES.get(row.category, row.category),
            "source_count": row.source_count,
            "date": today.isoformat(),
        })

    return {
        "success": True,
        "date": today.isoformat(),
        "categories": categories,
    }
