"""Configuration schemas for user settings."""

from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field, field_validator


# Data use categories for scraped websites
DATA_USE_CATEGORIES = [
    "dashboard_sentiment",
    "top_gainers",
    "top_losers",
    "hot_stocks",
    "hot_sectors",
    "bad_sectors",
    "analyst_ratings",
    "news",
    "etf_holdings",
    "etf_holding_changes",
    "fund_holdings",
    "fund_holding_changes",
]

# Display names for data use categories
DATA_USE_DISPLAY_NAMES = {
    "dashboard_sentiment": "Dashboard Sentiment",
    "top_gainers": "Top Gainers",
    "top_losers": "Top Losers",
    "hot_stocks": "Hot Stocks",
    "hot_sectors": "Hot Sectors",
    "bad_sectors": "Bad Sectors",
    "analyst_ratings": "Analyst Ratings",
    "news": "News",
    "etf_holdings": "ETF Holdings",
    "etf_holding_changes": "ETF Holding Changes",
    "fund_holdings": "Fund Holdings",
    "fund_holding_changes": "Fund Holding Changes",
}


# Data templates for each category - defines expected data format
DATA_TEMPLATES = {
    "dashboard_sentiment": {
        "description": "Market sentiment data for the dashboard",
        "template": {
            "market_summary": "Overall market description",
            "overall_sentiment": 0.5,  # 0-1 scale
            "bullish_score": 0.5,
            "bearish_score": 0.5,
            "trending_sectors": ["sector1", "sector2"],
            "declining_sectors": ["sector1", "sector2"],
            "market_themes": ["theme1", "theme2"],
            "key_events": ["event1", "event2"],
        },
        "extraction_prompt": """Extract market sentiment information from this webpage.

Requirements:
- Extract the overall market sentiment from headlines and market data
- Identify trending/hot sectors mentioned
- Identify declining/concerning sectors
- Extract key market themes or narratives
- Look for bullish/bearish language

Return ONLY valid JSON in this exact format:
{
    "market_summary": "Overall market description based on content...",
    "overall_sentiment": 0.5,
    "bullish_score": 0.5,
    "bearish_score": 0.5,
    "trending_sectors": ["sector1", "sector2"],
    "declining_sectors": ["sector1", "sector2"],
    "market_themes": ["theme1", "theme2"],
    "key_events": ["event1", "event2"]
}

If information is not found, use empty arrays/default values.
DO NOT make up information that is not present on the page.""",
    },
    "top_gainers": {
        "description": "Top gaining stocks by daily percentage change",
        "template": {
            "stocks": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "price": 150.25,
                    "change_pct": 5.2,
                    "change_abs": 7.45,
                    "volume": 50000000,
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract the TOP GAINING STOCKS from this webpage.

Requirements:
- Find stocks that have the HIGHEST POSITIVE percentage change today/yesterday
- This is specifically for stocks that went UP the most
- Extract ticker symbol, company name, current price if available
- MUST extract the percentage change (change_pct) - this is the most important field
- Extract absolute price change if available
- Extract trading volume if available

Return ONLY valid JSON in this exact format:
{
    "stocks": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "price": 150.25,
            "change_pct": 5.2,
            "change_abs": 7.45,
            "volume": 50000000
        }
    ],
    "source_date": "2024-01-01"
}

IMPORTANT:
- change_pct should be a POSITIVE number for gainers
- List stocks in order from highest gain to lowest
- Include at least 10-20 stocks if available
- If information is not found, return empty arrays.""",
    },
    "top_losers": {
        "description": "Top losing stocks by daily percentage change",
        "template": {
            "stocks": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "price": 150.25,
                    "change_pct": -5.2,
                    "change_abs": -7.45,
                    "volume": 50000000,
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract the TOP LOSING STOCKS from this webpage.

Requirements:
- Find stocks that have the HIGHEST NEGATIVE percentage change today/yesterday
- This is specifically for stocks that went DOWN the most
- Extract ticker symbol, company name, current price if available
- MUST extract the percentage change (change_pct) - this is the most important field
- Extract absolute price change if available
- Extract trading volume if available

Return ONLY valid JSON in this exact format:
{
    "stocks": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "price": 150.25,
            "change_pct": -5.2,
            "change_abs": -7.45,
            "volume": 50000000
        }
    ],
    "source_date": "2024-01-01"
}

IMPORTANT:
- change_pct should be a NEGATIVE number for losers
- List stocks in order from biggest loss to smallest
- Include at least 10-20 stocks if available
- If information is not found, return empty arrays.""",
    },
    "hot_stocks": {
        "description": "Trending/hot stocks data",
        "template": {
            "stocks": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "reason": "Why it's hot",
                    "sentiment": "bullish",
                    "price_change_pct": 5.2,
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract information about trending/hot stocks from this webpage.

Requirements:
- Find stocks that are mentioned as trending, hot, or gaining attention
- Extract ticker symbol, company name, and reason for being hot
- Note the sentiment (bullish/bearish/neutral)
- Extract price change percentage if available

Return ONLY valid JSON in this exact format:
{
    "stocks": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "reason": "Why it's trending",
            "sentiment": "bullish",
            "price_change_pct": 5.2
        }
    ],
    "source_date": "2024-01-01"
}

If information is not found, return empty arrays.""",
    },
    "hot_sectors": {
        "description": "Trending/hot sectors data",
        "template": {
            "sectors": [
                {
                    "name": "Technology",
                    "reason": "Why it's hot",
                    "top_stocks": ["AAPL", "MSFT"],
                    "performance_pct": 3.5,
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract information about trending/hot sectors from this webpage.

Requirements:
- Find sectors that are mentioned as trending, hot, or outperforming
- Extract sector name and reason for being hot
- Note top stocks in the sector if mentioned
- Extract performance percentage if available

Return ONLY valid JSON in this exact format:
{
    "sectors": [
        {
            "name": "Technology",
            "reason": "Why it's trending",
            "top_stocks": ["AAPL", "MSFT"],
            "performance_pct": 3.5
        }
    ],
    "source_date": "2024-01-01"
}

If information is not found, return empty arrays.""",
    },
    "bad_sectors": {
        "description": "Underperforming/declining sectors data",
        "template": {
            "sectors": [
                {
                    "name": "Energy",
                    "reason": "Why it's declining",
                    "affected_stocks": ["XOM", "CVX"],
                    "performance_pct": -2.5,
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract information about underperforming/declining sectors from this webpage.

Requirements:
- Find sectors that are mentioned as declining, underperforming, or facing challenges
- Extract sector name and reason for decline
- Note affected stocks in the sector if mentioned
- Extract performance percentage if available

Return ONLY valid JSON in this exact format:
{
    "sectors": [
        {
            "name": "Energy",
            "reason": "Why it's declining",
            "affected_stocks": ["XOM", "CVX"],
            "performance_pct": -2.5
        }
    ],
    "source_date": "2024-01-01"
}

If information is not found, return empty arrays.""",
    },
    "analyst_ratings": {
        "description": "Analyst ratings and recommendations",
        "template": {
            "ratings": [
                {
                    "ticker": "AAPL",
                    "analyst": "Analyst Name",
                    "firm": "Firm Name",
                    "rating": "Buy",
                    "price_target": 200.0,
                    "previous_rating": "Hold",
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract analyst ratings and recommendations from this webpage.

Requirements:
- Find stock ratings/recommendations from analysts
- Extract ticker, analyst name, firm, rating, and price target
- Note any rating changes if mentioned

Return ONLY valid JSON in this exact format:
{
    "ratings": [
        {
            "ticker": "AAPL",
            "analyst": "Analyst Name",
            "firm": "Firm Name",
            "rating": "Buy",
            "price_target": 200.0,
            "previous_rating": "Hold"
        }
    ],
    "source_date": "2024-01-01"
}

If information is not found, return empty arrays.""",
    },
    "news": {
        "description": "Market news and headlines",
        "template": {
            "articles": [
                {
                    "title": "Headline",
                    "url": "https://example.com/article",
                    "summary": "Brief summary",
                    "tickers": ["AAPL"],
                    "sentiment": "positive",
                    "category": "earnings",
                }
            ],
            "source_date": "2024-01-01",
        },
        "extraction_prompt": """Extract market news and headlines from this webpage.

Requirements:
- Find news articles and headlines
- Extract title, summary, related tickers
- IMPORTANT: Include the URL for each article (match title to AVAILABLE LINKS section)
- Determine sentiment (positive/negative/neutral)
- Categorize news (earnings, merger, regulation, etc.)

Return ONLY valid JSON in this exact format:
{
    "articles": [
        {
            "title": "Headline",
            "url": "https://example.com/article",
            "summary": "Brief summary",
            "tickers": ["AAPL"],
            "sentiment": "positive",
            "category": "earnings"
        }
    ],
    "source_date": "2024-01-01"
}

IMPORTANT: The "url" field is REQUIRED for each article. Find the matching URL from the AVAILABLE LINKS section.
If information is not found, return empty arrays.""",
    },
    "etf_holdings": {
        "description": "ETF holdings data",
        "template": {
            "etf_ticker": "SPY",
            "etf_name": "SPDR S&P 500 ETF",
            "holdings": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "weight_pct": 7.5,
                    "shares": 1000000,
                }
            ],
            "as_of_date": "2024-01-01",
        },
        "extraction_prompt": """Extract ETF holdings information from this webpage.

Requirements:
- Find the ETF name and ticker
- Extract top holdings with ticker, name, weight percentage, and shares
- Note the as-of date for the holdings data

Return ONLY valid JSON in this exact format:
{
    "etf_ticker": "SPY",
    "etf_name": "SPDR S&P 500 ETF",
    "holdings": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "weight_pct": 7.5,
            "shares": 1000000
        }
    ],
    "as_of_date": "2024-01-01"
}

If information is not found, return empty values.""",
    },
    "etf_holding_changes": {
        "description": "ETF holding changes data",
        "template": {
            "etf_ticker": "SPY",
            "changes": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "change_type": "increased",
                    "shares_change": 50000,
                    "weight_change_pct": 0.5,
                }
            ],
            "period": "Q4 2024",
        },
        "extraction_prompt": """Extract ETF holding changes from this webpage.

Requirements:
- Find changes in ETF holdings
- Extract ticker, change type (new/increased/decreased/sold)
- Note shares change and weight change if available
- Identify the reporting period

Return ONLY valid JSON in this exact format:
{
    "etf_ticker": "SPY",
    "changes": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "change_type": "increased",
            "shares_change": 50000,
            "weight_change_pct": 0.5
        }
    ],
    "period": "Q4 2024"
}

If information is not found, return empty values.""",
    },
    "fund_holdings": {
        "description": "Institutional fund holdings data",
        "template": {
            "fund_name": "Berkshire Hathaway",
            "holdings": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "value_usd": 150000000000,
                    "shares": 915000000,
                    "pct_portfolio": 40.5,
                }
            ],
            "filing_date": "2024-01-01",
        },
        "extraction_prompt": """Extract institutional fund holdings from this webpage.

Requirements:
- Find the fund/institution name
- Extract holdings with ticker, name, value, shares, and portfolio percentage
- Note the filing or report date

Return ONLY valid JSON in this exact format:
{
    "fund_name": "Berkshire Hathaway",
    "holdings": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "value_usd": 150000000000,
            "shares": 915000000,
            "pct_portfolio": 40.5
        }
    ],
    "filing_date": "2024-01-01"
}

If information is not found, return empty values.""",
    },
    "fund_holding_changes": {
        "description": "Institutional fund holding changes data",
        "template": {
            "fund_name": "Berkshire Hathaway",
            "changes": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc",
                    "change_type": "increased",
                    "shares_change": 1000000,
                    "value_change_usd": 150000000,
                }
            ],
            "period": "Q4 2024",
        },
        "extraction_prompt": """Extract institutional fund holding changes from this webpage.

Requirements:
- Find the fund/institution name
- Extract changes with ticker, change type, shares change, and value change
- Note the reporting period

Return ONLY valid JSON in this exact format:
{
    "fund_name": "Berkshire Hathaway",
    "changes": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "change_type": "increased",
            "shares_change": 1000000,
            "value_change_usd": 150000000
        }
    ],
    "period": "Q4 2024"
}

If information is not found, return empty values.""",
    },
}


class AIModelSettings(BaseModel):
    """AI model configuration settings."""

    default_model: Optional[str] = Field(None, description="Default Ollama model")
    stock_research_model: Optional[str] = Field(None, description="Model for stock research")
    market_sentiment_model: Optional[str] = Field(None, description="Model for market sentiment")
    web_scraping_model: Optional[str] = Field(None, description="Model for web scraping")
    temperature: Optional[float] = Field(0.3, ge=0.0, le=1.0, description="Model temperature")
    max_tokens: Optional[int] = Field(2048, ge=512, le=4096, description="Max tokens")


class DisplayPreferences(BaseModel):
    """Display preferences for UI."""

    research_history_items: Optional[int] = Field(10, ge=5, le=50, description="Number of research history items")
    fund_recent_changes_items: Optional[int] = Field(10, ge=5, le=50, description="Number of fund recent changes")
    holdings_per_fund: Optional[int] = Field(50, ge=10, le=100, description="Holdings per fund")
    peers_in_comparison: Optional[int] = Field(5, ge=3, le=10, description="Number of peers in comparison")


class WebsiteInfo(BaseModel):
    """Website information for scraping (legacy - simple format)."""

    name: str = Field(..., description="Website display name")
    url: str = Field(..., description="Website URL")


class ScrapedWebsiteCreate(BaseModel):
    """Schema for creating a new scraped website."""

    key: str = Field(..., description="Unique identifier key", min_length=1, max_length=100)
    name: str = Field(..., description="Display name for the data source", min_length=1, max_length=200)
    url: str = Field(..., description="URL to scrape", min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="Description of what data to scrape")
    data_use: Union[str, List[str]] = Field(..., description="Category(ies) of data use - single string or list")
    extraction_template: Optional[Dict[str, Any]] = Field(None, description="Custom extraction template")

    @field_validator('data_use')
    @classmethod
    def normalize_data_use(cls, v):
        """Convert data_use to comma-separated string for storage."""
        if isinstance(v, list):
            return ",".join(v)
        return v


class ScrapedWebsiteUpdate(BaseModel):
    """Schema for updating a scraped website."""

    name: Optional[str] = Field(None, description="Display name for the data source")
    url: Optional[str] = Field(None, description="URL to scrape")
    description: Optional[str] = Field(None, description="Description of what data to scrape")
    data_use: Optional[Union[str, List[str]]] = Field(None, description="Category(ies) of data use - single string or list")
    extraction_template: Optional[Dict[str, Any]] = Field(None, description="Custom extraction template")
    is_active: Optional[bool] = Field(None, description="Whether the website is active")

    @field_validator('data_use')
    @classmethod
    def normalize_data_use(cls, v):
        """Convert data_use to comma-separated string for storage."""
        if v is None:
            return v
        if isinstance(v, list):
            return ",".join(v)
        return v


class ScrapedWebsiteResponse(BaseModel):
    """Schema for scraped website response."""

    id: int
    key: str
    name: str
    url: str
    description: Optional[str]
    data_use: str  # Stored as comma-separated string
    data_use_list: List[str]  # List of categories
    data_use_display: str  # Human-readable display string
    extraction_template: Optional[Dict[str, Any]]
    is_active: bool
    last_test_at: Optional[datetime]
    last_test_result: Optional[Dict[str, Any]]
    last_test_success: Optional[bool]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScrapedWebsiteTestRequest(BaseModel):
    """Schema for testing a website scrape."""

    url: str = Field(..., description="URL to test scrape")
    description: Optional[str] = Field(None, description="Description of what to scrape")
    data_use: Union[str, List[str]] = Field(..., description="Data category(ies) to use template for - single string or list")


class ScrapedWebsiteTestResponse(BaseModel):
    """Schema for test scrape response."""

    success: bool
    scraped_data: Optional[Dict[str, Any]]
    error: Optional[str]
    response_time_ms: int
    extraction_prompt_used: str


class MarketScrapingSettings(BaseModel):
    """Market data scraping configuration."""

    website_key: Optional[str] = Field(None, description="Selected website for market scraping")
    scraping_model: Optional[str] = Field(None, description="Model for scraping")
    analysis_model: Optional[str] = Field(None, description="Model for analysis")
    custom_websites: Optional[Dict[str, WebsiteInfo]] = Field(default_factory=dict, description="User-defined custom websites (legacy)")


class ConfigSettings(BaseModel):
    """Complete user configuration settings."""

    ai_models: AIModelSettings = Field(default_factory=AIModelSettings)
    display_preferences: DisplayPreferences = Field(default_factory=DisplayPreferences)
    market_scraping: MarketScrapingSettings = Field(default_factory=MarketScrapingSettings)


class VPNStatus(BaseModel):
    """VPN connection status."""

    enabled: bool = Field(..., description="Whether VPN mode is enabled in config")
    connected: bool = Field(..., description="Whether VPN is currently connected")
    location: Optional[str] = Field(None, description="VPN connection location")
    message: str = Field(..., description="Status message")


class ConfigResponse(BaseModel):
    """Response for configuration endpoints."""

    settings: ConfigSettings
    has_alpha_vantage_key: bool = Field(False, description="Whether Alpha Vantage API key is configured")
    has_fmp_key: bool = Field(False, description="Whether FMP API key is configured")
    has_sec_user_agent: bool = Field(False, description="Whether SEC user agent is configured")
    vpn_status: Optional[VPNStatus] = Field(None, description="VPN connection status")


class TestAPIKeyRequest(BaseModel):
    """Request to test an API key."""

    provider: str = Field(..., description="API provider (alpha_vantage, fmp)")
    api_key: str = Field(..., description="API key to test")


class TestAPIKeyResponse(BaseModel):
    """Response for API key test."""

    valid: bool = Field(..., description="Whether the API key is valid")
    message: str = Field(..., description="Result message")
    provider: str = Field(..., description="API provider tested")
