"""Market Sentiment Agent for analyzing overall market conditions."""

from typing import Any
from datetime import date

import ollama
import structlog

from backend.app.config import get_settings
from backend.app.services.yahoo_finance import get_yahoo_finance_client
from backend.app.services.alpha_vantage import get_alpha_vantage_client

logger = structlog.get_logger(__name__)
settings = get_settings()


class MarketSentimentAgent:
    """Agent for analyzing market sentiment and conditions."""

    def __init__(self) -> None:
        self.model = settings.ollama_model

    async def analyze(self) -> dict[str, Any]:
        """Analyze current market sentiment.

        Returns:
            Market sentiment analysis results
        """
        logger.info("Market Sentiment Agent starting analysis")

        # Gather market data
        market_data = await self._gather_market_data()

        # Gather news
        news_data = await self._gather_news()

        # Run AI analysis
        analysis = await self._run_analysis(market_data, news_data)

        return {
            "date": date.today().isoformat(),
            "indices": market_data.get("indices", {}),
            "sectors": market_data.get("sectors", []),
            "news": news_data,
            "overall_sentiment": analysis.get("overall_sentiment", 0.5),
            "bullish_score": analysis.get("bullish_score", 0.5),
            "bearish_score": analysis.get("bearish_score", 0.5),
            "hot_sectors": analysis.get("hot_sectors", []),
            "negative_sectors": analysis.get("negative_sectors", []),
            "summary": analysis.get("summary", ""),
            "data_sources": {
                "indices": "yahoo_finance",
                "sectors": "yahoo_finance",
                "news": "alpha_vantage",
                "analysis": "ollama",
            },
        }

    async def _gather_market_data(self) -> dict[str, Any]:
        """Gather market indices and sector data."""
        client = get_yahoo_finance_client()

        try:
            indices = await client.get_market_indices()
            sectors = await client.get_sector_performance()

            return {
                "indices": indices,
                "sectors": sectors,
            }
        except Exception as e:
            logger.error("Failed to gather market data", error=str(e))
            return {"indices": {}, "sectors": []}

    async def _gather_news(self) -> list[dict[str, Any]]:
        """Gather market news with sentiment."""
        try:
            client = await get_alpha_vantage_client()
            news = await client.get_news_sentiment(
                topics="economy,finance,earnings",
                limit=20,
            )

            # Format news for analysis
            formatted = []
            for article in news:
                formatted.append({
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "sentiment": article.get("overall_sentiment"),
                    "sentiment_label": article.get("overall_sentiment_label"),
                    "url": article.get("url"),
                })

            return formatted

        except Exception as e:
            logger.warning("Failed to gather news", error=str(e))
            return []

    async def _run_analysis(
        self,
        market_data: dict[str, Any],
        news_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run AI analysis on gathered data."""
        # Build context
        context = self._build_analysis_context(market_data, news_data)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(),
                    },
                    {"role": "user", "content": context},
                ],
            )

            # Parse response
            import json
            content = response["message"]["content"]

            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])

        except Exception as e:
            logger.error("AI analysis failed", error=str(e))

        # Return defaults on failure
        return {
            "overall_sentiment": 0.5,
            "bullish_score": 0.5,
            "bearish_score": 0.5,
            "hot_sectors": [],
            "negative_sectors": [],
            "summary": "Analysis could not be completed.",
        }

    def _build_analysis_context(
        self,
        market_data: dict[str, Any],
        news_data: list[dict[str, Any]],
    ) -> str:
        """Build context string for AI analysis."""
        context = "Analyze the following market data:\n\n"

        # Add indices
        context += "## Market Indices\n"
        for symbol, data in market_data.get("indices", {}).items():
            if "error" not in data:
                change = float(data.get("change_percent", 0) or 0)
                context += f"- {data.get('name', symbol)}: {change:+.2f}%\n"

        # Add sectors
        context += "\n## Sector Performance (Top 5)\n"
        for sector in market_data.get("sectors", [])[:5]:
            change = float(sector.get("change_percent", 0) or 0)
            context += f"- {sector.get('name', 'Unknown')}: {change:+.2f}%\n"

        # Add bottom sectors
        context += "\n## Sector Performance (Bottom 5)\n"
        for sector in market_data.get("sectors", [])[-5:]:
            change = float(sector.get("change_percent", 0) or 0)
            context += f"- {sector.get('name', 'Unknown')}: {change:+.2f}%\n"

        # Add news
        context += "\n## Recent News Headlines\n"
        for article in news_data[:10]:
            label = article.get("sentiment_label", "neutral")
            context += f"- [{label}] {article.get('title', 'Unknown')}\n"

        return context

    def _get_system_prompt(self) -> str:
        """Get system prompt for market sentiment analysis."""
        return """You are a financial market analyst providing objective market sentiment analysis.

Analyze the provided market data and provide a comprehensive sentiment assessment.

Your response must be valid JSON with the following structure:
{
    "overall_sentiment": <float 0-1, where 0=very bearish, 1=very bullish>,
    "bullish_score": <float 0-1>,
    "bearish_score": <float 0-1>,
    "hot_sectors": ["sector1", "sector2", "sector3"],
    "negative_sectors": ["sector1", "sector2", "sector3"],
    "summary": "<2-3 sentence market summary>"
}

Be objective and data-driven. Consider:
- Index performance and trends
- Sector rotation patterns
- News sentiment distribution
- Volume and volatility indicators

Respond ONLY with valid JSON, no additional text."""
