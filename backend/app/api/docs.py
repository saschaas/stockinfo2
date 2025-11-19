"""API documentation configuration and examples."""

from typing import Any

# API metadata
API_TITLE = "StockInfo API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
## AI-Powered Stock Research API

This API provides comprehensive stock research capabilities including:

* **Market Sentiment** - Daily market analysis with AI-powered sentiment scoring
* **Stock Research** - Detailed stock analysis with valuation and technical indicators
* **Fund Tracking** - Monitor institutional holdings via SEC 13F filings
* **Report Generation** - Generate HTML and PDF research reports

### Authentication

Currently, the API does not require authentication. Rate limiting is applied per IP address.

### Rate Limits

| Endpoint Type | Limit |
|--------------|-------|
| General | 100 requests/minute |
| Research Jobs | 10 requests/minute |
| Report Generation | 5 requests/minute |

### Data Sources

All data is sourced from:
- **Alpha Vantage** - Stock prices, fundamentals, technical indicators
- **SEC EDGAR** - 13F institutional filings
- **Yahoo Finance** - Supplementary market data
- **Ollama** - AI-powered analysis and recommendations

### WebSocket Connections

Real-time updates are available via WebSocket at `/ws/research/{job_id}` for tracking research job progress.
"""

API_TAGS_METADATA = [
    {
        "name": "health",
        "description": "Health check endpoints for monitoring service status.",
    },
    {
        "name": "market",
        "description": "Market sentiment and overview endpoints. Get daily market analysis with AI-powered sentiment scoring.",
    },
    {
        "name": "stocks",
        "description": "Stock research and analysis endpoints. Start research jobs and retrieve comprehensive stock analysis.",
    },
    {
        "name": "funds",
        "description": "Fund tracking endpoints. Monitor institutional holdings and portfolio changes via SEC 13F filings.",
    },
    {
        "name": "reports",
        "description": "Report generation endpoints. Generate HTML and PDF research reports.",
    },
    {
        "name": "websocket",
        "description": "WebSocket endpoints for real-time updates on research job progress.",
    },
]

# OpenAPI examples
EXAMPLES: dict[str, dict[str, Any]] = {
    "market_sentiment": {
        "summary": "Current Market Sentiment",
        "description": "Example of current market sentiment response",
        "value": {
            "date": "2024-01-15",
            "overall_sentiment": 0.65,
            "bullish_score": 0.70,
            "bearish_score": 0.30,
            "sp500": {
                "close": 4850.25,
                "change_pct": 0.0125,
            },
            "nasdaq": {
                "close": 15230.50,
                "change_pct": 0.0185,
            },
            "dow": {
                "close": 37500.00,
                "change_pct": 0.0095,
            },
            "hot_sectors": [
                {"name": "Technology", "score": 0.85},
                {"name": "Healthcare", "score": 0.72},
            ],
            "negative_sectors": [
                {"name": "Energy", "score": 0.35},
            ],
            "top_news": [
                {
                    "title": "Tech stocks rally on AI optimism",
                    "source": "Reuters",
                    "sentiment": "positive",
                }
            ],
        },
    },
    "stock_analysis": {
        "summary": "Stock Analysis Response",
        "description": "Example of comprehensive stock analysis",
        "value": {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "current_price": 185.50,
            "price_change_1d": 0.0125,
            "valuation": {
                "pe_ratio": 28.5,
                "forward_pe": 25.0,
                "peg_ratio": 1.8,
                "price_to_book": 45.0,
                "market_cap": 2850000000000,
            },
            "technicals": {
                "rsi": 55.0,
                "macd": 2.5,
                "sma_20": 182.0,
                "sma_50": 178.0,
                "sma_200": 170.0,
            },
            "recommendation": "buy",
            "confidence_score": 0.75,
            "target_price_6m": 210.0,
            "recommendation_reasoning": "Strong fundamentals with growing services revenue. Technical indicators suggest bullish momentum with RSI in neutral territory.",
            "fund_ownership": [
                {
                    "fund_name": "ARK Innovation ETF",
                    "shares": 500000,
                    "value": 92750000,
                    "change_type": "increased",
                }
            ],
            "data_sources": {
                "prices": {"type": "api", "source": "alpha_vantage"},
                "fundamentals": {"type": "api", "source": "alpha_vantage"},
                "recommendation": {"type": "ai", "source": "ollama"},
            },
        },
    },
    "research_job": {
        "summary": "Research Job Response",
        "description": "Example of starting a research job",
        "value": {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "ticker": "MSFT",
            "status": "queued",
            "created_at": "2024-01-15T10:30:00Z",
            "message": "Research job queued. Connect to WebSocket for progress updates.",
        },
    },
    "fund_list": {
        "summary": "Fund List Response",
        "description": "Example of tracked funds list",
        "value": {
            "total": 20,
            "funds": [
                {
                    "id": 1,
                    "name": "ARK Innovation ETF",
                    "ticker": "ARKK",
                    "category": "tech_focused",
                    "last_filing_date": "2024-01-10",
                    "total_holdings": 35,
                    "total_value": 8500000000,
                },
                {
                    "id": 2,
                    "name": "Berkshire Hathaway",
                    "ticker": "BRK.A",
                    "category": "general",
                    "last_filing_date": "2024-01-05",
                    "total_holdings": 45,
                    "total_value": 350000000000,
                },
            ],
        },
    },
    "fund_holdings": {
        "summary": "Fund Holdings Response",
        "description": "Example of fund holdings",
        "value": {
            "fund_id": 1,
            "fund_name": "ARK Innovation ETF",
            "filing_date": "2024-01-10",
            "total_value": 8500000000,
            "holdings": [
                {
                    "ticker": "TSLA",
                    "company_name": "Tesla Inc.",
                    "shares": 3500000,
                    "value": 875000000,
                    "percentage": 10.3,
                    "change_type": "increased",
                    "change_shares": 150000,
                },
                {
                    "ticker": "ROKU",
                    "company_name": "Roku Inc.",
                    "shares": 5000000,
                    "value": 450000000,
                    "percentage": 5.3,
                    "change_type": "unchanged",
                    "change_shares": 0,
                },
            ],
        },
    },
    "error_not_found": {
        "summary": "Not Found Error",
        "description": "Example of 404 error response",
        "value": {
            "detail": "Stock analysis not found for ticker: INVALID",
        },
    },
    "error_validation": {
        "summary": "Validation Error",
        "description": "Example of 422 validation error",
        "value": {
            "detail": [
                {
                    "loc": ["body", "ticker"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
        },
    },
    "error_rate_limit": {
        "summary": "Rate Limit Error",
        "description": "Example of 429 rate limit error",
        "value": {
            "detail": "Rate limit exceeded. Please wait 60 seconds before retrying.",
        },
    },
}


def get_openapi_examples(example_keys: list[str]) -> dict[str, Any]:
    """Get OpenAPI examples by keys."""
    return {key: EXAMPLES[key] for key in example_keys if key in EXAMPLES}
